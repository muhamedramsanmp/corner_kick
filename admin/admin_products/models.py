# products/models.py
from django.db import models
from admin.admin_category.models import Category
from django.utils.text import slugify


class Product(models.Model):

    product_name = models.CharField(max_length=255)

    slug = models.SlugField(unique=True, blank=True, null=True)

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products"
    )

    description_fit = models.TextField(blank=True, null=True)

    care_guide = models.TextField(blank=True, null=True)

    materials = models.TextField(blank=True, null=True)

    delivery_returns = models.TextField(blank=True, null=True)

    description = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:

        ordering = ["-created_at"]

        verbose_name = "Product"

        verbose_name_plural = "Products"

    def __str__(self):

        return self.product_name

    def save(self, *args, **kwargs):

        if not self.slug:

            from django.utils.text import slugify

            base_slug = slugify(self.product_name)

            slug = base_slug

            counter = 1

            while Product.objects.filter(slug=slug).exclude(id=self.id).exists():

                slug = f"{base_slug}-{counter}"

                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    @property
    def total_stock(self):

        return sum(variant.stock for variant in self.variants.filter(is_deleted=False))

    @property
    def active_variants(self):

        return self.variants.filter(is_active=True, is_deleted=False).count()

    @property
    def low_stock_count(self):

        return self.variants.filter(stock__lt=20, is_deleted=False).count()

    @property
    def default_variant(self):

        variant = self.variants.filter(
            is_deleted=False, is_active=True, is_default=True
        ).first()

        if variant:
            return variant

        return self.variants.filter(is_deleted=False, is_active=True).first()


class Variant(models.Model):

    SIZE_CHOICES = [
        ("XS", "XS"),
        ("S", "S"),
        ("M", "M"),
        ("L", "L"),
        ("XL", "XL"),
        ("XXL", "XXL"),
    ]

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    sku = models.CharField(max_length=100, unique=True)

    size = models.CharField(max_length=20, choices=SIZE_CHOICES, blank=True, null=True)

    color = models.CharField(max_length=100)

    price = models.DecimalField(max_digits=10, decimal_places=2)

    stock = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    is_default = models.BooleanField(default=False)

    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:

        ordering = ["-created_at"]

        verbose_name = "Variant"

        verbose_name_plural = "Variants"
        unique_together = ("product", "color", "size")

    def __str__(self):

        return f"{self.product.product_name} - {self.color} - {self.size}"

    def save(self, *args, **kwargs):

        if self.is_default:

            Variant.objects.filter(product=self.product, is_default=True).exclude(
                id=self.id
            ).update(is_default=False)

        super().save(*args, **kwargs)

    @property
    def stock_status(self):

        if self.stock <= 0:
            return "Out Of Stock"

        elif self.stock < 20:
            return "Low Stock"

        return "In Stock"

    @property
    def available_stock(self):

        from user.products.models import CartItem

        cart_quantity = (
            CartItem.objects.filter(variant=self).aggregate(
                total=models.Sum("quantity")
            )["total"]
            or 0
        )

        return max(self.stock - cart_quantity, 0)

    @property
    def primary_image(self):

        image = self.images.filter(is_primary=True).first()

        if image:
            return image.image.url

        image = self.images.first()

        if image:
            return image.image.url

        return None


class ProductImage(models.Model):

    variant = models.ForeignKey(
        Variant, on_delete=models.CASCADE, related_name="images"
    )

    image = models.ImageField(upload_to="products/")

    is_primary = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:

        ordering = ["-created_at"]

        verbose_name = "Product Image"

        verbose_name_plural = "Product Images"

    def save(self, *args, **kwargs):

        if self.is_primary:

            ProductImage.objects.filter(variant=self.variant, is_primary=True).exclude(
                id=self.id
            ).update(is_primary=False)

        super().save(*args, **kwargs)

    def __str__(self):

        return str(self.variant)
