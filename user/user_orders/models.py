from django.db import models
from django.conf import settings
from admin.admin_products.models import Product, Variant
from user.addressinfo.models import Address


class Order(models.Model):

    PAYMENT_METHODS = (
        ('COD', 'Cash On Delivery'),
    )

    ORDER_STATUS = (

        ('Pending', 'Pending'),

        ('Processing', 'Processing'),

        ('Shipped', 'Shipped'),

        ('Out For Delivery', 'Out For Delivery'),

        ('Delivered', 'Delivered'),

        ('Cancelled', 'Cancelled'),

    )

    PAYMENT_STATUS = (
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
        ('Refunded', 'Refunded'),
    )


    STATUS_FLOW = {

        'Pending': [
            'Processing',
            'Cancelled'
        ],

        'Processing': [
            'Shipped',
            'Cancelled'
        ],

        'Shipped': [
            'Out For Delivery'
        ],

        'Out For Delivery': [
            'Delivered'
        ],

        'Delivered': [],

        'Cancelled': []

    }


    # =====================================
    # GET NEXT ALLOWED STATUS
    # =====================================

    def allowed_next_statuses(self):

        return self.STATUS_FLOW.get(
            self.order_status,
            []
        )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='Pending'
    )

    # =====================================
    # ADMIN NOTES
    # =====================================

    admin_note = models.TextField(
        blank=True,
        null=True
    )


    delivered_at = models.DateTimeField(
        blank=True,
        null=True
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

    address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='COD'
    )

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

    is_cancelled = models.BooleanField(
        default=False
    )
    status_message = models.CharField(
    max_length=255,
    blank=True,
    null=True
    )

    show_status_message = models.BooleanField(
        default=False
    )

    def __str__(self):

        return self.order_id


class OrderItem(models.Model):

    ITEM_STATUS = (
        ('Active', 'Active'),
        ('Cancelled', 'Cancelled'),
        ('Return Requested', 'Return Requested'),
        ('Returned', 'Returned'),
    )


    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True
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

    item_status = models.CharField(
        max_length=30,
        choices=ITEM_STATUS,
        default='Active'
    )

    cancel_reason = models.TextField(
        blank=True,
        null=True
    )

    cancelled_at = models.DateTimeField(
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    returned_at = models.DateTimeField(
    blank=True,
    null=True
    )

    def __str__(self):

        return f"{self.order.order_id} - {self.product.product_name}"
    
# =========================================================
# RETURN REQUEST
# =========================================================

class ReturnRequest(models.Model):

    RETURN_STATUS = (

        

        ('requested', 'Requested'),

        ('approved', 'Approved'),

        ('rejected', 'Rejected'),

        ('returned', 'Returned'),

    )

    REFUND_METHODS = (

        ('Original Payment', 'Original Payment'),

        ('Store Wallet', 'Store Wallet'),

    )

    order = models.ForeignKey(

        Order,

        on_delete=models.CASCADE,

        related_name='returns'

    )

    user = models.ForeignKey(

        settings.AUTH_USER_MODEL,

        on_delete=models.CASCADE

    )

    refund_method = models.CharField(

        max_length=50,

        choices=REFUND_METHODS

    )
    admin_response = models.TextField(
        blank=True,
        null=True
    )

    processed_at = models.DateTimeField(
        blank=True,
        null=True
    )

    return_reason = models.CharField(
        max_length=255
    )

    return_note = models.TextField(
        blank=True,
        null=True
    )

    refund_amount = models.DecimalField(

        max_digits=10,
        decimal_places=2,
        default=0

    )

    return_status = models.CharField(

        max_length=20,

        choices=RETURN_STATUS,

        default='requested'

    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):

        return f"Return - {self.order.order_id}"


# =========================================================
# RETURN ITEMS
# =========================================================

class ReturnItem(models.Model):

    return_request = models.ForeignKey(

        ReturnRequest,

        on_delete=models.CASCADE,

        related_name='items'

    )

    order_item = models.ForeignKey(

        OrderItem,

        on_delete=models.CASCADE

    )


    quantity = models.PositiveIntegerField(
        default=1
    )

    refund_amount = models.DecimalField(

        max_digits=10,
        decimal_places=2

    )
    @property
    def total_refund_amount(self):
        return sum(
            item.refund_amount
            for item in self.items.all()
        )

    def __str__(self):

        return self.order_item.product.product_name
    
class Meta:
    indexes = [
        models.Index(fields=['order_status']),
        models.Index(fields=['created_at']),
    ]