from django.db import models
from django.conf import settings
from admin.admin_products.models import Product, Variant


# =========================================================
# ORDER MODEL
# =========================================================

class Order(models.Model):

    PAYMENT_METHODS = (
        ('COD', 'Cash On Delivery'),
    )

    ORDER_STATUS = (
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    order_id = models.CharField(
        max_length=20,
        unique=True
    )

    # =====================================
    # ADDRESS SNAPSHOT
    # =====================================

    full_name = models.CharField(max_length=100)

    phone = models.CharField(max_length=15)

    address_line = models.TextField()

    city = models.CharField(max_length=100)

    state = models.CharField(max_length=100)

    pincode = models.CharField(max_length=10)

    country = models.CharField(max_length=50)

    # =====================================
    # PAYMENT
    # =====================================

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='COD'
    )

    payment_status = models.CharField(
        max_length=20,
        default='Pending'
    )

    # =====================================
    # PRICE
    # =====================================

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    shipping_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # =====================================
    # STATUS
    # =====================================

    order_status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS,
        default='Pending'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):

        return self.order_id


# =========================================================
# ORDER ITEM MODEL
# =========================================================

class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    variant = models.ForeignKey(
        Variant,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return f"{self.order.order_id} - {self.product.product_name}"