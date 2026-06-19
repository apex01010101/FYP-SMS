from django.urls import path
from . import views
urlpatterns = [
    path('',                 views.product_list,   name='product-list'),
    path('add/',             views.product_add,    name='product-add'),
    path('edit/<int:pk>/',   views.product_edit,   name='product-edit'),
    path('delete/<int:pk>/', views.product_delete, name='product-delete'),
    path('category/add/',    views.category_add,   name='category-add'),
    path('category/delete/<int:pk>/', views.category_delete, name='category-delete'),
]
