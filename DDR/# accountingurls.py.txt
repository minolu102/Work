# accounting/urls.py
from django.urls import path
from . import views

app_name = 'accounting'

urlpatterns = [
    path('', views.chart_of_accounts, name='chart_of_accounts'),
    path('accounts/', views.chart_of_accounts, name='chart_of_accounts'),
    path('accounts/<uuid:account_id>/', views.account_detail, name='account_detail'),
    path('accounts/create/', views.create_account, name='create_account'),
    
    path('journal/', views.journal_entries, name='journal_entries'),
    path('journal/<uuid:entry_id>/', views.journal_entry_detail, name='journal_entry_detail'),
    path('journal/create/', views.create_journal_entry, name='create_journal_entry'),
    path('journal/<uuid:entry_id>/post/', views.post_journal_entry, name='post_journal_entry'),
    
    path('reports/trial-balance/', views.trial_balance, name='trial_balance'),
    path('reports/profit-loss/', views.profit_loss, name='profit_loss'),
    path('reports/balance-sheet/', views.balance_sheet, name='balance_sheet'),
]