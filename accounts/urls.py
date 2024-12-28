from django.urls import path
from .views import UserRegistrationView, UserLoginView, UserLogoutView,UserBankAccountUpdateView
from . import views
 
urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', views.user_logout, name='logout'),
    # path('logout/', UserLogoutView.as_view(), name='logout'),
    path('profile/change_password/', views.change_password, name='change_password'),
    path('profile/', UserBankAccountUpdateView.as_view(), name='profile' )
]