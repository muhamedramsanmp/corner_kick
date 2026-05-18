from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        'order_id',
        'user',
        'total_amount',
        'payment_method',
        'order_status',
        'created_at',
    )

    inlines = [OrderItemInline]


admin.site.register(OrderItem)