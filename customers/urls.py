from django.urls import path
from . import views
urlpatterns = [
    path('',                        views.customer_list,      name='customer-list'),
    path('add/',                    views.customer_add,       name='customer-add'),
    path('edit/<int:pk>/',          views.customer_edit,      name='customer-edit'),
    path('delete/<int:pk>/',        views.customer_delete,    name='customer-delete'),
    path('payment/',                views.customer_payment,   name='customer-payment'),
    path('<int:pk>/ledger/',        views.customer_ledger,    name='customer-ledger'),
    # Customer portal (customer role)
    path('portal/',                 views.customer_dashboard, name='customer-dashboard'),
    path('portal/products/',        views.portal_products,    name='portal-products'),
    path('portal/orders/',          views.portal_orders,      name='portal-orders'),
    path('portal/orders/place/',    views.portal_place_order, name='portal-place-order'),
    path('portal/ledger/',          views.portal_ledger,      name='portal-ledger'),
]
