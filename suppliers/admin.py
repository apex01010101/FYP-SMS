from django.contrib import admin
from .models import Supplier, Purchase

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display  = ["name", "phone", "total_purchased", "balance_due"]
    search_fields = ["name"]

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ["__str__", "supplier", "paid_amount", "created_at"]
