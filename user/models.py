from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """
    Extends Django's built-in User.
    role = 'admin'    → superuser, uses /admin/
    role = 'seller'   → staff, uses seller dashboard
    role = 'customer' → regular user, uses customer portal
    """
    ROLE_CHOICES = (
        ('admin',    'Admin'),
        ('seller',   'Seller'),
        ('customer', 'Customer'),
    )
    user    = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role    = models.CharField(max_length=20, choices=ROLE_CHOICES, default='seller')
    phone   = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    image   = models.ImageField(default='avatar.jpg', upload_to='Profile_Images')

    def __str__(self):
        return f'{self.user.username} ({self.role})'

    @property
    def is_admin(self):
        return self.role == 'admin' or self.user.is_superuser

    @property
    def is_seller(self):
        return self.role == 'seller'

    @property
    def is_customer(self):
        return self.role == 'customer'
