from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('', lambda req: redirect('user-login')),
    path('admin/', admin.site.urls),

    # Auth
    path('user/', include('user.urls')),

    # Seller Dashboard
    path('dashboard/',  include('dashboard.urls')),
    path('products/',   include('products.urls')),
    path('customers/',  include('customers.urls')),
    path('suppliers/',  include('suppliers.urls')),
    path('sales/',      include('sales.urls')),
    path('orders/',     include('orders.urls')),
    path('expenses/',   include('expenses.urls')),
    path('accounting/', include('accounting.urls')),
    path('reports/',    include('reports.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
