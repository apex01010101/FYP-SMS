from django.shortcuts import render
from user.decorators import seller_required
from decimal import Decimal
import datetime


PERIOD_CHOICES = [
    ("today",   "Today"),
    ("week",    "Week"),
    ("month",   "Month"),
    ("3month",  "3 Months"),
    ("6month",  "6 Months"),
    ("all",     "All Time"),
    ("custom",  "Custom"),
]


def _get_period(request):
    today  = datetime.date.today()
    period = request.GET.get("period", "month")
    if period == "today":
        return today, today, "Today"
    elif period == "week":
        return today - datetime.timedelta(days=today.weekday()), today, "This Week"
    elif period == "month":
        return today.replace(day=1), today, "This Month"
    elif period == "3month":
        return today - datetime.timedelta(days=90), today, "Last 3 Months"
    elif period == "6month":
        return today - datetime.timedelta(days=180), today, "Last 6 Months"
    elif period == "all":
        return datetime.date(2000, 1, 1), today, "All Time"
    elif period == "custom":
        try:
            df = datetime.date.fromisoformat(request.GET.get("from", ""))
            dt = datetime.date.fromisoformat(request.GET.get("to",   ""))
            return df, dt, f"{df} to {dt}"
        except ValueError:
            pass
    return today.replace(day=1), today, "This Month"


def _build_chart(d_from, d_to):
    """
    Build day-by-day (or week/month) chart labels + revenue + profit + expense.
    Auto-groups to keep chart readable.
    """
    from sales.models    import Sale
    from expenses.models import Expense
    delta = (d_to - d_from).days
    labels, rev_data, prof_data, exp_data = [], [], [], []

    if delta <= 31:
        # Day by day
        cur = d_from
        while cur <= d_to:
            day_sales = Sale.objects.filter(sale_date=cur)
            rev  = float(sum(s.total_amount for s in day_sales))
            prof = float(sum(sum(i.profit for i in s.items.all()) for s in day_sales))
            exp  = float(sum(e.amount for e in Expense.objects.filter(date=cur)))
            labels.append(cur.strftime("%d %b"))
            rev_data.append(rev); prof_data.append(prof); exp_data.append(exp)
            cur += datetime.timedelta(days=1)
    elif delta <= 90:
        # Week by week
        cur = d_from
        while cur <= d_to:
            end = min(cur + datetime.timedelta(days=6), d_to)
            ws  = Sale.objects.filter(sale_date__range=[cur, end])
            rev  = float(sum(s.total_amount for s in ws))
            prof = float(sum(sum(i.profit for i in s.items.all()) for s in ws))
            exp  = float(sum(e.amount for e in Expense.objects.filter(date__range=[cur, end])))
            labels.append(cur.strftime("%d %b"))
            rev_data.append(rev); prof_data.append(prof); exp_data.append(exp)
            cur += datetime.timedelta(days=7)
    else:
        # Month by month
        import calendar
        cur = d_from.replace(day=1)
        while cur <= d_to:
            last = calendar.monthrange(cur.year, cur.month)[1]
            end  = min(cur.replace(day=last), d_to)
            ms   = Sale.objects.filter(sale_date__range=[cur, end])
            rev  = float(sum(s.total_amount for s in ms))
            prof = float(sum(sum(i.profit for i in s.items.all()) for s in ms))
            exp  = float(sum(e.amount for e in Expense.objects.filter(date__range=[cur, end])))
            labels.append(cur.strftime("%b %Y"))
            rev_data.append(rev); prof_data.append(prof); exp_data.append(exp)
            cur = (cur.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)

    return labels, rev_data, prof_data, exp_data


@seller_required
def reports_index(request):
    return sales_report(request)


# ── 1. SALES REPORT ───────────────────────────────────────────────────────────
@seller_required
def sales_report(request):
    from sales.models    import Sale, SaleItem
    from products.models import Category

    d_from, d_to, plabel = _get_period(request)
    period = request.GET.get("period", "month")

    period_sales  = Sale.objects.filter(sale_date__range=[d_from, d_to]).order_by("-sale_date")
    revenue       = sum(s.total_amount for s in period_sales)
    cogs          = sum(sum(i.cost_price * i.quantity for i in s.items.all()) for s in period_sales)
    gross_profit  = revenue - cogs
    invoice_count = period_sales.count()
    avg_sale      = round(revenue / invoice_count, 2) if invoice_count else 0

    # By category
    cat_data = []
    for cat in Category.objects.all():
        items = SaleItem.objects.filter(product__category=cat, sale__sale_date__range=[d_from, d_to])
        rev  = sum(i.line_total for i in items)
        prof = sum(i.profit     for i in items)
        if rev > 0:
            cat_data.append({"name": cat.name, "revenue": rev, "profit": prof,
                             "margin": round(prof / rev * 100, 1)})
    cat_data.sort(key=lambda x: x["revenue"], reverse=True)

    chart_labels, chart_rev, chart_prof, chart_exp = _build_chart(d_from, d_to)

    ctx = {
        "active_tab": "sales", "period": period, "period_label": plabel,
        "date_from": d_from, "date_to": d_to,
        "period_sales": period_sales, "revenue": revenue, "cogs": cogs,
        "gross_profit": gross_profit, "invoice_count": invoice_count,
        "avg_sale": avg_sale,
        "profit_margin": round(gross_profit / revenue * 100, 1) if revenue else 0,
        "cat_data": cat_data,
        "chart_labels": chart_labels, "chart_rev": chart_rev,
        "chart_prof": chart_prof, "chart_exp": chart_exp,
    }
    ctx["period_choices"] = PERIOD_CHOICES
    return render(request, "reports/sales_report.html", ctx)


# ── 2. PURCHASE REPORT ────────────────────────────────────────────────────────
@seller_required
def purchase_report(request):
    from suppliers.models import Supplier, Purchase
    from products.models  import StockBatch

    d_from, d_to, plabel = _get_period(request)
    period = request.GET.get("period", "month")

    period_pur      = Purchase.objects.filter(created_at__date__range=[d_from, d_to]).order_by("-created_at")
    total_purchased = sum(p.get_total()  for p in period_pur)
    total_paid      = sum(p.paid_amount  for p in period_pur)
    total_due       = total_purchased - total_paid

    # Per supplier
    sup_data = []
    for s in Supplier.objects.all():
        sp = period_pur.filter(supplier=s)
        t  = sum(p.get_total() for p in sp)
        if t > 0:
            sup_data.append({"supplier": s, "count": sp.count(), "total": t,
                             "paid": sum(p.paid_amount for p in sp), "due": t - sum(p.paid_amount for p in sp)})
    sup_data.sort(key=lambda x: x["total"], reverse=True)

    # Per product bought
    prod_data = []
    from products.models import Product
    for p in Product.objects.all():
        batches = StockBatch.objects.filter(product=p, date_received__date__range=[d_from, d_to])
        qty   = sum(b.quantity   for b in batches)
        spent = sum(b.cost_price * b.quantity for b in batches)
        if qty > 0:
            prod_data.append({"product": p, "qty": qty, "spent": spent,
                             "avg_cost": round(spent/qty, 2)})
    prod_data.sort(key=lambda x: x["spent"], reverse=True)

    # Chart
    import calendar
    chart_labels, chart_pur = [], []
    cur = d_from.replace(day=1)
    while cur <= d_to:
        last = calendar.monthrange(cur.year, cur.month)[1]
        end  = min(cur.replace(day=last), d_to)
        mp   = Purchase.objects.filter(created_at__date__range=[cur, end])
        chart_labels.append(cur.strftime("%b %Y"))
        chart_pur.append(float(sum(p.get_total() for p in mp)))
        cur = (cur.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)

    ctx = {
        "active_tab": "purchase", "period": period, "period_label": plabel,
        "date_from": d_from, "date_to": d_to,
        "period_pur": period_pur, "total_purchased": total_purchased,
        "total_paid": total_paid, "total_due": total_due,
        "sup_data": sup_data, "prod_data": prod_data,
        "chart_labels": chart_labels, "chart_pur": chart_pur,
    }
    ctx["period_choices"] = PERIOD_CHOICES
    return render(request, "reports/purchase_report.html", ctx)


# ── 3. EXPENSE REPORT ─────────────────────────────────────────────────────────
@seller_required
def expense_report(request):
    from expenses.models import Expense, ExpenseCategory

    d_from, d_to, plabel = _get_period(request)
    period = request.GET.get("period", "month")

    period_exp = Expense.objects.filter(date__range=[d_from, d_to]).order_by("-date")
    total_exp  = sum(e.amount for e in period_exp)

    cat_data = []
    for cat in ExpenseCategory.objects.all():
        exps  = period_exp.filter(category=cat)
        total = sum(e.amount for e in exps)
        if total > 0:
            cat_data.append({"category": cat, "count": exps.count(), "total": total,
                             "pct": round(total / total_exp * 100, 1) if total_exp else 0})
    cat_data.sort(key=lambda x: x["total"], reverse=True)

    # Chart: daily expense trend
    chart_labels, chart_exp = [], []
    cur = d_from
    while cur <= d_to:
        chart_labels.append(cur.strftime("%d %b") if (d_to - d_from).days <= 31 else cur.strftime("%b %Y"))
        chart_exp.append(float(sum(e.amount for e in Expense.objects.filter(date=cur))))
        cur += datetime.timedelta(days=1)
        if (d_to - d_from).days > 31:
            # skip to next month
            import calendar
            last = calendar.monthrange(cur.year, cur.month)[1]
            cur  = (cur.replace(day=1, month=cur.month) + datetime.timedelta(days=last)).replace(day=1)
            if cur > d_to:
                break

    ctx = {
        "active_tab": "expense", "period": period, "period_label": plabel,
        "date_from": d_from, "date_to": d_to,
        "period_exp": period_exp, "total_exp": total_exp,
        "cat_data": cat_data,
        "chart_labels": chart_labels, "chart_exp": chart_exp,
    }
    ctx["period_choices"] = PERIOD_CHOICES
    return render(request, "reports/expense_report.html", ctx)


# ── 4. PROFIT REPORT ──────────────────────────────────────────────────────────
@seller_required
def profit_report(request):
    from sales.models    import Sale, SaleItem
    from products.models import Product, Category
    from expenses.models import Expense

    d_from, d_to, plabel = _get_period(request)
    period = request.GET.get("period", "month")

    period_sales  = Sale.objects.filter(sale_date__range=[d_from, d_to])
    revenue       = sum(s.total_amount for s in period_sales)
    cogs          = sum(sum(i.cost_price * i.quantity for i in s.items.all()) for s in period_sales)
    gross_profit  = revenue - cogs
    total_expense = sum(e.amount for e in Expense.objects.filter(date__range=[d_from, d_to]))
    net_profit    = gross_profit - total_expense

    # Per product
    prod_profit = []
    for p in Product.objects.all():
        items = SaleItem.objects.filter(product=p, sale__sale_date__range=[d_from, d_to])
        rev   = sum(i.line_total for i in items)
        prof  = sum(i.profit     for i in items)
        qty   = sum(i.quantity   for i in items)
        if qty > 0:
            prod_profit.append({"product": p, "qty": qty, "revenue": rev, "profit": prof,
                                "margin": round(prof / rev * 100, 1) if rev else 0})
    prod_profit.sort(key=lambda x: x["profit"], reverse=True)

    # Per category
    cat_profit = []
    for cat in Category.objects.all():
        items = SaleItem.objects.filter(product__category=cat, sale__sale_date__range=[d_from, d_to])
        rev  = sum(i.line_total for i in items)
        prof = sum(i.profit     for i in items)
        if rev > 0:
            cat_profit.append({"category": cat, "revenue": rev, "profit": prof,
                               "margin": round(prof / rev * 100, 1)})
    cat_profit.sort(key=lambda x: x["profit"], reverse=True)

    # Chart
    chart_labels, _, chart_prof, _ = _build_chart(d_from, d_to)

    ctx = {
        "active_tab": "profit", "period": period, "period_label": plabel,
        "date_from": d_from, "date_to": d_to,
        "revenue": revenue, "cogs": cogs, "gross_profit": gross_profit,
        "total_expense": total_expense, "net_profit": net_profit,
        "profit_margin": round(net_profit / revenue * 100, 1) if revenue else 0,
        "prod_profit": prod_profit[:20], "cat_profit": cat_profit,
        "chart_labels": chart_labels, "chart_prof": chart_prof,
    }
    ctx["period_choices"] = PERIOD_CHOICES
    return render(request, "reports/profit_report.html", ctx)
