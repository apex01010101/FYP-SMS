from django.shortcuts import render
from user.decorators import seller_required
from .models import Transaction
from customers.models import Customer
from suppliers.models import Supplier
from decimal import Decimal
import datetime


@seller_required
def accounting_index(request):
    from sales.models    import Sale
    from expenses.models import Expense

    today = datetime.date.today()

    # Build cashbook with running balance
    all_tx   = Transaction.objects.order_by('date', 'created_at')
    cashbook = []
    running  = Decimal('0.00')
    for tx in all_tx:
        running += tx.inflow - tx.outflow
        cashbook.append({'tx': tx, 'balance': running})
    cashbook_display = list(reversed(cashbook))[:100]

    # Date filter
    date_from = request.GET.get('from', '')
    date_to   = request.GET.get('to',   '')
    filtered_tx = Transaction.objects.all()
    if date_from:
        filtered_tx = filtered_tx.filter(date__gte=date_from)
    if date_to:
        filtered_tx = filtered_tx.filter(date__lte=date_to)

    total_inflow  = sum(t.inflow  for t in Transaction.objects.all())
    total_outflow = sum(t.outflow for t in Transaction.objects.all())

    # Receivables
    receivables = [c for c in Customer.objects.all() if c.balance_due > 0]

    # Payables
    payables = [s for s in Supplier.objects.all() if s.balance_due > 0]

    # Monthly P&L
    month_sales = Sale.objects.filter(sale_date__month=today.month)
    revenue     = sum(s.total_amount for s in month_sales)
    cogs        = sum(
        sum(i.cost_price * i.quantity for i in s.items.all())
        for s in month_sales
    )
    gross_profit   = revenue - cogs
    month_expenses = sum(
        e.amount for e in Expense.objects.filter(date__month=today.month)
    )
    net_profit = gross_profit - month_expenses

    context = {
        'cashbook':         cashbook_display,
        'total_inflow':     total_inflow,
        'total_outflow':    total_outflow,
        'cash_in_hand':     running,
        'receivables':      receivables,
        'total_receivable': sum(c.balance_due for c in receivables),
        'payables':         payables,
        'total_payable':    sum(s.balance_due for s in payables),
        'revenue':          revenue,
        'cogs':             cogs,
        'gross_profit':     gross_profit,
        'month_expenses':   month_expenses,
        'net_profit':       net_profit,
        'profit_margin':    round(net_profit / revenue * 100, 1) if revenue else 0,
        'suppliers':        Supplier.objects.all(),
        'customers':        Customer.objects.filter(status='Active'),
        'date_from':        date_from,
        'date_to':          date_to,
    }
    return render(request, 'accounting/accounting.html', context)
