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

    print("REFERRAL REWARD SESSION CREATED")

    request.session["referral_reward"] = {
        "amount": 500,
        "wallet_balance": str(wallet.balance),
        "date": timezone.now().strftime("%d %b %Y %I:%M %p"),
    }
