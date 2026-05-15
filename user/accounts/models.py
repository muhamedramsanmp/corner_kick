from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta


User = get_user_model()


class OTP(models.Model):

    PURPOSE_CHOICES = (
        ('signup', 'Signup'),
        ('reset', 'Reset Password'),
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
        User,
        on_delete=models.CASCADE,
        related_name='account_profile'
    )

    image = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True
    )
    phone = models.CharField(   # 🔥 ADD THIS
        max_length=15,
        blank=True,
        null=True
    )

    def __str__(self):
        return self.user.email