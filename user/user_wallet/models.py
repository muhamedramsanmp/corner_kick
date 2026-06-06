from django.db import models
from django.conf import settings
from user.user_orders.models import Order


class Wallet(models.Model):

    user = models.OneToOneField(

        settings.AUTH_USER_MODEL,

        on_delete=models.CASCADE,

        related_name="wallet"

    )

    balance = models.DecimalField(

        max_digits=10,

        decimal_places=2,

        default=0

    )

    created_at = models.DateTimeField(

        auto_now_add=True

    )

    updated_at = models.DateTimeField(

        auto_now=True

    )

    def __str__(self):

        return f"{self.user.username} Wallet"
    


class WalletTransaction(models.Model):

    TRANSACTION_TYPES = (

        ("CREDIT", "Credit"),

        ("DEBIT", "Debit"),

    )

    STATUS_CHOICES = (

        ("PENDING", "Pending"),

        ("SUCCESS", "Success"),

        ("FAILED", "Failed"),

        ("REFUNDED", "Refunded"),

    )

    wallet = models.ForeignKey(

        Wallet,

        on_delete=models.CASCADE,

        related_name="transactions"

    )

    referral_id = models.IntegerField(

        null=True,

        blank=True

    )

    order = models.ForeignKey(

        Order,

        on_delete=models.SET_NULL,

        null=True,

        blank=True,

        related_name="wallet_transactions"

    )

    transaction_type = models.CharField(

        max_length=10,

        choices=TRANSACTION_TYPES

    )

    status = models.CharField(

        max_length=20,

        choices=STATUS_CHOICES,

        default="PENDING"

    )

    payment_date = models.DateTimeField(

        null=True,

        blank=True

    )

    amount = models.DecimalField(

        max_digits=10,

        decimal_places=2

    )

    description = models.TextField(

        blank=True,

        null=True

    )

    razorpay_order_id = models.CharField(

        max_length=255,

        blank=True,

        null=True

    )

    razorpay_payment_id = models.CharField(

        max_length=255,

        blank=True,

        null=True

    )

    created_at = models.DateTimeField(

        auto_now_add=True

    )

    def __str__(self):

        return f"{self.wallet.user.username} - {self.amount}"