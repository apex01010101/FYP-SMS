from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import UserProfile


def user_login(request):
    if request.user.is_authenticated:
        return _role_redirect(request.user)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return _role_redirect(user)
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'user/login.html')


def _role_redirect(user):
    """Redirect user to their role-appropriate dashboard."""
    if user.is_superuser:
        return redirect('/admin/')
    try:
        role = user.profile.role
    except Exception:
        return redirect('user-login')
    if role == 'seller':
        return redirect('dashboard-index')
    if role == 'customer':
        return redirect('customer-dashboard')
    return redirect('user-login')


def user_logout(request):
    logout(request)
    return redirect('user-login')


def role_redirect(request):
    """Called after LOGIN_REDIRECT_URL."""
    if request.user.is_authenticated:
        return _role_redirect(request.user)
    return redirect('user-login')


@login_required(login_url='/user/login/')
def profile(request):
    """Works for both sellers and customers — shows own profile."""
    return render(request, 'user/profile.html')


@login_required(login_url='/user/login/')
def profile_update(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name  = request.POST.get('last_name',  user.last_name)
        user.email      = request.POST.get('email',      user.email)
        user.save()

        profile = user.profile
        profile.phone   = request.POST.get('phone',   profile.phone)
        profile.address = request.POST.get('address', profile.address)
        if request.FILES.get('image'):
            profile.image = request.FILES['image']
        profile.save()
        messages.success(request, 'Profile updated successfully.')

        # Redirect back to correct dashboard
        if profile.role == 'customer':
            return redirect('customer-dashboard')
        return redirect('dashboard-index')

    return render(request, 'user/profile_update.html')
