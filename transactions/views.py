from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import get_object_or_404, render,redirect
from django.views import View
from django.http import HttpResponse
from django.views.generic import CreateView, ListView
from transactions.constants import DEPOSIT, WITHDRAWAL,LOAN, LOAN_PAID,Transfer_money
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string
from datetime import datetime
from django.db.models import Sum
from transactions.forms import (
    DepositForm,
    WithdrawForm,
    LoanRequestForm,
    TransferForm,
)
from transactions.models import Transaction,Bankrupt
from accounts.models import UserBankAccount
from .models import Transaction
from .forms import TransferForm
def send_transaction_email(user, amount, subject, template):
        message = render_to_string(template, {
            'user' : user,
            'amount' : amount,
        })
        send_email = EmailMultiAlternatives(subject, '', to=[user.email])
        send_email.attach_alternative(message, "text/html")
        send_email.send()
class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = 'transactions/transaction_form.html'
    model = Transaction
    title = ''
    success_url = reverse_lazy('transaction_report')
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) # template e context data pass kora
        context.update({
            'title': self.title
        })
        return context
class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposit'
    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial
    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
        # if not account.initial_deposit_date:
        #     now = timezone.now()
        #     account.initial_deposit_date = now
        account.balance += amount # amount = 200, tar ager balance = 0 taka new balance = 0+200 = 200
        account.save(
            update_fields=[
                'balance'
            ]
        )
        messages.success(
            self.request,
            f'{"{:,.2f}".format(float(amount))}$ was deposited to your account successfully'
        )
        send_transaction_email(self.request.user, amount, "Deposite Message", "transactions/deposite_email.html")
        return super().form_valid(form)


class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money'

    def get_initial(self):
        initial = {'transaction_type': WITHDRAWAL}
        return initial

    def get(self, request):
        # Check if the bank is globally marked as bankrupt
        global_bankrupt = Bankrupt.objects.filter(bankrupt=True).exists()

        if global_bankrupt:
            messages.error(request, "Withdrawals are not possible as the bank is marked as bankrupt.")
            return redirect('transaction_report')

        return super().get(request)

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account

        # Check again to ensure no transactions during bankrupt status
        global_bankrupt = Bankrupt.objects.filter(bankrupt=True).exists()

        if global_bankrupt:
            messages.error(self.request, "Withdrawals are not possible as the bank is marked as bankrupt.")
            return redirect('transaction_report')

        # Deduct the withdrawal amount and update the balance
        account.balance -= amount
        account.save(update_fields=['balance'])

        # Notify the user of successful withdrawal
        messages.success(
            self.request,
            f"Successfully withdrawn {'{:,.2f}'.format(float(amount))}$ from your account."
        )

        # Send a withdrawal email notification
        send_transaction_email(
            self.request.user, amount, "Withdrawal Message", "transactions/withdrawal_email.html"
        )
        return super().form_valid(form)


class LoanRequestView(TransactionCreateMixin):
    form_class = LoanRequestForm
    title = 'Request For Loan'
    def get_initial(self):
        initial = {'transaction_type': LOAN}
        return initial
    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transaction.objects.filter(
            account=self.request.user.account,transaction_type=3,loan_approve=True).count()
        if current_loan_count >= 3:
            return HttpResponse("You have cross the loan limits")
        messages.success(
            self.request,
            f'Loan request for {"{:,.2f}".format(float(amount))}$ submitted successfully'
        )
        send_transaction_email(self.request.user, amount, "Loan Request Message", "transactions/loan_email.html")
        return super().form_valid(form)
    
class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = 'transactions/transaction_report.html'
    model = Transaction
    balance = 0 # filter korar pore ba age amar total balance ke show korbe
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account=self.request.user.account
        )
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
            self.balance = Transaction.objects.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date
            ).aggregate(Sum('amount'))['amount__sum']
        else:
            self.balance = self.request.user.account.balance
       
        return queryset.distinct() # unique queryset hote hobe
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account
        })
        return context
    
        
class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        loan = get_object_or_404(Transaction, id=loan_id)
        print(loan)
        if loan.loan_approve:
            user_account = loan.account
                # Reduce the loan amount from the user's balance
                # 5000, 500 + 5000 = 5500
                # balance = 3000, loan = 5000
            if loan.amount < user_account.balance:
                user_account.balance -= loan.amount
                loan.balance_after_transaction = user_account.balance
                user_account.save()
                loan.loan_approved = True
                loan.transaction_type = LOAN_PAID
                loan.save()
                return redirect('transactions:loan_list')
            else:
                messages.error(
            self.request,
            f'Loan amount is greater than available balance'
        )
        return redirect('loan_list')
class LoanListView(LoginRequiredMixin,ListView):
    model = Transaction
    template_name = 'transactions/loan_request.html'
    context_object_name = 'loans' # loan list ta ei loans context er moddhe thakbe
    
    def get_queryset(self):
        user_account = self.request.user.account
        queryset = Transaction.objects.filter(account=user_account,transaction_type=3)
        print(queryset)
        return queryset
    
# class TransferMoneyView(View):
#     template_name = 'transactions/transfer_form.html'

#     def get(self, request):
#         form = TransferForm(account=request.user.account)
#         return render(request, self.template_name, {'form': form})

#     def post(self, request):
#         form = TransferForm(request.POST, account=request.user.account)
#         if form.is_valid():
#             amount = form.cleaned_data['amount']
#             recipient_account_number = form.cleaned_data['recipient_account']
#             recipient_account = get_object_or_404(UserBankAccount, account_number=recipient_account_number)

#             # Deduct from sender's account
#             sender_account = request.user.account
#             sender_account.balance -= amount
#             sender_account.save()

#             # Add to recipient's account
#             recipient_account.balance += amount
#             recipient_account.save()

#             # Log transaction
#             Transaction.objects.create(
#                 account=sender_account,
#                 amount=-amount,
#                 balance_after_transaction=sender_account.balance,
#                 transaction_type="TRANSFER",
#             )
#             Transaction.objects.create(
#                 account=recipient_account,
#                 amount=amount,
#                 balance_after_transaction=recipient_account.balance,
#                 transaction_type="RECEIPT",
#             )

#             # Send notifications
#             send_transaction_email(sender_account.user, amount, "Amount Transferred", "transactions/transfer_email.html")
#             send_transaction_email(recipient_account.user, amount, "Amount Received", "transactions/received_email.html")

#             messages.success(request, "Transfer successful!")
#             return redirect('transaction_report')

#         return render(request, self.template_name, {'form': form})
    
class TransferMoneyView(TransactionCreateMixin, View):
    form_class = TransferForm
    title = 'Transfer money'
    def get_initial(self):
        initial = {'transaction_type': Transfer_money}
        return initial
    def get(self, request):
        form = TransferForm(account=request.user.account)
        return render(request, 'transactions/transfer_form.html', {'form': form})

    def post(self, request):
        form = TransferForm(request.POST, account=request.user.account)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            recipient_account_no = form.cleaned_data['recipient_account']
            sender_account = request.user.account
            recipient_account = get_object_or_404(UserBankAccount, account_no=recipient_account_no)

            # Deduct from sender and add to recipient
            sender_account.balance -= amount
            recipient_account.balance += amount
            sender_account.save()
            recipient_account.save()

            # Create transaction records
            Transaction.objects.create(
                account=sender_account,
                amount=-amount,
                balance_after_transaction=sender_account.balance,
                transaction_type=5  # Transfer Out
            )
            Transaction.objects.create(
                account=recipient_account,
                amount=amount,
                balance_after_transaction=recipient_account.balance,
                transaction_type=1  # Transfer In
            )

            send_transaction_email(sender_account.user, amount, "Amount Transferred", "transactions/transfer_email.html")
            send_transaction_email(recipient_account.user, amount, "Amount Received", "transactions/received_email.html")

            messages.success(request, f'Transferred ${amount} successfully!')
            return redirect('transaction_report')

        return render(request, 'transactions/transfer_form.html', {'form': form})