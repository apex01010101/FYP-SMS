from django.urls import path
from . import views
urlpatterns = [
    path("",          views.reports_index,   name="reports-index"),
    path("sales/",    views.sales_report,    name="report-sales"),
    path("purchase/", views.purchase_report, name="report-purchase"),
    path("expense/",  views.expense_report,  name="report-expense"),
    path("profit/",   views.profit_report,   name="report-profit"),
]
