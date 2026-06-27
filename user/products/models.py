from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify

from admin.admin_offer.utils import calculate_discounted_price
from admin.admin_products.models import Product, Variant
from user.user_orders.models import Order


def save(self, *args, **kwargs):

    if not self.slug:

        base_slug = slugify(self.product_name)

        slug = base_slug

        counter = 1

        while Product.objects.filter(slug=slug).exclude(id=self.id).exists():

            slug = f"{base_slug}-{counter}"

            counter += 1

        self.slug = slug

    super().save(*args, **kwargs)


class Cart(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):

        return f"{self.user}'s Cart"

    @property
    def total_price(self):

        return sum(item.total_price for item in self.items.all())

    @property
    def total_items(self):

        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")

    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:

        unique_together = ("cart", "variant")

    def __str__(self):

        return f"{self.variant} x {self.quantity}"

    @property
    def total_price(self):

        price_data = calculate_discounted_price(self.variant)

        return price_data["final_price"] * self.quantity


class Wishlist(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist"
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:

        unique_together = ("user", "product")

    def __str__(self):

        return f"{self.user} - {self.product.product_name}"


class Review(models.Model):

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="reviews")

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ]
    )

    review_text = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    review_message = models.CharField(max_length=255, blank=True, null=True)

    show_message = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "product")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.product}"
