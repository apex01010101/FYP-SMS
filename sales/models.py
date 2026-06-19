from django.db import models
from decimal import Decimal


class Sale(models.Model):
    PAYMENT_METHODS = (
        ('Cash', 'Cash'), ('Card', 'Card'),
        ('Bank Transfer', 'Bank Transfer'), ('Credit', 'On Credit'),
    )
    customer       = models.ForeignKey('customers.Customer',
                                       on_delete=models.SET_NULL,
                                       null=True, blank=True,
                                       related_name='sales')
    customer_name  = models.CharField(max_length=255, default='Walk-in')
    sale_date      = models.DateField(auto_now_add=True)
    tax_percent    = models.DecimalField(max_digits=5, decimal_places=2,
                                         default=0)
    paid_amount    = models.DecimalField(max_digits=12, decimal_places=2,
                                         default=0)
    payment_method = models.CharField(max_length=20,
                                       choices=PAYMENT_METHODS, default='Cash')
    notes          = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    @property
    def invoice_number(self):
        return f'INV-{self.pk:04d}'

    @property
    def subtotal(self):
        return sum(i.line_total for i in self.items.all())

    @property
    def tax_amount(self):
        return self.subtotal * (self.tax_percent / 100)

    @property
    def total_amount(self):
        return self.subtotal + self.tax_amount

    @property
    def balance(self):
        return max(self.total_amount - self.paid_amount, Decimal('0.00'))

    @property
    def status(self):
        if self.balance <= 0:    return 'paid'
        if self.paid_amount > 0: return 'partial'
        return 'unpaid'

    @property
    def item_count(self):
        return self.items.count()

    def __str__(self):
        return self.invoice_number


class SaleItem(models.Model):
    sale       = models.ForeignKey(Sale, related_name='items',
                                   on_delete=models.CASCADE)
    product    = models.ForeignKey('products.Product',
                                   on_delete=models.PROTECT)
    quantity   = models.PositiveIntegerField()
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount   = models.DecimalField(max_digits=5, decimal_places=2,
                                      default=0)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2,
                                      default=0)

    @property
    def line_total(self):
        return (Decimal(str(self.quantity)) * self.sale_price
                * (1 - self.discount / 100))

    @property
    def profit(self):
        return self.line_total - (Decimal(str(self.quantity)) * self.cost_price)

    def __str__(self):
        return f'{self.product.name} x{self.quantity}'
