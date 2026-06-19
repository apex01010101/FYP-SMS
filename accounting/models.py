from django.db import models


class Transaction(models.Model):
    TYPE_CHOICES = (
        ('sale',             'Sale Revenue'),
        ('sale_payment',     'Customer Payment Received'),
        ('purchase',         'Stock Purchase'),
        ('supplier_payment', 'Supplier Payment Made'),
        ('expense',          'Business Expense'),
    )
    transaction_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    description      = models.CharField(max_length=255)
    inflow           = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    outflow          = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    date             = models.DateField()
    reference        = models.CharField(max_length=100, blank=True)
    sale_id          = models.PositiveIntegerField(null=True, blank=True)
    purchase_id      = models.PositiveIntegerField(null=True, blank=True)
    expense_id       = models.PositiveIntegerField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.date} | {self.description}'
