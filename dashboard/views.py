from django.shortcuts import render
from user.decorators import seller_required
import datetime
from decimal import Decimal


@seller_required
def index(request):
    from sales.models    import Sale
    from expenses.models import Expense
    from products.models import Product
    from customers.models import Customer
    from suppliers.models import Supplier

    today = datetime.date.today()

    today_sales    = Sale.objects.filter(sale_date=today)
    today_revenue  = sum(s.total_amount  for s in today_sales)
    today_profit   = sum(sum(i.profit for i in s.items.all()) for s in today_sales)
    today_invoices = today_sales.count()

    stock_value   = sum(p.stock_value for p in Product.objects.all())
    low_stock     = [p for p in Product.objects.all() if p.is_low_stock]

    # 7-day chart data
    chart_labels, chart_sales, chart_expenses = [], [], []
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        chart_labels.append(day.strftime('%a'))
        day_rev = sum(s.total_amount for s in Sale.objects.filter(sale_date=day))
        day_exp = sum(e.amount for e in Expense.objects.filter(date=day))
        chart_sales.append(float(day_rev))
        chart_expenses.append(float(day_exp))

    context = {
        'today_revenue':   today_revenue,
        'today_invoices':  today_invoices,
        'today_profit':    today_profit,
        'stock_value':     stock_value,
        'low_stock_items': low_stock[:5],
        'low_stock_count': len(low_stock),
        'total_customers': Customer.objects.count(),
        'total_suppliers': Supplier.objects.count(),
        'chart_labels':    chart_labels,
        'chart_sales':     chart_sales,
        'chart_expenses':  chart_expenses,
        'recent_sales':    today_sales.order_by('-created_at')[:5],
    }
    return render(request, 'dashboard/index.html', context)
