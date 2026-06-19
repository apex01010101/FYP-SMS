from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from user.decorators import seller_required
from .models import Product, Category, StockBatch
import uuid
from django.db.models import ProtectedError
from decimal import Decimal

def _auto_sku(name):
    prefix = ''.join(name.split())[:4].upper()
    return f'{prefix}-{str(uuid.uuid4())[:4].upper()}'


@seller_required
def product_list(request):
    products   = Product.objects.select_related('category').all()
    categories = Category.objects.all()

    q = request.GET.get('q', '')
    if q:
        products = products.filter(name__icontains=q)

    cat = request.GET.get('category', '')
    if cat:
        products = products.filter(category_id=cat)

    context = {
        'products':           products,
        'categories':         categories,
        'total_products':     Product.objects.count(),
        'low_stock_items':    [p for p in Product.objects.all() if p.is_low_stock],
    }
    return render(request, 'products/product.html', context)


@seller_required
def product_add(request):
    if request.method == 'POST':
        name    = request.POST.get('name', '').strip()
        sku     = request.POST.get('sku', '').strip() or _auto_sku(name)
        cat_id  = request.POST.get('category') or None
        price   = request.POST.get('sale_price', 0)   or 0
        reorder = request.POST.get('reorder_level', 10) or 10
        qty     = int(request.POST.get('quantity', 0)  or 0)
        cost    = request.POST.get('cost_price', 0)   or 0
        desc    = request.POST.get('description', '').strip()

        if not name:
            messages.error(request, 'Product name is required.')
            return redirect('product-list')

        # Ensure unique SKU
        while Product.objects.filter(sku=sku).exists():
            sku = _auto_sku(name)

        product = Product.objects.create(
            name=name, sku=sku, category_id=cat_id,
            sale_price=price, reorder_level=reorder, description=desc,
        )
        if qty and cost:
            StockBatch.objects.create(
                product=product, cost_price=cost, quantity=qty,
            )
        messages.success(request, f'Product "{name}" added successfully.')
    return redirect('product-list')


@seller_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.name          = request.POST.get('name',          product.name)
        product.category_id   = request.POST.get('category')      or product.category_id
        # product.sale_price    = request.POST.get('sale_price',    product.sale_price)
        new_sale_price = Decimal(
            request.POST.get('sale_price', product.sale_price)
        )

        if new_sale_price < Decimal(str(product.avg_cost_price)):
            messages.error(
                request,
                f'Sale price cannot be lower than average cost price (Rs. {product.avg_cost_price}).'
            )
            return redirect('product-list')

        product.sale_price = new_sale_price
        product.reorder_level = request.POST.get('reorder_level', product.reorder_level)
        product.description   = request.POST.get('description',   product.description)
        product.is_active     = request.POST.get('is_active') == 'on'
        product.save()
        messages.success(request, f'Product "{product.name}" updated.')
    return redirect('product-list')


@seller_required
def product_delete(request, pk):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk)
        name = product.name
        try:
            product.delete()
            messages.success(request, f'Product "{name}" deleted.')
        except ProtectedError:
            
            messages.warning(
                request, f'Cannot delete Product {name}.' 
                f'Please inactive the product instead.'
                )
    return redirect('product-list')


@seller_required
def category_add(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        desc = request.POST.get('description', '').strip()
        if name:
            cat, created = Category.objects.get_or_create(
                name=name, defaults={'description': desc}
            )
            if created:
                messages.success(request, f'Category "{name}" added.')
            else:
                messages.warning(request, f'Category "{name}" already exists.')
        else:
            messages.error(request, 'Category name is required.')
    return redirect('product-list')


@seller_required
def category_delete(request, pk):
    if request.method == 'POST':
        cat = get_object_or_404(Category, pk=pk)
        if cat.product_set.exists():
            messages.error(request, f'Cannot delete "{cat.name}" — it has products assigned.')
        else:
            cat.delete()
            messages.success(request, f'Category deleted.')
    return redirect('product-list')
