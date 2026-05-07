from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import unicodedata
from datetime import datetime
from .models import FinancialData




# ---------------- HELPERS ----------------
def clean(t):
    return unicodedata.normalize("NFKC", t).replace('\u202a', '').replace('\u202c', '').strip()


def is_num(s):
    s = s.replace('B', '').replace('M', '').replace('−', '-').replace(',', '').strip()
    try:
        float(s)
        return True
    except:
        return False


def is_value(s):
    """Accept numeric values AND dash placeholders as valid row values"""
    return is_num(s) or s.strip() == '—'


def convert_to_numeric(value):
    if not is_num(value):
        return None
    clean_val = value.replace('B', '').replace('M', '').replace('−', '-').replace(',', '').strip()
    try:
        numeric_value = float(clean_val)
        if 'B' in value:
            numeric_value *= 1_000_000_000
        elif 'M' in value:
            numeric_value *= 1_000_000
        return numeric_value
    except:
        return None

# ---------------- MAIN SCRAPER ----------------
def scrape_company(symbol):

    print(f"🚀 Scraping: {symbol}")

    FinancialData.objects.filter(symbol=symbol.upper()).delete()

    options = Options()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)

    try:
        url = f"https://www.tradingview.com/symbols/PSX-{symbol}/financials-statistics-and-ratios/?selected=price_cash_flow"
        driver.get(url)
        time.sleep(6)

        # ---------------- SCROLL BODY RIGHT + DOWN ----------------
        try:
            body_scroll_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    '//*[@id="js-category-content"]/div[2]/div/div/div[3]/div[2]/div[3]/div[2]/div[2]/div'
                ))
            )

            # Scroll body RIGHT
            driver.execute_script("arguments[0].scrollLeft = arguments[0].scrollWidth", body_scroll_container)
            time.sleep(2)

            # Scroll body DOWN
            body_inner = driver.find_element(
                By.XPATH,
                '//*[@id="js-category-content"]/div[2]/div/div/div[3]/div[2]/div[3]/div[2]/div[2]/div/div[1]'
            )
            driver.execute_script("arguments[0].scrollTop = 0", body_inner)
            time.sleep(1)
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", body_inner)
            time.sleep(2)

        except Exception as e:
            print("⚠️ Body scroll error:", e)

        time.sleep(3)

        # ---------------- HEADERS ----------------
        header = driver.find_element(
            By.XPATH,
            '//*[@id="js-category-content"]/div[2]/div/div/div[3]/div[2]/div[3]/div[1]/div'
        )

        raw = [clean(x) for x in header.text.split("\n") if clean(x)]
        print(f"📋 Raw header tokens: {raw}")

        cols = []
        i = 1  # skip first label (Currency: PKR)

        while i < len(raw):
            if i + 1 < len(raw) and not raw[i + 1].startswith("Q") and raw[i + 1] != "Current":
                cols.append(raw[i] + " " + raw[i + 1])
                i += 2
            else:
                cols.append(raw[i])
                i += 1

        print(f"📊 ALL HEADER COLUMNS ({len(cols)}): {cols}")

        # ---------------- BODY VALUES ----------------
        body = driver.find_element(
            By.XPATH,
            '//*[@id="js-category-content"]/div[2]/div/div/div[3]/div[2]/div[3]/div[2]/div[2]/div/div[1]'
        )

        vals = [clean(x) for x in body.text.split("\n") if clean(x)]

        print(f"📋 Total tokens in body: {len(vals)}")
        print(f"📋 First 30 tokens: {vals[:30]}")

        # ✅ KEY FIX: detect N from body, not from header
        # Find first metric row by locating first non-category token
        # then count how many values follow it before next text token
        N = detect_N_from_body(vals)
        print(f"📋 DETECTED N from body: {N}")

        if N is None or N == 0:
            print("❌ Could not detect N. Aborting.")
            return 0, "Could not detect column count from body"

        # ✅ Use only the LAST N cols from header (body shows rightmost columns)
        visible_cols = cols[-N:]
        print(f"📊 VISIBLE COLUMNS ({len(visible_cols)}): {visible_cols}")

        # ---------------- PARSE ROWS ----------------
        rows = []
        category = ""
        i = 0

        while i < len(vals):

            if i + N < len(vals):
                nxt = vals[i + 1: i + 1 + N]

                if len(nxt) == N and all(is_value(x) for x in nxt):
                    rows.append([category, vals[i]] + nxt)
                    i += N + 1
                    continue

            if not is_num(vals[i]) and vals[i] != '—':
                category = vals[i]

            i += 1

        print(f"📊 ROWS FOUND: {len(rows)}")

        if not rows:
            print("❌ No rows found!")
            print("📋 Full vals dump:", vals)
            return 0, "No rows parsed"

        # ---------------- SAVE TO DATABASE ----------------
        rows_saved = 0
        scrape_date = datetime.now()

        for r in rows:
            cat = r[0]
            metric = r[1]
            values = r[2:]

            for idx, period in enumerate(visible_cols):
                value = values[idx]

                FinancialData.objects.create(
                    symbol=symbol.upper(),
                    category=cat,
                    metric=metric,
                    period=period,
                    value=value,
                    numeric_value=convert_to_numeric(value),
                    scrape_date=scrape_date
                )

                rows_saved += 1

        print(f"✅ Done. Rows saved: {rows_saved}")
        return rows_saved, None

    except Exception as e:
        print(f"❌ Scraper error: {e}")
        import traceback
        traceback.print_exc()
        return 0, str(e)

    finally:
        driver.quit()


# ✅ HELPER: auto-detect how many columns are visible in body
def detect_N_from_body(vals):
    """
    Find the first metric row and count how many
    consecutive is_value() tokens follow it.
    That count = N (visible columns in body DOM)
    """
    i = 0
    while i < len(vals):
        # Skip known category names and pure dash lines
        if not is_value(vals[i]):
            # This could be a metric name — count values after it
            count = 0
            j = i + 1
            while j < len(vals) and is_value(vals[j]):
                count += 1
                j += 1

            if count > 0:
                print(f"📋 detect_N: '{vals[i]}' → {count} values follow")
                return count
        i += 1
    return None