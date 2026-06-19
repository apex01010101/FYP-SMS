from django.db import models


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = 'Expense Categories'

    def __str__(self):
        return self.name


class Expense(models.Model):
    category   = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    amount     = models.DecimalField(max_digits=10, decimal_places=2)
    note       = models.TextField(blank=True)
    date       = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.category.name} — Rs. {self.amount}'
