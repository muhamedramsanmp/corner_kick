from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from user.products.models import CartItem
from user.addressinfo.models import Address
from .models import Order, OrderItem

import uuid


@login_required(login_url='login')
def checkout_page(request):

    cart_items = CartItem.objects.filter(
        cart__user=request.user
    ).select_related(
        'variant',
        'variant__product'
    )

    # =====================================
    # EMPTY CART
    # =====================================

    if not cart_items.exists():

        messages.error(
            request,
            'Your cart is empty.'
        )

        return redirect(
            'user_products:cart_page'
        )

    # =====================================
    # USER ADDRESSES
    # =====================================

    addresses = Address.objects.filter(
        user=request.user
    ).order_by(
        '-is_default'
    )

    # =====================================
    # PRICE CALCULATIONS
    # =====================================

    subtotal = sum(
        item.total_price
        for item in cart_items
    )

    shipping_charge = 0

    tax_amount = 0

    discount_amount = 0

    total_amount = (
        subtotal
        + shipping_charge
        + tax_amount
        - discount_amount
    )

    # =====================================
    # PLACE ORDER
    # =====================================

    if request.method == 'POST':

        address_id = request.POST.get(
            'selected_address'
        )

        payment_method = request.POST.get(
            'payment_method'
        )

        # =================================
        # ADDRESS VALIDATION
        # =================================

        if not address_id:

            messages.error(
                request,
                'Please select address.'
            )

            return redirect(
                'checkout_page'
            )

        try:

            selected_address = Address.objects.get(
                id=address_id,
                user=request.user
            )

        except Address.DoesNotExist:

            messages.error(
                request,
                'Invalid address.'
            )

            return redirect(
                'checkout_page'
            )

        # =================================
        # STOCK VALIDATION
        # =================================

        for item in cart_items:

            if item.quantity > item.variant.stock:

                messages.error(

                    request,

                    f'Sorry, only {item.variant.stock} stock available for {item.variant.product.product_name}.'

                )

                return redirect(
                    'checkout_page'
                )

        # =================================
        # DATABASE TRANSACTION
        # =================================

        with transaction.atomic():

            # =============================
            # CREATE ORDER
            # =============================

            order = Order.objects.create(

                user=request.user,

                order_id=str(uuid.uuid4()).replace(
                    '-',
                    ''
                )[:12].upper(),

                # ADDRESS SNAPSHOT

                full_name=selected_address.full_name,

                phone=selected_address.phone,

                address_line=selected_address.address_line,

                city=selected_address.city,

                state=selected_address.state,

                pincode=selected_address.pincode,

                country=selected_address.country,

                # PAYMENT

                payment_method=payment_method,

                # PRICE

                subtotal=subtotal,

                shipping_charge=shipping_charge,

                tax_amount=tax_amount,

                discount_amount=discount_amount,

                total_amount=total_amount,

            )

            # =============================
            # CREATE ORDER ITEMS
            # =============================

            for item in cart_items:

                OrderItem.objects.create(

                    order=order,

                    product=item.variant.product,

                    variant=item.variant,

                    quantity=item.quantity,

                    price=item.variant.price,

                    total_price=item.total_price

                )

                # =========================
                # REDUCE STOCK
                # =========================

                item.variant.stock -= item.quantity

                item.variant.save()

            # =============================
            # CLEAR CART
            # =============================

            cart_items.delete()

        # =================================
        # SUCCESS PAGE
        # =================================

        return redirect(
            'order_success',
            order_id=order.order_id
        )

    context = {

        'cart_items': cart_items,

        'addresses': addresses,

        'subtotal': subtotal,

        'shipping_charge': shipping_charge,

        'tax_amount': tax_amount,

        'discount_amount': discount_amount,

        'total_amount': total_amount,

    }

    return render(
        request,
        'checkout.html',
        context
    )

@login_required(login_url='login')
def order_success(request, order_id):

    order = Order.objects.get(
        order_id=order_id,
        user=request.user
    )

    context = {
        'order': order
    }

    return render(
        request,
        'order_success.html',
        context
    )