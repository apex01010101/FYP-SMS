from django.urls import path
from . import views
urlpatterns = [
    path('',                 views.sale_list,    name='sale-list'),
    path('add/',             views.sale_add,     name='sale-add'),
    path('delete/<int:pk>/', views.sale_delete,  name='sale-delete'),
    path('payment/',         views.sale_payment, name='sale-payment'),
    path('<int:pk>/invoice/', views.sale_invoice, name='sale-invoice'),
]
