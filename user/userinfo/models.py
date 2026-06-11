from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="userinfo_otp"
    )
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # 🔥 FIXED → 60 seconds
    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(seconds=60)

    # 🔥 FIXED → 60 seconds
    def time_left(self):
        expire_time = self.created_at + timedelta(seconds=60)
        remaining = (expire_time - timezone.now()).total_seconds()
        return max(0, int(remaining))

    def __str__(self):
        return f"{self.user.email} - {self.otp}"
