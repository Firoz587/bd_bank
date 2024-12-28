from django.shortcuts import render
from django.views.generic import FormView
from .forms import UserRegistrationForm,UserUpdateForm
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth import login, logout,update_session_auth_hash
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView
from django.views import View
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

def send_email_notification(user, subject, template, context=None):
    context = context or {}
    context['user'] = user  # Add the user to the context if not already present.

    # Render the email message from the template.
    message = render_to_string(template, context)

    # Send the email.
    email = EmailMultiAlternatives(subject, '', to=[user.email])
    email.attach_alternative(message, "text/html")
    email.send()

class UserRegistrationView(FormView):
    template_name = 'accounts/user_registration.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('profile')
    
    def form_valid(self,form):
        print(form.cleaned_data)
        user = form.save()
        login(self.request, user)
        print(user)
        return super().form_valid(form) # form_valid function call hobe jodi sob thik thake
    
class UserLoginView(LoginView):
    template_name = 'accounts/user_login.html'
    def get_success_url(self):
        return reverse_lazy('home')
class UserLogoutView(LogoutView):
    def get_success_url(self):
        if self.request.user.is_authenticated:
            logout(self.request)
        return reverse_lazy('home')
def user_logout(request):
    logout(request)
    return redirect('home')
class UserBankAccountUpdateView(View):
    template_name = 'accounts/profile.html'
    def get(self, request):
        form = UserUpdateForm(instance=request.user)
        return render(request, self.template_name, {'form': form})
    def post(self, request):
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')  # Redirect to the user's profile page
        return render(request, self.template_name, {'form': form})
    
@login_required
def change_password(request):
    if request.method == 'POST':
        change_pass_form = PasswordChangeForm(request.user, data=request.POST)
        if change_pass_form.is_valid():
            change_pass_form.save()
            messages.success(request, 'Password Updated Successfully!')
            send_email_notification(
            user=request.user,
            subject="Password Change Notification",
            template="accounts/password_change_email.html",
            context={
                'change_time': timezone.now(),
            }
)

            update_session_auth_hash(request, change_pass_form.user)
            return redirect('profile')
    else:
        change_pass_form = PasswordChangeForm(user=request.user)
        
    return render(request, 'accounts/change_password.html', {'form': change_pass_form})