from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class Customer(models.Model):
    TYPE_CHOICES = (
        ('Retail',    'Retail'),
        ('Wholesale', 'Wholesale'),
        ('Walk-in',   'Walk-in'),
    )
    STATUS_CHOICES = (
        ('Active',   'Active'),
        ('Inactive', 'Inactive'),
    )
    # Django User account for customer login
    user            = models.OneToOneField(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='customer'
    )
    name            = models.CharField(max_length=255)
    phone           = models.CharField(max_length=20,  blank=True)
    email           = models.EmailField(blank=True)
    address         = models.TextField(blank=True)
    customer_type   = models.CharField(max_length=20,
                                       choices=TYPE_CHOICES, default='Retail')
    credit_limit    = models.DecimalField(max_digits=12, decimal_places=2,
                                          default=0)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2,
                                          default=0)
    status          = models.CharField(max_length=10,
                                       choices=STATUS_CHOICES, default='Active')
    notes           = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def total_purchases(self):
        return sum(s.total_amount for s in self.sales.all())

    @property
    def total_paid(self):
        return sum(s.paid_amount for s in self.sales.all())

    @property
    def balance_due(self):
        return sum(s.balance for s in self.sales.all())
