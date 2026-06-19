from django.urls import path
from . import views

urlpatterns = [
    path('login/',          views.user_login,     name='user-login'),
    path('logout/',         views.user_logout,    name='user-logout'),
    path('redirect/',       views.role_redirect,  name='user-redirect'),
    path('profile/',        views.profile,        name='user-profile'),
    path('profile/update/', views.profile_update, name='user-profile-update'),
]
