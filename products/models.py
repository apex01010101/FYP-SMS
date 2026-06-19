from django.db import models
from django.db.models import Sum


class Category(models.Model):
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Product(models.Model):
    name          = models.CharField(max_length=255)
    sku           = models.CharField(max_length=50, unique=True)
    category      = models.ForeignKey(Category, on_delete=models.SET_NULL,
                                      null=True, blank=True)
    sale_price    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    description   = models.TextField(blank=True)
    is_active     = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def current_stock(self):
        return self.batches.filter(quantity__gt=0).aggregate(
            t=Sum('quantity'))['t'] or 0

    @property
    def avg_cost_price(self):
        batches = list(self.batches.filter(quantity__gt=0))
        total_qty  = sum(b.quantity for b in batches)
        total_cost = sum(b.cost_price * b.quantity for b in batches)
        return round(total_cost / total_qty, 2) if total_qty else 0

    @property
    def is_low_stock(self):
        return self.current_stock <= self.reorder_level

    @property
    def stock_value(self):
        return sum(b.cost_price * b.quantity
                   for b in self.batches.filter(quantity__gt=0))


class StockBatch(models.Model):
    product       = models.ForeignKey(Product, related_name='batches',
                                      on_delete=models.CASCADE)
    purchase      = models.ForeignKey('suppliers.Purchase',
                                      on_delete=models.SET_NULL,
                                      null=True, blank=True,
                                      related_name='stock_batches')
    cost_price    = models.DecimalField(max_digits=10, decimal_places=2)
    quantity      = models.PositiveIntegerField(default=0)
    date_received = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date_received']  # FIFO

    def __str__(self):
        return f'{self.product.name} — Batch #{self.id}'
