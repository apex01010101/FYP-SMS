from django.db import models
from decimal import Decimal


class Supplier(models.Model):
    name       = models.CharField(max_length=255)
    phone      = models.CharField(max_length=20, blank=True)
    address    = models.TextField(blank=True)
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def total_purchased(self):
        return sum(p.get_total() for p in self.purchase_set.all())

    @property
    def total_paid(self):
        from django.db.models import Sum
        result = self.purchase_set.aggregate(t=Sum('paid_amount'))['t']
        return result or Decimal('0.00')

    @property
    def balance_due(self):
        return self.total_purchased - self.total_paid


class Purchase(models.Model):
    PAYMENT_METHODS = (
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Cheque', 'Cheque'),
    )
    supplier       = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    invoice_ref    = models.CharField(max_length=100, blank=True)
    paid_amount    = models.DecimalField(max_digits=12, decimal_places=2,
                                         default=0)
    payment_method = models.CharField(max_length=20,
                                       choices=PAYMENT_METHODS, default='Cash')
    notes          = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def get_total(self):
        return sum(b.cost_price * b.quantity
                   for b in self.stock_batches.all())

    @property
    def balance_due(self):
        return self.get_total() - self.paid_amount

    def __str__(self):
        return f'PUR-{self.pk:04d} — {self.supplier.name}'
