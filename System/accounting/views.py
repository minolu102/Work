# accounting/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone
from .models import ChartOfAccount, JournalEntry, JournalLine, FiscalYear, Sequence
from .forms import ChartOfAccountForm, JournalEntryForm, JournalLineForm
# Create your views here.

@login_required
def chart_of_accounts(request):
    """แสดงผังบัญชี"""
    accounts = ChartOfAccount.objects.filter(
        company=request.user.profile.company,
        is_active=True
    ).select_related('parent_account').order_by('code')
    
    context = {
        'accounts': accounts,
        'title': 'Chart of Accounts - ผังบัญชี'
    }
    return render(request, 'accounting/chart_of_accounts.html', context)

@login_required
def account_detail(request, account_id):
    """รายละเอียดบัญชี"""
    account = get_object_or_404(ChartOfAccount, id=account_id, company=request.user.profile.company)
    
    # ดึงรายการบัญชีแยกประเภท
    journal_lines = account.journal_entries.select_related(
        'journal_entry'
    ).filter(
        journal_entry__status='posted'
    ).order_by('-journal_entry__entry_date')[:50]
    
    # คำนวณยอดคงเหลือ
    current_balance = account.get_balance()
    
    context = {
        'account': account,
        'journal_lines': journal_lines,
        'current_balance': current_balance,
        'title': f'Account Details - {account.name}'
    }
    return render(request, 'accounting/account_detail.html', context)

@login_required
def journal_entries(request):
    """แสดงรายการบัญชี"""
    entries = JournalEntry.objects.filter(
        company=request.user.profile.company
    ).select_related('posted_by').order_by('-entry_date')
    
    # Filter by status
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        entries = entries.filter(status=status_filter)
    
    context = {
        'entries': entries,
        'status_filter': status_filter,
        'title': 'Journal Entries - รายการบัญชี'
    }
    return render(request, 'accounting/journal_entries.html', context)

@login_required
def journal_entry_detail(request, entry_id):
    """รายละเอียดรายการบัญชี"""
    entry = get_object_or_404(
        JournalEntry, 
        id=entry_id, 
        company=request.user.profile.company
    )
    
    journal_lines = entry.journal_lines.select_related('account').all()
    
    context = {
        'entry': entry,
        'journal_lines': journal_lines,
        'title': f'Journal Entry - {entry.entry_number}'
    }
    return render(request, 'accounting/journal_entry_detail.html', context)

@login_required
def create_journal_entry(request):
    """สร้างรายการบัญชีใหม่"""
    if request.method == 'POST':
        form = JournalEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.company = request.user.profile.company
            entry.created_by = request.user
            
            # Generate entry number
            sequence = Sequence.objects.get_or_create(
                sequence_type='journal_entry',
                defaults={'prefix': 'JE', 'current_number': 0}
            )[0]
            entry.entry_number = sequence.get_next_number()
            entry.save()
            
            messages.success(request, 'Journal entry created successfully.')
            return redirect('accounting:journal_entry_detail', entry_id=entry.id)
    else:
        form = JournalEntryForm()
    
    context = {
        'form': form,
        'title': 'Create Journal Entry'
    }
    return render(request, 'accounting/journal_entry_form.html', context)

@login_required
def post_journal_entry(request, entry_id):
    """Post รายการบัญชี"""
    if request.method == 'POST':
        entry = get_object_or_404(
            JournalEntry,
            id=entry_id,
            company=request.user.profile.company
        )
        
        try:
            entry.post_entry(request.user)
            messages.success(request, f'Journal entry {entry.entry_number} posted successfully.')
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('accounting:journal_entry_detail', entry_id=entry.id)
    
    return redirect('accounting:journal_entries')

@login_required
def trial_balance(request):
    """งบทดลอง"""
    company = request.user.profile.company
    
    # Get fiscal year
    try:
        fiscal_year = FiscalYear.objects.get(company=company, is_current=True)
    except FiscalYear.DoesNotExist:
        messages.error(request, 'No active fiscal year found.')
        return redirect('accounting:chart_of_accounts')
    
    # Get all accounts with balances
    accounts = ChartOfAccount.objects.filter(
        company=company,
        is_active=True,
        is_header=False
    ).order_by('code')
    
    trial_balance_data = []
    total_debit = 0
    total_credit = 0
    
    for account in accounts:
        balance = account.get_balance()
        
        if balance != 0:
            if account.account_type in ['asset', 'expense'] and balance > 0:
                debit_amount = abs(balance)
                credit_amount = 0
            elif account.account_type in ['asset', 'expense'] and balance < 0:
                debit_amount = 0
                credit_amount = abs(balance)
            elif account.account_type in ['liability', 'equity', 'income'] and balance > 0:
                debit_amount = 0
                credit_amount = abs(balance)
            else:
                debit_amount = abs(balance)
                credit_amount = 0
            
            trial_balance_data.append({
                'account': account,
                'debit_amount': debit_amount,
                'credit_amount': credit_amount,
            })
            
            total_debit += debit_amount
            total_credit += credit_amount
    
    context = {
        'trial_balance_data': trial_balance_data,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'fiscal_year': fiscal_year,
        'title': 'Trial Balance - งบทดลอง'
    }
    return render(request, 'accounting/trial_balance.html', context)

@login_required
def create_account(request):
    """Create a new chart of account"""
    if request.method == 'POST':
        form = ChartOfAccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.company = request.user.profile.company
            account.save()
            messages.success(request, 'Account created successfully.')
            return redirect('accounting:chart_of_accounts')
    else:
        form = ChartOfAccountForm()
    context = {
        'form': form,
        'title': 'Create Account'
    }
    return render(request, 'accounting/account_form.html', context)

@login_required
def profit_loss(request):
    """Profit & Loss report placeholder"""
    return render(request, 'accounting/profit_loss.html', {'title': 'Profit & Loss'})

@login_required
def balance_sheet(request):
    """Balance Sheet report placeholder"""
    return render(request, 'accounting/balance_sheet.html', {'title': 'Balance Sheet'})