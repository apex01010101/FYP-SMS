from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from user.decorators import seller_required, customer_required
from user.models import UserProfile
from .models import Customer
from accounting.models import Transaction
import datetime
from decimal import Decimal


# ══ SELLER: Customer Management ══════════════════════════════

@seller_required
def customer_list(request):
    customers = Customer.objects.all().order_by("-created_at")
    q = request.GET.get("q", "")
    if q:
        customers = customers.filter(name__icontains=q)
    ctype = request.GET.get("type", "")
    if ctype:
        customers = customers.filter(customer_type=ctype)
    all_c = Customer.objects.all()
    context = {
        "customers":         customers,
        "total_customers":   Customer.objects.count(),
        "total_receivable":  sum(c.balance_due for c in all_c),
        "active_count":      Customer.objects.filter(status="Active").count(),
        "new_this_month":    Customer.objects.filter(
            created_at__month=datetime.date.today().month).count(),
        "overdue_customers": [c for c in all_c if c.balance_due > 0][:5],
    }
    return render(request, "customers/customers.html", context)


@seller_required
def customer_add(request):
    if request.method == "POST":
        name          = request.POST.get("name", "").strip()
        phone         = request.POST.get("phone", "").strip()
        email         = request.POST.get("email", "").strip()
        address       = request.POST.get("address", "").strip()
        customer_type = request.POST.get("customer_type", "Retail")
        credit_limit  = request.POST.get("credit_limit")  or 0
        opening_bal   = request.POST.get("opening_balance") or 0
        notes         = request.POST.get("notes", "").strip()
        create_login  = request.POST.get("create_login")

        if not name:
            messages.error(request, "Customer name is required.")
            return redirect("customer-list")

        user_obj = None
        if create_login:
            # Generate username from email, phone, or name — in that priority order
            if email:
                base_username = email.split("@")[0].lower().replace(" ", "_")
            elif phone:
                # Use digits only from phone
                digits = "".join(c for c in phone if c.isdigit())
                base_username = f"cust_{digits[-7:]}" if digits else None
            else:
                base_username = None

            if not base_username:
                # Fallback: use customer name (lowercase, no spaces)
                base_username = name.lower().replace(" ", "_").replace(".", "")

            # Ensure uniqueness
            username = base_username
            counter  = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user_obj = User.objects.create_user(
                username=username, email=email,
                password="customer123", first_name=name,
            )
            # Set customer role on the profile (signal creates it as seller by default)
            try:
                user_obj.profile.role    = "customer"
                user_obj.profile.phone   = phone
                user_obj.profile.address = address
                user_obj.profile.save()
            except Exception:
                from user.models import UserProfile
                UserProfile.objects.update_or_create(
                    user=user_obj,
                    defaults={"role": "customer", "phone": phone, "address": address}
                )

        Customer.objects.create(
            user=user_obj, name=name, phone=phone, email=email,
            address=address, customer_type=customer_type,
            credit_limit=credit_limit, opening_balance=opening_bal, notes=notes,
        )

        if create_login and user_obj:
            messages.success(
                request,
                f'Customer "{name}" added with login access. ' +
                f'Username: {user_obj.username} | Password: customer123'
            )
        else:
            messages.success(request, f'Customer "{name}" added.')
    return redirect("customer-list")


@seller_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        customer.name          = request.POST.get("name",          customer.name)
        customer.phone         = request.POST.get("phone",         customer.phone)
        customer.email         = request.POST.get("email",         customer.email)
        customer.address       = request.POST.get("address",       customer.address)
        customer.customer_type = request.POST.get("customer_type", customer.customer_type)
        customer.credit_limit  = request.POST.get("credit_limit",  customer.credit_limit) or 0
        customer.status        = request.POST.get("status",        customer.status)
        customer.notes         = request.POST.get("notes",         customer.notes)
        customer.save()
        messages.success(request, f'Customer "{customer.name}" updated.')
    return redirect("customer-list")


@seller_required
def customer_delete(request, pk):
    if request.method == "POST":
        customer = get_object_or_404(Customer, pk=pk)
        name = customer.name
        if customer.user:
            customer.user.delete()
        customer.delete()
        messages.success(request, f'Customer "{name}" deleted.')
    return redirect("customer-list")


@seller_required
def customer_payment(request):
    if request.method == "POST":
        from sales.models import Sale
        customer_id = request.POST.get("customer")
        amount      = Decimal(request.POST.get("amount", "0") or "0")
        if amount <= 0:
            messages.error(request, "Payment amount must be greater than zero.")
            return redirect("customer-list")
        method      = request.POST.get("payment_method", "Cash")
        pay_date    = request.POST.get("payment_date") or datetime.date.today()

        customer  = get_object_or_404(Customer, pk=customer_id)

        # Prevent payment when nothing is due
        if customer.balance_due <= 0:
            messages.error(
                request,
                f"{customer.name} has no outstanding balance."
            )
            return redirect("customer-list")

        # Prevent overpayment
        if amount > customer.balance_due:
            messages.error(
                request,
                f"Payment cannot exceed balance due (Rs. {customer.balance_due:.2f})."
            )
            return redirect("customer-list")

        remaining = amount

        for sale in Sale.objects.filter(
            customer_id=customer_id
        ).order_by("created_at"):
            if remaining <= 0:
                break
            bal = sale.balance
            if bal > 0:
                pay = min(remaining, bal)
                sale.paid_amount += pay
                sale.save()
                remaining -= pay

        Transaction.objects.create(
            transaction_type="sale_payment",
            description=f"Payment received — {customer.name}",
            inflow=amount, outflow=0,
            date=pay_date,
            reference=f"PAY-CUST-{customer.pk}",
        )
        messages.success(request, f"Payment of Rs. {amount} recorded for {customer.name}.")
    return redirect("customer-list")


@seller_required
def customer_ledger(request, pk):
    """
    Full ledger for one customer showing every sale and payment
    with running balance.
    """
    from sales.models import Sale

    customer = get_object_or_404(Customer, pk=pk)

    # Build ledger entries from sales
    entries  = []
    running  = Decimal("0.00")

    # Opening balance
    if customer.opening_balance:
        running += customer.opening_balance
        entries.append({
            "date":        customer.created_at.date(),
            "description": "Opening Balance",
            "reference":   "—",
            "debit":       customer.opening_balance,
            "credit":      Decimal("0.00"),
            "balance":     running,
            "type":        "opening",
        })

    # All sales — sorted oldest first for running balance
    sales = Sale.objects.filter(customer=customer).order_by("created_at")

    for sale in sales:
        # Debit entry for the sale
        running += sale.total_amount
        entries.append({
            "date":        sale.sale_date,
            "description": f"Sale — {sale.item_count} item(s)",
            "reference":   sale.invoice_number,
            "debit":       sale.total_amount,
            "credit":      Decimal("0.00"),
            "balance":     running,
            "type":        "sale",
        })
        # Credit entry for payments made
        if sale.paid_amount > 0:
            running -= sale.paid_amount
            entries.append({
                "date":        sale.sale_date,
                "description": f"Payment — {sale.payment_method}",
                "reference":   sale.invoice_number,
                "debit":       Decimal("0.00"),
                "credit":      sale.paid_amount,
                "balance":     running,
                "type":        "payment",
            })

    # Date filter
    date_from = request.GET.get("from", "")
    date_to   = request.GET.get("to",   "")
    if date_from:
        try:
            df = datetime.date.fromisoformat(date_from)
            entries = [e for e in entries if e["date"] >= df]
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.date.fromisoformat(date_to)
            entries = [e for e in entries if e["date"] <= dt]
        except ValueError:
            pass

    context = {
        "customer":    customer,
        "entries":     entries,
        "sales":       sales,
        "date_from":   date_from,
        "date_to":     date_to,
    }
    return render(request, "customers/ledger.html", context)


# ══ CUSTOMER PORTAL VIEWS ════════════════════════════════════

@customer_required
def customer_dashboard(request):
    customer = _get_customer(request)
    if not customer:
        messages.error(request, "No customer profile linked to your account.")
        return redirect("user-login")

    from sales.models  import Sale
    from orders.models import Order
    from products.models import Product

    recent_orders   = Order.objects.filter(customer=customer).order_by("-created_at")[:5]
    recent_invoices = Sale.objects.filter(customer=customer).order_by("-created_at")[:5]

    context = {
        "customer":           customer,
        "total_orders":       Order.objects.filter(customer=customer).count(),
        "pending_orders":     Order.objects.filter(customer=customer, status="pending").count(),
        "confirmed_orders":   Order.objects.filter(customer=customer, status="confirmed").count(),
        "total_purchases":    customer.total_purchases,
        "balance_due":        customer.balance_due,
        "recent_orders":      recent_orders,
        "recent_invoices":    recent_invoices,
    }
    return render(request, "customer_portal/dashboard.html", context)


@customer_required
def portal_products(request):
    from products.models import Product, Category
    products   = Product.objects.filter(is_active=True).select_related("category")
    categories = Category.objects.all()
    q = request.GET.get("q", "")
    if q:
        products = products.filter(name__icontains=q)
    cat = request.GET.get("category", "")
    if cat:
        products = products.filter(category_id=cat)
    context = {
        "products":   products,
        "categories": categories,
        "customer":   _get_customer(request),
    }
    return render(request, "customer_portal/products.html", context)


@customer_required
def portal_orders(request):
    from orders.models import Order
    customer = _get_customer(request)
    orders   = Order.objects.filter(customer=customer).order_by("-created_at")
    return render(request, "customer_portal/orders.html", {
        "orders": orders, "customer": customer,
    })


@customer_required
def portal_place_order(request):
    from orders.models import Order, OrderItem
    if request.method == "POST":
        customer   = _get_customer(request)
        prod_ids   = request.POST.getlist("product[]")
        quantities = request.POST.getlist("quantity[]")
        notes      = request.POST.get("notes", "").strip()

        valid_items = [(pid, qty) for pid, qty in zip(prod_ids, quantities)
                       if pid and qty and int(qty) > 0]
        if not valid_items:
            messages.error(request, "Please select at least one product.")
            return redirect("portal-products")

        order = Order.objects.create(
            customer=customer,
            customer_name=customer.name,
            notes=notes,
        )
        for pid, qty in valid_items:
            OrderItem.objects.create(order=order, product_id=pid, quantity=int(qty))

        messages.success(
            request,
            f"{order.order_number} placed! We will review and confirm it shortly."
        )
        return redirect("portal-orders")
    return redirect("portal-products")


@customer_required
def portal_ledger(request):
    from sales.models import Sale
    customer = _get_customer(request)
    sales    = Sale.objects.filter(customer=customer).order_by("created_at")

    # Build running ledger
    entries = []
    running = customer.opening_balance or Decimal("0.00")
    if running:
        entries.append({"label": "Opening Balance", "debit": running,
                        "credit": Decimal("0.00"), "balance": running, "type": "opening"})
    for sale in sales:
        running += sale.total_amount
        entries.append({"label": sale.invoice_number, "date": sale.sale_date,
                        "debit": sale.total_amount, "credit": Decimal("0.00"),
                        "balance": running, "type": "sale"})
        if sale.paid_amount > 0:
            running -= sale.paid_amount
            entries.append({"label": "Payment", "date": sale.sale_date,
                            "debit": Decimal("0.00"), "credit": sale.paid_amount,
                            "balance": running, "type": "payment"})

    return render(request, "customer_portal/ledger.html", {
        "customer": customer, "entries": entries, "sales": sales,
    })


def _get_customer(request):
    try:
        return request.user.customer
    except Exception:
        return None
