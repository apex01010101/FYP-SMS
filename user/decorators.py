from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from functools import wraps


def seller_required(view_func):
    """Only sellers and admins can access seller dashboard views."""
    @wraps(view_func)
    @login_required(login_url='/user/login/')
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        try:
            role = request.user.profile.role
        except Exception:
            return redirect('user-login')
        if role in ('seller', 'admin'):
            return view_func(request, *args, **kwargs)
        # Customer trying to access seller area
        return redirect('customer-dashboard')
    return wrapper


def customer_required(view_func):
    """Only customers can access the customer portal."""
    @wraps(view_func)
    @login_required(login_url='/user/login/')
    def wrapper(request, *args, **kwargs):
        try:
            role = request.user.profile.role
        except Exception:
            return redirect('user-login')
        if role == 'customer':
            return view_func(request, *args, **kwargs)
        # Seller/admin trying to access customer area
        return redirect('dashboard-index')
    return wrapper
