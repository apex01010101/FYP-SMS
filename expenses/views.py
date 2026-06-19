from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from user.decorators import seller_required
from .models import Expense, ExpenseCategory
from accounting.models import Transaction
import datetime


@seller_required
def expense_list(request):
    expenses   = Expense.objects.select_related('category').order_by('-created_at')
    categories = ExpenseCategory.objects.all()
    today      = datetime.date.today()

    q = request.GET.get('q', '')
    if q:
        expenses = expenses.filter(note__icontains=q)

    cat = request.GET.get('category', '')
    if cat:
        expenses = expenses.filter(category_id=cat)

    context = {
        'expenses':              expenses,
        'categories':            categories,
        'total_expense_records': Expense.objects.count(),
        'expense_categories':    categories.count(),
        'today_expenses':        sum(e.amount for e in Expense.objects.filter(date=today)),
        'monthly_expenses':      sum(e.amount for e in Expense.objects.filter(date__month=today.month)),
        'by_category': [
            {'name': c.name,
             'total': sum(e.amount for e in Expense.objects.filter(category=c))}
            for c in categories
        ],
    }
    return render(request, 'expenses/expenses.html', context)


@seller_required
def expense_add(request):
    if request.method == 'POST':
        cat_id = request.POST.get('category')
        amount = request.POST.get('amount', 0) or 0
        note   = request.POST.get('note', '').strip()

        if not cat_id:
            messages.error(request, 'Please select a category.')
            return redirect('expense-list')

        expense = Expense.objects.create(
            category_id=cat_id, amount=amount, note=note,
        )
        cat_name = ExpenseCategory.objects.get(pk=cat_id).name
        Transaction.objects.create(
            transaction_type='expense',
            description=f'Expense — {cat_name}',
            inflow=0, outflow=amount,
            date=datetime.date.today(),
            reference=f'EXP-{expense.pk:04d}',
            expense_id=expense.pk,
        )
        messages.success(request, 'Expense recorded.')
    return redirect('expense-list')


@seller_required
def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        expense.category_id = request.POST.get('category', expense.category_id)
        expense.amount      = request.POST.get('amount',   expense.amount)
        expense.note        = request.POST.get('note',     expense.note)
        expense.save()
        Transaction.objects.filter(expense_id=pk).update(outflow=expense.amount)
        messages.success(request, 'Expense updated.')
    return redirect('expense-list')


@seller_required
def expense_delete(request, pk):
    if request.method == 'POST':
        Transaction.objects.filter(expense_id=pk).delete()
        get_object_or_404(Expense, pk=pk).delete()
        messages.success(request, 'Expense deleted.')
    return redirect('expense-list')


@seller_required
def category_add(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            ExpenseCategory.objects.get_or_create(name=name)
            messages.success(request, f'Category "{name}" added.')
        else:
            messages.error(request, 'Category name is required.')
    return redirect('expense-list')
