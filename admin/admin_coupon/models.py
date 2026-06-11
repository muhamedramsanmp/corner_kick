from django.db import models
from django.conf import settings
from user.user_orders.models import Order
import re
from django.core.exceptions import ValidationError


class Coupon(models.Model):

    DISCOUNT_TYPES = (
        ("PERCENTAGE", "Percentage"),
        ("FIXED", "Fixed Amount"),
    )

    code = models.CharField(max_length=50, unique=True)

    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)

    discount_value = models.DecimalField(max_digits=10, decimal_places=2)

    min_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    max_discount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    total_usage_limit = models.PositiveIntegerField(default=1)

    usage_limit_per_user = models.PositiveIntegerField(default=1)

    used_count = models.PositiveIntegerField(default=0)

    start_date = models.DateField()

    end_date = models.DateField()

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):

        self.code = self.code.strip().upper()

        if not re.match(r"^[A-Z0-9]+$", self.code):
            raise ValidationError(
                {"code": "Only uppercase letters and numbers allowed."}
            )
        if self.max_discount is not None:

            if self.max_discount <= 0:

                raise ValidationError(
                    {"max_discount": "Maximum discount must be greater than zero."}
                )

        if self.start_date and self.end_date:

            if self.end_date <= self.start_date:

                raise ValidationError(
                    {"end_date": "End date must be after start date."}
                )

        if self.discount_type == "PERCENTAGE":

            if self.discount_value > 50:

                raise ValidationError(
                    {"discount_value": "Percentage discount cannot exceed 50%."}
                )

        if self.discount_type == "FIXED":

            if self.discount_value > 300:

                raise ValidationError(
                    {"discount_value": "Fixed discount cannot exceed ₹300."}
                )

        if self.usage_limit_per_user > self.total_usage_limit:

            raise ValidationError(
                {"usage_limit_per_user": "User limit cannot exceed total limit."}
            )

    def save(self, *args, **kwargs):

        self.code = self.code.upper().strip()

        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self):

        return self.code


class CouponUsage(models.Model):

    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)

    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:

        unique_together = ("coupon", "user")

    @property
    def usage_percentage(self):

        if self.coupon.total_usage_limit == 0:
            return 0

        return int((self.coupon.used_count / self.coupon.total_usage_limit) * 100)
