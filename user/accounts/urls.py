from django.urls import path 
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path("logout/", views.logout_view, name="logout"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("verify-otp/",      views.verify_otp,      name="verify_otp"),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path("reset-password/",  views.reset_password,  name="reset_password"),
]