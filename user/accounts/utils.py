import random
import string

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from user.user_orders.models import Order
from user.user_wallet.models import Wallet, WalletTransaction

from .models import Referral, ReferralCode, ReferralReward


def generate_referral_code():

    while True:

        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

        if not ReferralCode.objects.filter(code=code).exists():

            return code


def credit_referral_reward(request, user, order):

    existing_orders = Order.objects.filter(user=user).exclude(id=order.id).exists()

    if existing_orders:
        return

    referral = Referral.objects.filter(referred_user=user, status="pending").first()

    if not referral:
        return

    reward_exists = ReferralReward.objects.filter(referral=referral).exists()

    if reward_exists:
        return

    wallet, created = Wallet.objects.get_or_create(user=referral.referrer)

    wallet.balance += 500
    wallet.save()

    WalletTransaction.objects.create(
        wallet=wallet,
        referral_id=referral.id,
        order=order,
        transaction_type="CREDIT",
        status="SUCCESS",
        amount=500,
        description=(f"Referral reward for " f"{user.email}"),
    )

    ReferralReward.objects.create(
        referral=referral,
        user=referral.referrer,
        reward_amount=500,
        reward_type="wallet",
        status="credited",
    )

    referral.status = "completed"
    referral.save()

    request.session["referral_reward"] = {
        "amount": 500,
        "wallet_balance": str(wallet.balance),
        "date": timezone.now().strftime("%d %b %Y %I:%M %p"),
    }


# utils.py


def send_signup_otp(email, full_name, otp):

    html_content = render_to_string(
        "signup_otp.html",
        {
            "full_name": full_name,
            "otp": otp,
        },
    )

    email_message = EmailMultiAlternatives(
        subject="Corner Kick - Email Verification OTP",
        body=f"Your OTP is {otp}",
        from_email=settings.EMAIL_HOST_USER,
        to=[email],
    )

    email_message.attach_alternative(html_content, "text/html")

    email_message.send()


def send_reset_password_otp(email, otp):

    html_content = render_to_string(
        "reset_password_otp.html",
        {
            "otp": otp,
        },
    )

    email_message = EmailMultiAlternatives(
        subject="Corner Kick - Password Reset OTP",
        body=f"Your OTP is {otp}",
        from_email=settings.EMAIL_HOST_USER,
        to=[email],
    )

    email_message.attach_alternative(html_content, "text/html")

    email_message.send()
