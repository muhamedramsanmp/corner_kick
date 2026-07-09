import re

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
import re
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

from admin.admin_category.models import Category
from admin.admin_products.models import Product

from admin.admin_category.models import Category

class Offer(models.Model):

    DISCOUNT_TYPES = (
        ("PERCENTAGE", "Percentage"),
        ("FIXED", "Fixed Amount"),
    )

    APPLY_TO_CHOICES = (
        ("PRODUCT", "Product"),
        ("CATEGORY", "Category"),
    )

    offer_name = models.CharField(max_length=200)

    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)

    discount_value = models.DecimalField(max_digits=10, decimal_places=2)

    min_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    max_discount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    apply_to = models.CharField(max_length=20, choices=APPLY_TO_CHOICES)

    start_date = models.DateField()

    end_date = models.DateField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    is_deleted = models.BooleanField(default=False)

    def clean(self):

        today = timezone.now().date()
        if not re.match(r"^(?=.*[A-Za-z])[A-Za-z0-9 ]+$", self.offer_name):

            raise ValidationError(
                {
                    "offer_name": "Offer name can contain only letters, numbers and spaces."
                }
            )
        if self.offer_name.isdigit():

            raise ValidationError(
                {"offer_name": "Offer name cannot contain only numbers."}
            )

        if self.start_date > self.end_date:

            raise ValidationError(
                {"end_date": "End date must be greater than start date."}
            )

        if self.discount_value <= 0:

            raise ValidationError(
                {"discount_value": "Discount value must be greater than zero."}
            )

        if self.discount_type == "PERCENTAGE":

            if self.discount_value > 50:

                raise ValidationError(
                    {"discount_value": "Percentage discount cannot exceed 50."}
                )

        if self.max_discount is not None:

            if self.max_discount <= 0:

                raise ValidationError(
                    {
                        "max_discount":
                        "Maximum discount must be greater than zero."
                    }
                )

            max_allowed_max_discount = (
                self.min_purchase * Decimal("0.50")
            )

            if self.max_discount > max_allowed_max_discount:

                raise ValidationError(
                    {
                        "max_discount":
                        f"Maximum discount cannot exceed 50% "
                        f"of minimum purchase amount "
                        f"(₹{max_allowed_max_discount})."
                    }
                )
                    
        if self.discount_type == "PERCENTAGE":

            if self.max_discount > 5000:
                raise ValidationError(
                    {
                        "max_discount":
                        "Maximum discount cannot exceed ₹5000."
                    }
                )

        if self.min_purchase < 0:

            raise ValidationError(
                {"min_purchase": "Minimum purchase cannot be negative."}
            )
        if (
            self.discount_type == "FIXED" and
            self.apply_to == "PRODUCT"
        ):
            linked_products = self.offer_products.all()

            for item in linked_products:
                cheapest_variant = (
                    item.product.variants
                    .filter(is_deleted=False)
                    .order_by("price")
                    .first()
                )

                if (
                    cheapest_variant and
                    self.discount_value >= cheapest_variant.price
                ):
                    raise ValidationError(
                        {
                            "discount_value":
                            "Flat discount cannot be greater than or equal to product price."
                        }
                    )

        duplicate_offer = Offer.objects.filter(
            offer_name__iexact=self.offer_name, is_deleted=False
        ).exclude(id=self.id)

        if duplicate_offer.exists():

            raise ValidationError({"offer_name": "Offer name already exists."})

    def save(self, *args, **kwargs):

        self.offer_name = self.offer_name.title()

        self.full_clean()

        super().save(*args, **kwargs)

    @property
    def is_expired(self):

        return self.end_date < timezone.now().date()

    def __str__(self):

        return self.offer_name


class OfferProduct(models.Model):

    offer = models.ForeignKey(
        Offer, on_delete=models.CASCADE, related_name="offer_products"
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:

        unique_together = ("offer", "product")


class CategoryOffer(models.Model):

    offer = models.ForeignKey(
        Offer, on_delete=models.CASCADE, related_name="category_offers"
    )

    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:

        unique_together = ("offer", "category")



class Offer(models.Model):

    DISCOUNT_TYPES = (
        ("PERCENTAGE", "Percentage"),
        ("FIXED", "Fixed Amount"),
    )

    APPLY_TO_CHOICES = (
        ("PRODUCT", "Product"),
        ("CATEGORY", "Category"),
    )

    offer_name = models.CharField(max_length=200)

    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)

    discount_value = models.DecimalField(max_digits=10, decimal_places=2)

    min_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    max_discount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    apply_to = models.CharField(max_length=20, choices=APPLY_TO_CHOICES)

    start_date = models.DateField()

    end_date = models.DateField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    is_deleted = models.BooleanField(default=False)

    def clean(self):

        today = timezone.now().date()
        if not re.match(r"^(?=.*[A-Za-z])[A-Za-z0-9 ]+$", self.offer_name):

            raise ValidationError(
                {
                    "offer_name": "Offer name can contain only letters, numbers and spaces."
                }
            )
        if self.offer_name.isdigit():

            raise ValidationError(
                {"offer_name": "Offer name cannot contain only numbers."}
            )

        if self.start_date > self.end_date:

            raise ValidationError(
                {"end_date": "End date must be greater than start date."}
            )

        if self.discount_value <= 0:

            raise ValidationError(
                {"discount_value": "Discount value must be greater than zero."}
            )

        if self.discount_type == "PERCENTAGE":

            if self.discount_value > 50:

                raise ValidationError(
                    {"discount_value": "Percentage discount cannot exceed 50."}
                )

        if self.max_discount is not None:

            if self.max_discount <= 0:

                raise ValidationError(
                    {"max_discount": "Maximum discount must be greater than zero."}
                )

        if self.min_purchase < 0:

            raise ValidationError(
                {"min_purchase": "Minimum purchase cannot be negative."}
            )
        if self.discount_type == "FIXED":

            if self.discount_value >= self.min_purchase and self.min_purchase > 0:

                raise ValidationError(
                    {
                        "discount_value":
                        "Flat offer amount must be less than minimum purchase amount."
                    }
                )
            
            max_allowed_discount = self.min_purchase * Decimal("0.50")

            if (
                self.min_purchase > 0 and
                self.discount_value > max_allowed_discount
            ):

                raise ValidationError(
                    {
                        "discount_value":
                        f"Flat offer cannot exceed 50% of minimum purchase "
                        f"(₹{max_allowed_discount})."
                    }
                )

        duplicate_offer = Offer.objects.filter(
            offer_name__iexact=self.offer_name, is_deleted=False
        ).exclude(id=self.id)

        if duplicate_offer.exists():

            raise ValidationError({"offer_name": "Offer name already exists."})

    def save(self, *args, **kwargs):

        self.offer_name = self.offer_name.title()

        self.full_clean()

        super().save(*args, **kwargs)

    @property
    def is_expired(self):

        return self.end_date < timezone.now().date()

    def __str__(self):

        return self.offer_name


class OfferProduct(models.Model):

    offer = models.ForeignKey(
        Offer, on_delete=models.CASCADE, related_name="offer_products"
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:

        unique_together = ("offer", "product")


class CategoryOffer(models.Model):

    offer = models.ForeignKey(
        Offer, on_delete=models.CASCADE, related_name="category_offers"
    )

    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:

        unique_together = ("offer", "category")

    @property
    def current_status(self):

        today = timezone.now().date()

        if self.offer.end_date < today:
            return "Expired"

        if (
            self.offer.is_active
            and self.offer.start_date <= today <= self.offer.end_date
        ):
            return "Active"

        return "Inactive"
