from django.db import models
from decimal import Decimal


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending',   'Pending'),
        ('confirmed', 'Confirmed'),
        ('converted', 'Converted to Invoice'),
        ('cancelled', 'Cancelled'),
    )
    customer      = models.ForeignKey('customers.Customer',
                                      on_delete=models.SET_NULL,
                                      null=True, blank=True,
                                      related_name='orders')
    customer_name = models.CharField(max_length=255, default='Walk-in')
    status        = models.CharField(max_length=20,
                                      choices=STATUS_CHOICES, default='pending')
    notes         = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    @property
    def order_number(self):
        return f'ORD-{self.pk:04d}'

    @property
    def total_amount(self):
        return sum(
            i.product.sale_price * i.quantity
            for i in self.items.all()
        )

    @property
    def item_count(self):
        return self.items.count()

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order    = models.ForeignKey(Order, related_name='items',
                                  on_delete=models.CASCADE)
    product  = models.ForeignKey('products.Product',
                                  on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    @property
    def subtotal(self):
        return self.product.sale_price * self.quantity

    def __str__(self):
        return f'{self.product.name} ({self.quantity})'
