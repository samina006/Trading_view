from django.db import models

class FinancialData(models.Model):
    symbol = models.CharField(max_length=20)
    category = models.CharField(max_length=200)
    metric = models.CharField(max_length=200)
    period = models.CharField(max_length=100)
    value = models.TextField()
    numeric_value = models.FloatField(null=True, blank=True)
    scrape_date = models.DateTimeField()

    def __str__(self):
        return self.symbol