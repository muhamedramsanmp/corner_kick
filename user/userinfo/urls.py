from django.urls import path
from . import views

app_name = 'userinfo'

urlpatterns = [
    path('', views.profile_view, name='profile'),
    path('edit-profile/',views.edit_profile,name='edit_profile'),
    path('logout-page/', views.logout_page, name='logout_page'),
    path('logout/', views.logout_user, name='logout_user'),
    path('change-password/',views.change_password,name='change_password'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('profile-verify-otp/', views.profile_verify_otp, name='profile_verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path("change-email-verify/", views.change_email_verify, name="change_email_verify"),
    path("resend-change-email-otp/", views.resend_change_email_otp, name="resend_change_email"),
]