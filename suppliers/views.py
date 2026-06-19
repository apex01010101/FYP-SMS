from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from user.decorators import seller_required
from decimal import Decimal
from .models import Supplier, Purchase
from products.models import Product, StockBatch
from accounting.models import Transaction
import datetime


@seller_required
def supplier_list(request):
    suppliers = Supplier.objects.all().order_by('-created_at')
    q = request.GET.get('q', '')
    if q:
        suppliers = suppliers.filter(name__icontains=q)

    all_s = Supplier.objects.all()
    context = {
        'suppliers':            suppliers,
        'products':             Product.objects.filter(is_active=True),
        'total_suppliers':      Supplier.objects.count(),
        'active_suppliers':     Supplier.objects.count(),
        'total_payable':        abs(sum(s.balance_due for s in all_s)),
        'purchases_this_month': sum(
            p.get_total() for s in all_s
            for p in s.purchase_set.filter(
                created_at__month=datetime.date.today().month)
        ),
        'top_suppliers': sorted(all_s,
                                key=lambda s: s.total_purchased,
                                reverse=True)[:3],
    }
    return render(request, 'suppliers/suppliers.html', context)


@seller_required
def supplier_add(request):
    if request.method == 'POST':
        name    = request.POST.get('name', '').strip()
        phone   = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        notes   = request.POST.get('notes', '').strip()
        if not name:
            messages.error(request, 'Supplier name is required.')
            return redirect('supplier-list')
        Supplier.objects.create(name=name, phone=phone,
                                address=address, notes=notes)
        messages.success(request, f'Supplier "{name}" added.')
    return redirect('supplier-list')


@seller_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        supplier.name    = request.POST.get('name',    supplier.name)
        supplier.phone   = request.POST.get('phone',   supplier.phone)
        supplier.address = request.POST.get('address', supplier.address)
        supplier.notes   = request.POST.get('notes',   supplier.notes)
        supplier.save()
        messages.success(request, 'Supplier updated.')
    return redirect('supplier-list')


@seller_required
def supplier_delete(request, pk):
    if request.method == 'POST':
        supplier = get_object_or_404(Supplier, pk=pk)
        if supplier.purchase_set.exists():
            messages.error(request,
                           f'Cannot delete "{supplier.name}" — it has purchase records.')
        else:
            supplier.delete()
            messages.success(request, 'Supplier deleted.')
    return redirect('supplier-list')


@seller_required
def supplier_payment(request):
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        amount      = Decimal(request.POST.get('amount', '0') or '0')
        method      = request.POST.get('payment_method', 'Cash')
        pay_date    = request.POST.get('payment_date') or datetime.date.today()

        supplier  = get_object_or_404(Supplier, pk=supplier_id)
        if amount <= 0:
            messages.error(
                request,
                'Payment amount must be greater than zero.'
            )
            return redirect('supplier-list')
        # Prevent payment when nothing is due
        if supplier.balance_due <= 0:
            messages.error(
                request,
                f'{supplier.name} has no outstanding balance.'
            )
            return redirect('supplier-list')

        # Prevent overpayment
        if amount > supplier.balance_due:
            messages.error(
                request,
                f'Payment cannot exceed balance due (Rs. {supplier.balance_due:.2f}).'
            )
            return redirect('supplier-list')
        remaining = amount

        for purchase in Purchase.objects.filter(
            supplier=supplier
        ).order_by('created_at'):
            if remaining <= 0:
                break
            bal = purchase.balance_due
            if bal > 0:
                pay = min(remaining, bal)
                purchase.paid_amount += pay
                purchase.save()
                remaining -= pay

        Transaction.objects.create(
            transaction_type='supplier_payment',
            description=f'Payment to {supplier.name}',
            inflow=0, outflow=amount,
            date=pay_date,
            reference=f'PAY-SUP-{supplier.pk}',
        )
        messages.success(request, f'Payment of Rs. {amount} recorded for {supplier.name}.')
    return redirect('supplier-list')


@seller_required
def purchase_add(request):
    if request.method == 'POST':
        supplier_id    = request.POST.get('supplier')
        invoice_ref    = request.POST.get('invoice_ref', '').strip()
        paid_amount    = Decimal(request.POST.get('paid_amount', '0') or '0')
        payment_method = request.POST.get('payment_method', 'Cash')
        notes          = request.POST.get('notes', '').strip()

        prod_ids    = request.POST.getlist('product[]')
        quantities  = request.POST.getlist('quantity[]')
        cost_prices = request.POST.getlist('cost_price[]')

        if not supplier_id:
            messages.error(request, 'Please select a supplier.')
            return redirect('supplier-list')

        purchase = Purchase.objects.create(
            supplier_id=supplier_id, invoice_ref=invoice_ref,
            paid_amount=paid_amount, payment_method=payment_method,
            notes=notes,
        )

        total = Decimal('0.00')
        for pid, qty, cost in zip(prod_ids, quantities, cost_prices):
            if pid and qty and cost:
                qty  = int(qty)
                cost = Decimal(cost)
                StockBatch.objects.create(
                    product_id=pid, purchase=purchase,
                    cost_price=cost, quantity=qty,
                )
                total += cost * qty

        supplier = get_object_or_404(Supplier, pk=supplier_id)
        Transaction.objects.create(
            transaction_type='purchase',
            description=f'Stock purchase — {supplier.name}',
            inflow=0, outflow=total,
            date=datetime.date.today(),
            reference=str(purchase),
            purchase_id=purchase.pk,
        )
        messages.success(request, f'Purchase recorded. Stock updated.')
    return redirect('supplier-list')


@seller_required
def supplier_ledger(request, pk):
    """Full ledger for one supplier with running balance."""
    from decimal import Decimal
    supplier  = get_object_or_404(Supplier, pk=pk)
    purchases = Purchase.objects.filter(supplier=supplier).order_by("created_at")

    entries = []
    running = Decimal("0.00")

    for purchase in purchases:
        total = purchase.get_total()
        # We OWE this amount (outflow for us = debit on supplier ledger)
        running += total
        entries.append({
            "date":        purchase.created_at.date(),
            "description": f"Purchase — {purchase.invoice_ref or purchase}",
            "reference":   str(purchase),
            "debit":       total,
            "credit":      Decimal("0.00"),
            "balance":     running,
            "type":        "purchase",
        })
        if purchase.paid_amount > 0:
            running -= purchase.paid_amount
            entries.append({
                "date":        purchase.created_at.date(),
                "description": f"Payment — {purchase.payment_method}",
                "reference":   str(purchase),
                "debit":       Decimal("0.00"),
                "credit":      purchase.paid_amount,
                "balance":     running,
                "type":        "payment",
            })

    date_from = request.GET.get("from", "")
    date_to   = request.GET.get("to", "")

    context = {
        "supplier":   supplier,
        "entries":    entries,
        "purchases":  purchases,
        "date_from":  date_from,
        "date_to":    date_to,
    }
    return render(request, "suppliers/ledger.html", context)
