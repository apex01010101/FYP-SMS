from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from user.decorators import seller_required
from decimal import Decimal
from .models import Sale, SaleItem
from products.models import Product, StockBatch
from customers.models import Customer
from accounting.models import Transaction
import datetime


def _deduct_fifo(product, qty_needed):
    """Deduct stock using FIFO. Returns weighted average cost."""
    batches    = StockBatch.objects.filter(
        product=product, quantity__gt=0).order_by('date_received')
    remaining  = qty_needed
    total_cost = Decimal('0.00')

    for batch in batches:
        if remaining <= 0:
            break
        take           = min(batch.quantity, remaining)
        total_cost    += Decimal(str(take)) * batch.cost_price
        batch.quantity -= take
        batch.save()
        remaining      -= take

    if remaining > 0:
        messages.warning_text = f'Warning: {remaining} units of {product.name} were out of stock.'

    return (total_cost / Decimal(str(qty_needed))) if qty_needed else Decimal('0.00')


@seller_required
def sale_list(request):
    sales     = Sale.objects.select_related('customer').prefetch_related('items').order_by('-created_at')
    customers = Customer.objects.filter(status='Active')
    products  = Product.objects.filter(is_active=True)
    today     = datetime.date.today()

    q = request.GET.get('q', '')
    if q:
        sales = sales.filter(customer_name__icontains=q)

    status_f = request.GET.get('status', '')
    if status_f:
        pk_list = [s.pk for s in Sale.objects.all() if s.status == status_f]
        sales   = Sale.objects.filter(pk__in=pk_list).order_by('-created_at')

    today_sales = Sale.objects.filter(sale_date=today)

    context = {
        'sales':             sales,
        'customers':         customers,
        'products':          products,
        'today_revenue':     sum(s.total_amount for s in today_sales),
        'today_invoices':    today_sales.count(),
        'monthly_revenue':   sum(
            s.total_amount for s in Sale.objects.filter(
                sale_date__month=today.month)),
        'unpaid_count':      len([s for s in Sale.objects.all()
                                  if s.status != 'paid']),
        'today_profit':      sum(
            sum(i.profit for i in s.items.all()) for s in today_sales),
        'today_credit_sales': sum(s.balance for s in today_sales),
    }
    return render(request, 'sales/sales.html', context)


@seller_required
def sale_add(request):
    if request.method == 'POST':
        customer_id    = request.POST.get('customer') or None
        tax_percent    = Decimal(request.POST.get('tax_percent', '0') or '0')
        paid_amount    = Decimal(request.POST.get('paid_amount', '0') or '0')
        payment_method = request.POST.get('payment_method', 'Cash')
        notes          = request.POST.get('notes', '').strip()

        prod_ids   = request.POST.getlist('product[]')
        quantities = request.POST.getlist('quantity[]')
        prices     = request.POST.getlist('sale_price[]')
        discounts  = request.POST.getlist('discount[]')

        if not any(p for p in prod_ids if p):
            messages.error(request, 'Please add at least one product.')
            return redirect('sale-list')

        customer_name = 'Walk-in'
        if customer_id:
            try:
                customer_name = Customer.objects.get(pk=customer_id).name
            except Customer.DoesNotExist:
                customer_id = None

        #adding restriction for less sale price
        for pid, qty, price, disc in zip(prod_ids, quantities, prices, discounts):
            if pid and not qty:
                messages.error(
                    request,
                    'Quantity cannot be empty.'
                )
                return redirect('sale-list')

            if pid and not price:
                messages.error(
                    request,
                    'Sale price cannot be empty.'
                )
                return redirect('sale-list')

            if not pid:
                continue

            qty = int(qty)

            if qty <= 0:
                messages.error(
                    request,
                    'Quantity must be greater than zero.'
                )
                return redirect('sale-list')
                
            product = get_object_or_404(Product, pk=pid)
            price = Decimal(price)

            if price < Decimal(str(product.avg_cost_price)):
                messages.error(
                    request,
                    f'{product.name}: Sale price (Rs. {price}) cannot be lower than average cost price (Rs. {product.avg_cost_price}).'
                )
                return redirect('sale-list')

            

        sale = Sale.objects.create(
            customer_id=customer_id, customer_name=customer_name,
            tax_percent=tax_percent, paid_amount=paid_amount,
            payment_method=payment_method, notes=notes,
        )

        for pid, qty, price, disc in zip(prod_ids, quantities, prices, discounts):
            if pid and qty and price:
                qty      = int(qty)
                price    = Decimal(price)
                disc     = Decimal(disc or '0')
                product  = get_object_or_404(Product, pk=pid)
                
                avg_cost = _deduct_fifo(product, qty)

                SaleItem.objects.create(
                    sale=sale, product=product,
                    quantity=qty, sale_price=price,
                    discount=disc, cost_price=avg_cost,
                )

        if paid_amount > 0:
            Transaction.objects.create(
                transaction_type='sale',
                description=f'Sale — {sale.customer_name} ({sale.invoice_number})',
                inflow=paid_amount, outflow=0,
                date=sale.sale_date,
                reference=sale.invoice_number,
                sale_id=sale.pk,
            )

        messages.success(request, f'{sale.invoice_number} created successfully.')
    return redirect('sale-list')


@seller_required
def sale_delete(request, pk):
    if request.method == 'POST':
        sale = get_object_or_404(Sale, pk=pk)
        # Restore stock
        for item in sale.items.all():
            StockBatch.objects.create(
                product=item.product,
                cost_price=item.cost_price,
                quantity=item.quantity,
            )
        Transaction.objects.filter(sale_id=sale.pk).delete()
        inv = sale.invoice_number
        sale.delete()
        messages.success(request, f'{inv} deleted. Stock restored.')
    return redirect('sale-list')


@seller_required
def sale_payment(request):
    if request.method == 'POST':
        sale_id  = request.POST.get('invoice')
        amount   = Decimal(request.POST.get('amount', '0') or '0')
        pay_date = request.POST.get('payment_date') or datetime.date.today()
        sale     = get_object_or_404(Sale, pk=sale_id)

        apply = min(amount, sale.balance)
        sale.paid_amount += apply
        sale.save()

        Transaction.objects.create(
            transaction_type='sale_payment',
            description=f'Payment — {sale.customer_name} ({sale.invoice_number})',
            inflow=apply, outflow=0,
            date=pay_date,
            reference=sale.invoice_number,
            sale_id=sale.pk,
        )
        messages.success(request, f'Payment of Rs. {apply} recorded.')
    return redirect('sale-list')


@seller_required
def sale_invoice(request, pk):
    """View a single invoice detail."""
    sale = get_object_or_404(Sale, pk=pk)
    return render(request, 'sales/invoice.html', {'sale': sale})
