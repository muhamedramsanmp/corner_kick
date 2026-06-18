import random
import string

from .models import ReferralCode
from django.contrib.sessions.backends.db import SessionStore
from user.user_wallet.models import Wallet, WalletTransaction
from .models import Referral, ReferralReward
from django.utils import timezone
from user.user_orders.models import Order


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

from django.conf import settings
from django.core.mail import send_mail


def send_signup_otp(email, full_name, otp):

    send_mail(
        subject="Corner Kick - Email Verification OTP",
        message=(
            f"Hello {full_name},\n\n"
            f"Welcome to Corner Kick.\n\n"
            f"Your verification OTP is: {otp}\n\n"
            f"OTP Expiry: 60 seconds\n\n"
            f"Please do not share this OTP with anyone.\n\n"
            f"Regards,\n"
            f"Corner Kick Team"
        ),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False,
    )


from django.conf import settings
from django.core.mail import send_mail


def send_reset_password_otp(email, otp):

    send_mail(
        subject="Corner Kick - Password Reset OTP",
        message=(
            "Hello,\n\n"
            "We received a request to reset your password.\n\n"
            f"Your Password Reset OTP is: {otp}\n\n"
            "OTP Expiry: 60 seconds\n\n"
            "If you did not request a password reset, "
            "please ignore this email.\n\n"
            "Do not share this OTP with anyone.\n\n"
            "Regards,\n"
            "Corner Kick Team"
        ),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False,
    )