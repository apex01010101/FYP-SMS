from django.urls import path
from . import views
urlpatterns = [
    path("",                   views.supplier_list,    name="supplier-list"),
    path("add/",               views.supplier_add,     name="supplier-add"),
    path("edit/<int:pk>/",     views.supplier_edit,    name="supplier-edit"),
    path("delete/<int:pk>/",   views.supplier_delete,  name="supplier-delete"),
    path("payment/",           views.supplier_payment, name="supplier-payment"),
    path("purchase/add/",      views.purchase_add,     name="purchase-add"),
    path("<int:pk>/ledger/",   views.supplier_ledger,  name="supplier-ledger"),
]
