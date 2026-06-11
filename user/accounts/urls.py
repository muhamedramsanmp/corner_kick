from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("signup-verify/", views.verify_signup_otp, name="verify_signup_otp"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("resend-otp/", views.resend_otp, name="resend_otp"),
    path("reset-password/", views.reset_password, name="reset_password"),
    path("resend-signup-otp/", views.resend_signup_otp, name="resend_signup_otp"),
    path("referral/", views.referral_dashboard, name="referral_dashboard"),
    path(
        "reward-seen/<int:reward_id>/", views.mark_reward_seen, name="mark_reward_seen"
    ),
]
