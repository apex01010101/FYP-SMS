from django.urls import path
from . import views
urlpatterns = [
    path('', views.accounting_index, name='accounting-index'),
]
