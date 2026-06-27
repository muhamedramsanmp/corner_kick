import uuid
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from admin.admin_coupon.models import Coupon
from admin.admin_offer.utils import calculate_discounted_price
from user.accounts.utils import credit_referral_reward
from user.user_orders.models import Order, OrderItem
from user.user_wallet.models import Wallet, WalletTransaction

from .models import Order, OrderItem


def get_cart_summary(cart_items):

    subtotal = Decimal("0")
    offer_discount = Decimal("0")

    for item in cart_items:
        price_data = calculate_discounted_price(item.variant)
        item.checkout_total = price_data["final_price"] * item.quantity
        item.original_total = price_data["original_price"] * item.quantity

        subtotal += price_data["original_price"] * item.quantity
        offer_discount += price_data["discount_amount"] * item.quantity

    return subtotal, offer_discount


def validate_and_apply_coupon(coupon, user, amount_after_offer):

    today = timezone.now().date()
    is_valid = True
    discount_amount = Decimal("0")

    if coupon.total_usage_limit:
        total_used = Order.objects.filter(coupon=coupon).count()
        if total_used >= coupon.total_usage_limit:
            is_valid = False

    if coupon.usage_limit_per_user:
        user_used = Order.objects.filter(user=user, coupon=coupon).count()
        if user_used >= coupon.usage_limit_per_user:
            is_valid = False

    if not coupon.is_active:
        is_valid = False

    if coupon.start_date and today < coupon.start_date:
        is_valid = False

    if coupon.end_date and today > coupon.end_date:
        is_valid = False

    if coupon.min_purchase and amount_after_offer < coupon.min_purchase:
        is_valid = False

    if is_valid:
        if coupon.discount_type == "PERCENTAGE":
            discount_amount = (amount_after_offer * coupon.discount_value) / 100
            if coupon.max_discount:
                discount_amount = min(discount_amount, coupon.max_discount)
        else:
            discount_amount = Decimal(coupon.discount_value)

        discount_amount = min(Decimal(discount_amount), amount_after_offer)

    return is_valid, discount_amount


def resolve_coupon(request, coupon_code=None):
    coupon_id = request.session.get("coupon_id")
    coupon = None

    if coupon_id:
        try:
            coupon = Coupon.objects.get(id=coupon_id, is_deleted=False)
        except Coupon.DoesNotExist:
            pass

    if not coupon and coupon_code:
        try:
            coupon = Coupon.objects.get(code__iexact=coupon_code, is_deleted=False)
        except Coupon.DoesNotExist:
            pass

    return coupon


def create_order_with_items(
    user,
    cart_items,
    selected_address,
    payment_method,
    payment_status,
    subtotal,
    offer_discount,
    discount_amount,
    total_amount,
    shipping_charge,
    tax_amount,
    applied_coupon,
):
    order = Order.objects.create(
        user=user,
        order_id=str(uuid.uuid4()).replace("-", "")[:12].upper(),
        coupon=applied_coupon,
        address=selected_address,
        payment_method=payment_method,
        payment_status=payment_status,
        subtotal=subtotal,
        shipping_charge=shipping_charge,
        tax_amount=tax_amount,
        discount_amount=discount_amount,
        total_amount=total_amount,
        offer_discount=offer_discount,
    )

    for item in cart_items:
        price_data = calculate_discounted_price(item.variant)

        OrderItem.objects.create(
            order=order,
            product=item.variant.product,
            variant=item.variant,
            quantity=item.quantity,
            original_price=price_data["original_price"],
            offer_discount=price_data["discount_amount"],
            offer_name=(
                price_data["offer"].offer_name if price_data["offer"] else None
            ),
            price=price_data["final_price"],
            total_price=price_data["final_price"] * item.quantity,
        )

        item.variant.stock -= item.quantity
        item.variant.save()

    return order


def process_cod_payment(
    request,
    cart_items,
    selected_address,
    subtotal,
    offer_discount,
    discount_amount,
    total_amount,
    shipping_charge,
    tax_amount,
    applied_coupon,
):

    with transaction.atomic():
        order = create_order_with_items(
            user=request.user,
            cart_items=cart_items,
            selected_address=selected_address,
            payment_method="COD",
            payment_status="Pending",
            subtotal=subtotal,
            offer_discount=offer_discount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            shipping_charge=shipping_charge,
            tax_amount=tax_amount,
            applied_coupon=applied_coupon,
        )
        cart_items.delete()
        request.session.pop("coupon_id", None)

    return redirect("order_success", order_id=order.order_id)


def process_wallet_payment(
    request,
    cart_items,
    selected_address,
    subtotal,
    offer_discount,
    discount_amount,
    total_amount,
    shipping_charge,
    tax_amount,
    applied_coupon,
):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    if wallet.balance < total_amount:
        messages.error(
            request,
            f"Insufficient wallet balance. Available balance ₹{wallet.balance}",
        )
        return redirect("checkout_page")

    with transaction.atomic():
        wallet.balance -= total_amount
        wallet.save()

        order = create_order_with_items(
            user=request.user,
            cart_items=cart_items,
            selected_address=selected_address,
            payment_method="WALLET",
            payment_status="Paid",
            subtotal=subtotal,
            offer_discount=offer_discount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            shipping_charge=shipping_charge,
            tax_amount=tax_amount,
            applied_coupon=applied_coupon,
        )

        credit_referral_reward(request, request.user, order)

        WalletTransaction.objects.create(
            wallet=wallet,
            order=order,
            transaction_type="DEBIT",
            status="SUCCESS",
            amount=total_amount,
            description=f"Wallet payment for order {order.order_id}",
        )

        cart_items.delete()
        request.session.pop("coupon_id", None)

    return redirect("order_success", order_id=order.order_id)


def process_razorpay_payment(
    request,
    cart_items,
    addresses,
    subtotal,
    offer_discount,
    discount_amount,
    total_amount,
    shipping_charge,
    applied_coupon,
    address_id,
):
    from django.shortcuts import render

    request.session["checkout_data"] = {
        "subtotal": str(subtotal),
        "offer_discount": str(offer_discount),
        "discount_amount": str(discount_amount),
        "total_amount": str(total_amount),
        "coupon_id": (applied_coupon.id if applied_coupon else None),
    }

    return render(
        request,
        "checkout.html",
        {
            "cart_items": cart_items,
            "addresses": addresses,
            "subtotal": subtotal,
            "shipping_charge": shipping_charge,
            "discount_amount": discount_amount,
            "total_amount": total_amount,
            "open_razorpay": True,
            "selected_address_id": address_id,
        },
    )


def build_checkout_context(
    request,
    cart_items,
    addresses,
    subtotal,
    offer_discount,
    shipping_charge,
    tax_amount,
    coupons,
):

    amount_after_offer = subtotal - offer_discount
    coupon_discount = Decimal("0")
    applied_coupon_code = None

    coupon_id = request.session.get("coupon_id")
    if coupon_id:
        coupon = Coupon.objects.filter(id=coupon_id).first()
        if coupon:
            applied_coupon_code = coupon.code
            if coupon.discount_type == "PERCENTAGE":
                coupon_discount = (amount_after_offer * coupon.discount_value) / 100
                if coupon.max_discount and coupon_discount > coupon.max_discount:
                    coupon_discount = coupon.max_discount
            else:
                coupon_discount = Decimal(coupon.discount_value)

    total_amount = amount_after_offer - coupon_discount
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    return {
        "cart_items": cart_items,
        "addresses": addresses,
        "subtotal": subtotal,
        "shipping_charge": shipping_charge,
        "tax_amount": tax_amount,
        "discount_amount": coupon_discount,
        "total_amount": total_amount,
        "amount_after_offer": amount_after_offer,
        "wallet": wallet,
        "coupons": coupons,
        "offer_discount": offer_discount,
        "applied_coupon": applied_coupon_code,
        "coupon_discount": coupon_discount,
    }
