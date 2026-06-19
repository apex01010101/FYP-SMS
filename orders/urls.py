from django.urls import path
from . import views
urlpatterns = [
    path("",                  views.order_list,    name="order-list"),
    path("add/",              views.order_add,     name="order-add"),
    path("confirm/<int:pk>/", views.order_confirm, name="order-confirm"),
    path("convert/<int:pk>/", views.order_convert, name="order-convert"),
    path("cancel/<int:pk>/",  views.order_cancel,  name="order-cancel"),
]
