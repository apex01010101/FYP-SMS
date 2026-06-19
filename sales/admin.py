from django.contrib import admin
from .models import Sale, SaleItem

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display  = ["invoice_number", "customer_name", "total_amount", "paid_amount", "status", "sale_date"]
    list_filter   = ["payment_method", "sale_date"]
    search_fields = ["customer_name"]
    inlines       = [SaleItemInline]
