from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class OTP(models.Model):

    PURPOSE_CHOICES = (
        ("signup", "Signup"),
        ("reset", "Reset Password"),
    )

    email = models.EmailField(null=True, blank=True)  # TEMP
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=1)

    def time_left(self):

        expiry_time = self.created_at + timedelta(minutes=1)

        remaining = (expiry_time - timezone.now()).total_seconds()

        return max(0, int(remaining))

    def __str__(self):
        return f"{self.email} - {self.code} ({self.purpose})"


class Profile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="account_profile"
    )

    image = models.ImageField(upload_to="profiles/", blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)  # 🔥 ADD THIS

    def __str__(self):
        return self.user.email


from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ReferralCode(models.Model):

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="referral_code"
    )

    code = models.CharField(max_length=20, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code


class Referral(models.Model):

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("completed", "Completed"),
    )

    referrer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="referrals_made"
    )

    referred_user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="referred_by"
    )

    referral_code = models.ForeignKey(
        ReferralCode, on_delete=models.CASCADE, related_name="referrals"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.referrer} -> {self.referred_user}"


class ReferralReward(models.Model):

    REWARD_STATUS = (
        ("pending", "Pending"),
        ("credited", "Credited"),
        ("cancelled", "Cancelled"),
    )

    REWARD_TYPE = (("wallet", "Wallet"),)

    referral = models.ForeignKey(
        Referral, on_delete=models.CASCADE, related_name="rewards"
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="referral_rewards"
    )

    reward_amount = models.DecimalField(max_digits=10, decimal_places=2)

    reward_type = models.CharField(max_length=20, choices=REWARD_TYPE, default="wallet")

    status = models.CharField(max_length=20, choices=REWARD_STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
