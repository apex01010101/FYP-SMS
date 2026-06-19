from django.contrib import admin
from .models import Transaction

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display  = ["date", "transaction_type", "description", "inflow", "outflow"]
    list_filter   = ["transaction_type", "date"]
    search_fields = ["description", "reference"]
