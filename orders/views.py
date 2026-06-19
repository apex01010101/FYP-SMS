from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from user.decorators import seller_required
from .models import Order, OrderItem
from customers.models import Customer
from products.models import Product


@seller_required
def order_list(request):
    orders    = Order.objects.select_related("customer") \
                             .prefetch_related("items__product") \
                             .order_by("-created_at")
    customers = Customer.objects.filter(status="Active")
    products  = Product.objects.filter(is_active=True)

    q = request.GET.get("q", "")
    if q:
        orders = orders.filter(customer_name__icontains=q)

    status_f = request.GET.get("status", "")
    if status_f:
        orders = orders.filter(status=status_f)

    context = {
        "orders":           orders,
        "customers":        customers,
        "products":         products,
        "pending_orders":   Order.objects.filter(status="pending").count(),
        "confirmed_orders": Order.objects.filter(status="confirmed").count(),
        "converted_orders": Order.objects.filter(status="converted").count(),
        "cancelled_orders": Order.objects.filter(status="cancelled").count(),
        "total_orders":     Order.objects.count(),
    }
    return render(request, "orders/orders.html", context)


@seller_required
def order_add(request):
    if request.method == "POST":
        customer_id = request.POST.get("customer") or None
        notes       = request.POST.get("notes", "").strip()
        prod_ids    = request.POST.getlist("product[]")
        quantities  = request.POST.getlist("quantity[]")
        customer_name = "Walk-in"
        if customer_id:
            try:
                customer_name = Customer.objects.get(pk=customer_id).name
            except Customer.DoesNotExist:
                customer_id = None
        if not any(p for p in prod_ids if p):
            messages.error(request, "Please add at least one product.")
            return redirect("order-list")
        order = Order.objects.create(
            customer_id=customer_id, customer_name=customer_name, notes=notes,
        )
        for pid, qty in zip(prod_ids, quantities):
            if pid and qty and int(qty) > 0:
                OrderItem.objects.create(order=order, product_id=pid, quantity=int(qty))
        messages.success(request, f"{order.order_number} created.")
    return redirect("order-list")


@seller_required
def order_confirm(request, pk):
    """Accept a pending order — does NOT deduct stock yet."""
    if request.method == "POST":
        order = get_object_or_404(Order, pk=pk)
        if order.status != "pending":
            messages.error(request, f"{order.order_number} is not pending.")
            return redirect("order-list")
        order.status = "confirmed"
        order.save()
        messages.success(request, f"{order.order_number} confirmed. Convert to invoice when ready.")
    return redirect("order-list")


@seller_required
def order_convert(request, pk):
    """Convert confirmed/pending order to Sale invoice. Deducts stock via FIFO."""
    if request.method == "POST":
        from sales.views import _deduct_fifo
        from sales.models import Sale, SaleItem

        order = get_object_or_404(Order, pk=pk)
        if order.status in ("converted", "cancelled"):
            messages.error(request, f"{order.order_number} cannot be converted.")
            return redirect("order-list")

        # Stock check
        for item in order.items.all():
            if item.product.current_stock < item.quantity:
                messages.error(
                    request,
                    f"Insufficient stock for \"{item.product.name}\". "
                    f"Available: {item.product.current_stock}, Needed: {item.quantity}."
                )
                return redirect("order-list")

        sale = Sale.objects.create(
            customer_id=order.customer_id,
            customer_name=order.customer_name,
            paid_amount=0,
            payment_method="Credit",
            notes=f"Converted from {order.order_number}",
        )
        for item in order.items.all():
            avg_cost = _deduct_fifo(item.product, item.quantity)
            SaleItem.objects.create(
                sale=sale, product=item.product,
                quantity=item.quantity,
                sale_price=item.product.sale_price,
                cost_price=avg_cost,
            )
        order.status = "converted"
        order.save()
        messages.success(request, f"{order.order_number} converted to {sale.invoice_number}. Record payment when received.")
    return redirect("order-list")


@seller_required
def order_cancel(request, pk):
    if request.method == "POST":
        order = get_object_or_404(Order, pk=pk)
        if order.status == "converted":
            messages.error(request, "Cannot cancel a converted order. Delete the invoice instead.")
            return redirect("order-list")
        order.status = "cancelled"
        order.save()
        messages.success(request, f"{order.order_number} cancelled.")
    return redirect("order-list")
