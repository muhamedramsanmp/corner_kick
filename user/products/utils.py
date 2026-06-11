from django.db.models import Q
from .models import CartItem

def remove_invalid_cart_items(cart):

    return CartItem.objects.filter(
        cart=cart
    ).filter(
        Q(variant__is_active=False)
        | Q(variant__is_deleted=True)
        | Q(variant__product__is_active=False)
        | Q(variant__product__is_deleted=True)
        | Q(variant__product__category__is_active=False)
        | Q(variant__product__category__is_deleted=True)
    ).delete()