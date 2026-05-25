from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from user.products.models import CartItem
from user.addressinfo.models import Address
from .models import Order, OrderItem
from django.utils import timezone
from django.core.paginator import Paginator
import uuid
from django.db.models import Q

from datetime import timedelta


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
            'user_products:cart'
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

                # ADDRESS FOREIGN KEY

                address=selected_address,

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


@login_required(login_url='login')
def my_orders(request):

    # =====================================
    # GET FILTER VALUES
    # =====================================

    search = request.GET.get(
        'search',
        ''
    )

    status = request.GET.get(
        'status',
        ''
    )

    date_filter = request.GET.get(
        'date',
        ''
    )

    # =====================================
    # BASE QUERYSET
    # =====================================

    orders = Order.objects.filter(

        user=request.user

    ).prefetch_related(

        'items',
        'items__variant',
        'items__variant__product',
        'items__variant__images',
        'returns'

    ).order_by(

        '-created_at'

    )

    # =====================================
    # SEARCH FILTER
    # =====================================

    if search:

        orders = orders.filter(

            Q(order_id__icontains=search) |

            Q(items__variant__product__product_name__icontains=search)

        ).distinct()

    # =====================================
    # DATE FILTER
    # =====================================

    today = timezone.now()

    if date_filter == '7':

        orders = orders.filter(
            created_at__gte=today - timedelta(days=7)
        )

    elif date_filter == '30':

        orders = orders.filter(
            created_at__gte=today - timedelta(days=30)
        )

    elif date_filter == '90':

        orders = orders.filter(
            created_at__gte=today - timedelta(days=90)
        )

    # =====================================
    # DISPLAY STATUS
    # =====================================

    for order in orders:

        display_status = order.order_status

        if order.returns.filter(
            return_status='requested'
        ).exists():

            display_status = 'Return Requested'

        elif order.returns.filter(
            return_status='approved'
        ).exists():

            display_status = 'Return Approved'

        elif order.returns.filter(
            return_status='rejected'
        ).exists():

            display_status = 'Return Rejected'

        order.display_status = display_status

    # =====================================
    # STATUS FILTER
    # =====================================

    if status:

        filtered_orders = []

        for order in orders:

            if order.display_status == status:

                filtered_orders.append(order)

        orders = filtered_orders

    # =====================================
    # PAGINATION
    # =====================================

    paginator = Paginator(
        orders,
        6
    )

    page_number = request.GET.get(
        'page'
    )

    page_obj = paginator.get_page(
        page_number
    )

    context = {

        'orders': page_obj,

        'page_obj': page_obj,

        'search': search,

        'status': status,

        'date_filter': date_filter,

    }

    return render(

        request,

        'my_orders.html',

        context

    )

@login_required(login_url='login')
def order_details(request, order_id):

    order = Order.objects.filter(

        order_id=order_id,
        user=request.user

    ).prefetch_related(

        'items',
        'items__variant',
        'items__variant__images',
        'items__product',
        'returns',
        'returns__items'

    ).first()

    if not order:

        messages.error(
            request,
            'Order not found.'
        )

        return redirect(
            'my_orders'
        )
    
    if order.show_status_message:

        messages.success(

            request,

            order.status_message

        )

        order.show_status_message = False

        order.save()

    # =====================================================
    # ATTACH RETURN STATUS TO ITEMS
    # =====================================================

    for item in order.items.all():

        item.return_request = None

        for return_request in order.returns.all():

            for return_item in return_request.items.all():

                if return_item.order_item_id == item.id:

                    item.return_request = return_request

                    break
    order.has_return_request = order.returns.exists()
                  
    context = {

        'order': order

    }

    return render(

        request,

        'order_details.html',

        context

    )

@login_required(login_url='login')
def cancel_order_item(request, item_id):

    order_item = OrderItem.objects.filter(

        id=item_id,
        order__user=request.user

    ).select_related(

        'variant',
        'order'

    ).first()

    # =====================================
    # INVALID ITEM
    # =====================================

    if not order_item:

        messages.error(
            request,
            'Order item not found.'
        )

        return redirect(
            'my_orders'
        )

    # =====================================
    # ALREADY CANCELLED
    # =====================================

    if order_item.item_status == 'Cancelled':

        messages.warning(
            request,
            'Item already cancelled.'
        )

        return redirect(
            'order_details',
            order_id=order_item.order.order_id
        )

    # =====================================
    # SHIPPED / DELIVERED CHECK
    # =====================================

    if order_item.order.order_status in [

        'Shipped',
        'Out For Delivery',
        'Delivered'

    ]:

        messages.error(
            request,
            'This item can no longer be cancelled.'
        )

        return redirect(
            'order_details',
            order_id=order_item.order.order_id
        )

    # =====================================
    # POST REQUEST
    # =====================================

    if request.method == 'POST':

        cancel_reason = request.POST.get(
            'cancel_reason'
        )

        # =================================
        # UPDATE ITEM
        # =================================

        order_item.item_status = 'Cancelled'

        order_item.cancel_reason = cancel_reason

        order_item.cancelled_at = timezone.now()

        order_item.save()

        # =================================
        # RESTORE STOCK
        # =================================

        order_item.variant.stock += order_item.quantity

        order_item.variant.save()

        # =================================
        # CHECK REMAINING ACTIVE ITEMS
        # =================================

        remaining_items = order_item.order.items.exclude(
            item_status='Cancelled'
        ).exists()

        if not remaining_items:

            order_item.order.order_status = 'Cancelled'

            order_item.order.is_cancelled = True

            order_item.order.save()

        messages.success(
            request,
            'Item cancelled successfully.'
        )

        return redirect(
            'order_details',
            order_id=order_item.order.order_id
        )

    context = {

        'order_item': order_item

    }

    return render(

        request,

        'cancel_order_item.html',

        context

    )
    
@login_required(login_url='login')
def cancel_entire_order(request, order_id):

    order = Order.objects.filter(

        order_id=order_id,
        user=request.user

    ).prefetch_related(

        'items',
        'items__variant',
        'items__product'

    ).first()

    # =====================================
    # INVALID ORDER
    # =====================================

    if not order:

        messages.error(
            request,
            'Order not found.'
        )

        return redirect(
            'my_orders'
        )

    # =====================================
    # STATUS CHECK
    # =====================================

    if order.order_status in ['Shipped', 'Delivered', 'Cancelled']:

        messages.error(
            request,
            'This order cannot be cancelled.'
        )

        return redirect(
            'order_details',
            order_id=order.order_id
        )

    # =====================================
    # POST REQUEST
    # =====================================

    if request.method == 'POST':

        cancel_reason = request.POST.get(
            'cancel_reason'
        )

        # =================================
        # CANCEL ALL ACTIVE ITEMS
        # =================================

        active_items = order.items.filter(
            item_status='Active'
        )

        for item in active_items:

            # ITEM STATUS

            item.item_status = 'Cancelled'

            item.cancel_reason = cancel_reason

            item.cancelled_at = timezone.now()

            item.save()

            # RESTORE STOCK

            item.variant.stock += item.quantity

            item.variant.save()

        # =================================
        # ORDER STATUS
        # =================================

        order.order_status = 'Cancelled'

        order.is_cancelled = True

        order.save()

        messages.success(
            request,
            'Entire order cancelled successfully.'
        )

        return redirect(
            'order_details',
            order_id=order.order_id
        )

    context = {

        'order': order

    }

    return render(

        request,

        'cancel_entire_order.html',

        context

    )
    

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from .models import (
    OrderItem,
    ReturnRequest,
    ReturnItem
)


@login_required(login_url='login')
def return_single_item(request, item_id):

    order_item = get_object_or_404(

        OrderItem.objects.select_related(
            'order',
            'product',
            'variant'
        ),

        id=item_id,
        order__user=request.user,
        order__order_status='Delivered'

    )

    # =====================================
    # ALREADY RETURNED
    # =====================================

    existing_return = ReturnItem.objects.filter(
        order_item=order_item
    ).exists()

    if existing_return:

        messages.error(
            request,
            'Return request already submitted.'
        )

        return redirect(
            'order_details',
            order_id=order_item.order.order_id
        )

    # =====================================
    # POST
    # =====================================

    if request.method == 'POST':

        refund_method = request.POST.get(
            'refund_method'
        )

        return_reason = request.POST.get(
            'return_reason'
        )

        return_note = request.POST.get(
            'return_note'
        )

        # CREATE RETURN REQUEST

        return_request = ReturnRequest.objects.create(

            order=order_item.order,

            user=request.user,

            refund_method=refund_method,

            return_reason=return_reason,

            return_note=return_note,

            refund_amount=order_item.total_price

        )

        # CREATE RETURN ITEM

        ReturnItem.objects.create(

            return_request=return_request,

            order_item=order_item,

            quantity=order_item.quantity,

            refund_amount=order_item.total_price

        )

        # UPDATE ITEM STATUS

        order_item.item_status = 'Return Requested'

        order_item.save()

        messages.success(
            request,
            'Return request submitted.'
        )

        return redirect(
            'order_details',
            order_id=order_item.order.order_id
        )

    context = {

        'order_item': order_item

    }

    return render(

        request,

        'return_single_item.html',

        context

    )


@login_required(login_url='login')
def return_entire_order(request, order_id):

    order = get_object_or_404(

        Order.objects.prefetch_related(
            'items',
            'items__product',
            'items__variant'
        ),

        order_id=order_id,
        user=request.user,
        order_status='Delivered'

    )

    # =====================================
    # POST
    # =====================================

    if request.method == 'POST':

        selected_items = request.POST.getlist(
            'selected_items'
        )

        refund_method = request.POST.get(
            'refund_method'
        )

        return_reason = request.POST.get(
            'return_reason'
        )

        return_note = request.POST.get(
            'return_note'
        )

        items = order.items.filter(
            id__in=selected_items
        )

        total_refund = sum(
            item.total_price
            for item in items
        )

        # CREATE RETURN REQUEST

        return_request = ReturnRequest.objects.create(

            order=order,

            user=request.user,

            refund_method=refund_method,

            return_reason=return_reason,

            return_note=return_note,

            refund_amount=total_refund

        )

        # CREATE RETURN ITEMS

        for item in items:

            ReturnItem.objects.create(

                return_request=return_request,

                order_item=item,

                quantity=item.quantity,

                refund_amount=item.total_price

            )

            item.item_status = 'Return Requested'

            item.save()

        messages.success(
            request,
            'Return request submitted.'
        )

        return redirect(
            'order_details',
            order_id=order.order_id
        )

    context = {

        'order': order

    }

    return render(

        request,

        'return_entire_order.html',

        context

    )