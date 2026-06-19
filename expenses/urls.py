from django.urls import path
from . import views
urlpatterns = [
    path('',                 views.expense_list,   name='expense-list'),
    path('add/',             views.expense_add,    name='expense-add'),
    path('edit/<int:pk>/',   views.expense_edit,   name='expense-edit'),
    path('delete/<int:pk>/', views.expense_delete, name='expense-delete'),
    path('category/add/',    views.category_add,   name='expense-category-add'),
]
