from django.contrib import admin
from .models import Product, Category, StockBatch

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "sku", "category", "sale_price", "current_stock", "is_low_stock", "is_active"]
    list_filter  = ["category", "is_active"]
    search_fields = ["name", "sku"]

@admin.register(StockBatch)
class StockBatchAdmin(admin.ModelAdmin):
    list_display = ["product", "cost_price", "quantity", "date_received"]
    list_filter  = ["product"]
