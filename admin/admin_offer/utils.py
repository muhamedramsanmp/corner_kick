from decimal import Decimal
from django.utils import timezone

from .models import Offer


def get_discount_amount(price, offer):

    if price < offer.min_purchase:
        return Decimal("0")

    if offer.discount_type == "PERCENTAGE":

        discount = (price * offer.discount_value) / Decimal("100")

        if offer.max_discount and discount > offer.max_discount:
            discount = offer.max_discount

        return discount

    return min(offer.discount_value, price)


def get_best_offer(product, price):

    today = timezone.now().date()

    product_offers = Offer.objects.filter(
        offer_products__product=product,
        apply_to="PRODUCT",
        is_active=True,
        is_deleted=False,
        start_date__lte=today,
        end_date__gte=today,
    ).distinct()

    category_offers = Offer.objects.filter(
        category_offers__category=product.category,
        apply_to="CATEGORY",
        is_active=True,
        is_deleted=False,
        start_date__lte=today,
        end_date__gte=today,
    ).distinct()

    all_offers = list(product_offers) + list(category_offers)

    if not all_offers:
        return None

    best_offer = None
    highest_discount = Decimal("0")

    for offer in all_offers:

        discount = get_discount_amount(price, offer)

        if discount > highest_discount:

            highest_discount = discount
            best_offer = offer

    return best_offer


def calculate_discounted_price(variant):

    original_price = variant.price

    offer = get_best_offer(variant.product, variant.price)

    if not offer:

        return {
            "original_price": original_price,
            "final_price": original_price,
            "discount_amount": Decimal("0"),
            "offer": None,
        }

    discount_amount = get_discount_amount(original_price, offer)

    final_price = original_price - discount_amount

    if final_price < Decimal("0"):
        final_price = Decimal("0")

    return {
        "original_price": original_price,
        "final_price": final_price,
        "discount_amount": discount_amount,
        "offer": offer,
    }
