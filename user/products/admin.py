from django.contrib import admin
from .models import Cart, CartItem
from .models import Wishlist

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):

    list_display = (

        'id',

        'user',

        'total_items',

        'total_price',

        'created_at'

    )


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):

    list_display = (

        'id',

        'cart',

        'variant',

        'quantity',

        'total_price'

    )

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):

    list_display = (

        'id',

        'user',

        'product',

        'created_at'

    )    