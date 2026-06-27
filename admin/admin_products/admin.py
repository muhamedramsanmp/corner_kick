
from django.contrib import admin

from .models import Product, ProductImage, Variant


class ProductImageInline(admin.TabularInline):

    model = ProductImage

    extra = 1


class VariantInline(admin.TabularInline):

    model = Variant

    extra = 1

    fields = ("sku", "size", "color", "price", "stock", "is_active")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "product_name",
        "category",
        "total_stock",
        "active_variants",
        "is_active",
        "created_at",
    )

    search_fields = ("product_name", "category__category_name")

    list_filter = ("category", "is_active", "is_deleted")

    prepopulated_fields = {"slug": ("product_name",)}

    inlines = [VariantInline]


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "product",
        "sku",
        "size",
        "color",
        "price",
        "stock",
        "stock_status",
        "is_active",
    )

    search_fields = ("sku", "product__product_name")

    list_filter = ("is_active", "color", "size")

    inlines = [ProductImageInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):

    list_display = ("id", "variant", "is_primary", "created_at")
