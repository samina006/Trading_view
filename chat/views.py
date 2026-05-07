from django.shortcuts import render, redirect
from collections import defaultdict
from .models import FinancialData
from .scraper import scrape_company
from .scraper import convert_to_numeric
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User


@login_required(login_url='login')
def home(request):

    print("REQUEST HIT HOME VIEW")

    symbol = request.GET.get("symbol")
    message = request.GET.get("msg")

    table_data = []
    periods = []

    if symbol:
        symbol = symbol.strip().upper()
        print("SYMBOL:", symbol)

        data = FinancialData.objects.filter(symbol__iexact=symbol)
        print("DATA COUNT:", data.count())

        # ---------------- STRUCTURE BUILD ----------------
        structured = defaultdict(lambda: defaultdict(dict))
        period_set = set()

        for row in data:
            structured[row.category][row.metric][row.period] = row.value
            period_set.add(row.period)

        periods = sorted(period_set)

        # ---------------- FORMAT LIKE OLD VIEW ----------------
        for category, metrics in structured.items():
            rows = []

            for metric, values in metrics.items():

                row_values = []
                for p in periods:
                    row_values.append(values.get(p, "-"))

                rows.append({
                    "metric": metric,
                    "values": row_values
                })

            table_data.append({
                "category": category,
                "rows": rows
            })

        print("TABLE DATA SAMPLE:", table_data)

    return render(request, "index.html", {
        "table_data": table_data,
        "periods": periods,
        "symbol": symbol,
        "message": message
    })
# ---------------- LOGIN ----------------
def login_page(request):

    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("/")
        else:
            return render(request, "login.html", {"error": "Invalid credentials"})

    return render(request, "login.html")
    


# ---------------- SEARCH ----------------

@login_required(login_url='login')
def search(request):

    if request.method == "POST":

        symbol = request.POST.get("symbol")

        if not symbol:
            return render(request, "search.html", {"error": "Enter symbol"})

        symbol = symbol.strip().upper()

        rows, error = scrape_company(symbol)

        if error:
            message = error
        else:
            message = f"✅ {rows} records inserted for {symbol}"

        return redirect(f"/?msg={message}&symbol={symbol}")

    return render(request, "search.html")

def logout_view(request):
    logout(request)
    return redirect('login')

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            return render(request, "register.html", {"error": "User already exists"})

        User.objects.create_user(username=username, password=password)
        return redirect('login')

    return render(request, "register.html")