from django.shortcuts import render, redirect, get_object_or_404
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
from user.decorators import user_required
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from datetime import timedelta
from decimal import Decimal
from .models import OrderItem, ReturnRequest, ReturnItem
from user.user_wallet.models import Wallet, WalletTransaction
import uuid
import razorpay
from user.products.models import Cart,CartItem
import json
from django.http import JsonResponse
from django.conf import settings
from user.user_wallet.models import Wallet
from admin.admin_coupon.models import Coupon
from user.user_orders.models import Order, OrderItem
from user.accounts.utils import credit_referral_reward
from admin.admin_offer.utils import calculate_discounted_price
from user.products.utils import remove_invalid_cart_items

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from user.addressinfo.models import Address

from user.products.utils import remove_invalid_cart_items
from .checkout_helpers import (
    get_cart_summary,
    resolve_coupon,
    validate_and_apply_coupon,
    process_cod_payment,
    process_wallet_payment,
    process_razorpay_payment,
    build_checkout_context,
)


SHIPPING_CHARGE = 0
TAX_AMOUNT = 0


@login_required
def checkout_page(request):
    cart = Cart.objects.filter(user=request.user).first()
    if cart:
        remove_invalid_cart_items(cart)

    cart_items = CartItem.objects.filter(
        cart__user=request.user
    ).select_related("variant", "variant__product")

    if not cart_items.exists():
        messages.error(request, "One or more products are no longer available.")
        return redirect("user_products:cart")

    addresses = Address.objects.filter(user=request.user).order_by("-is_default")
    coupons = Coupon.objects.filter(is_active=True)
    subtotal, offer_discount = get_cart_summary(cart_items)
    amount_after_offer = subtotal - offer_discount

    if request.method == "POST":

        if cart:
            remove_invalid_cart_items(cart)

        cart_items = CartItem.objects.filter(
            cart__user=request.user
        ).select_related("variant", "variant__product")

        if not cart_items.exists():
            messages.error(request, "One or more products are no longer available.")
            return redirect("user_products:cart")

        address_id = request.POST.get("selected_address")
        payment_method = request.POST.get("payment_method")
        coupon_code = request.POST.get("coupon_code")

        coupon = resolve_coupon(request, coupon_code)
        discount_amount, applied_coupon = _apply_coupon_if_valid(
            coupon, request.user, amount_after_offer
        )

        total_amount = amount_after_offer - discount_amount + SHIPPING_CHARGE + TAX_AMOUNT

        if not address_id:
            messages.error(request, "Please select address.")
            return redirect("checkout_page")

        try:
            selected_address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            messages.error(request, "Invalid address.")
            return redirect("checkout_page")

        for item in cart_items:
            if item.quantity > item.variant.stock:
                messages.error(
                    request,
                    f"Only {item.variant.stock} stock available for "
                    f"{item.variant.product.product_name}",
                )
                return redirect("checkout_page")
        common_kwargs = dict(
            request=request,
            cart_items=cart_items,
            selected_address=selected_address,
            subtotal=subtotal,
            offer_discount=offer_discount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            shipping_charge=SHIPPING_CHARGE,
            tax_amount=TAX_AMOUNT,
            applied_coupon=applied_coupon,
        )

        if payment_method == "COD":
            return process_cod_payment(**common_kwargs)

        elif payment_method == "WALLET":
            return process_wallet_payment(**common_kwargs)

        elif payment_method == "RAZORPAY":
            return process_razorpay_payment(
                **common_kwargs,
                addresses=addresses,
                address_id=address_id,
            )

    context = build_checkout_context(
        request=request,
        cart_items=cart_items,
        addresses=addresses,
        subtotal=subtotal,
        offer_discount=offer_discount,
        shipping_charge=SHIPPING_CHARGE,
        tax_amount=TAX_AMOUNT,
        coupons=coupons,
    )
    return render(request, "checkout.html", context)

def _apply_coupon_if_valid(coupon, user, amount_after_offer):
 
    from decimal import Decimal

    if not coupon:
        return Decimal("0"), None

    is_valid, discount_amount = validate_and_apply_coupon(
        coupon, user, amount_after_offer
    )

    if is_valid:
        return discount_amount, coupon

    return Decimal("0"), None


@user_required
def create_razorpay_order(request):

    if request.method != "POST":
        
        return JsonResponse({"success": False}, status=400)
    

    data = json.loads(request.body)

    amount = int(float(data["amount"]) * 100)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    razorpay_order = client.order.create(
        {"amount": amount, "currency": "INR", "payment_capture": 1}
    )

    return JsonResponse(
        {
            "key": settings.RAZORPAY_KEY_ID,
            "amount": razorpay_order["amount"],
            "razorpay_order_id": razorpay_order["id"],
        }
    )
    


@user_required
def payment_success(request):

    razorpay_payment_id = request.GET.get("payment_id")

    razorpay_order_id = request.GET.get("order_id")

    razorpay_signature = request.GET.get("signature")

    address_id = request.GET.get("address_id")

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    try:

        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )

    except Exception:

        return redirect("payment_failed")

    address = Address.objects.filter(id=address_id, user=request.user).first()

    if not address:

        messages.error(request, "Address not found")

        return redirect("checkout_page")

    cart = Cart.objects.filter(user=request.user).first()

    if not cart:

        messages.error(request, "Cart not found")

        return redirect("user_products:cart")

    cart_items = CartItem.objects.filter(cart=cart).select_related(
        "variant", "variant__product"
    )

    subtotal = Decimal("0")
    offer_discount = Decimal("0")

    for item in cart_items:

        price_data = calculate_discounted_price(item.variant)

        subtotal += price_data["original_price"] * item.quantity

        offer_discount += price_data["discount_amount"] * item.quantity

    applied_coupon = None
    discount_amount = Decimal("0")
    coupon_id = request.session.get("coupon_id")
    if coupon_id:
        try:
            coupon = Coupon.objects.get(id=coupon_id, is_active=True, is_deleted=False)
            amount_after_offer = subtotal - offer_discount
            
            # Re-validate
            today = timezone.now().date()
            is_valid = True
            if coupon.total_usage_limit:
                total_used = Order.objects.filter(coupon=coupon).count()
                if total_used >= coupon.total_usage_limit:
                    is_valid = False
            if coupon.usage_limit_per_user:
                user_used = Order.objects.filter(user=request.user, coupon=coupon).count()
                if user_used >= coupon.usage_limit_per_user:
                    is_valid = False
            if coupon.start_date and today < coupon.start_date:
                is_valid = False
            if coupon.end_date and today > coupon.end_date:
                is_valid = False
            if coupon.min_purchase and amount_after_offer < coupon.min_purchase:
                is_valid = False
                
            if is_valid:
                applied_coupon = coupon
                if coupon.discount_type == "PERCENTAGE":
                    discount_amount = (amount_after_offer * coupon.discount_value) / 100
                    if coupon.max_discount:
                        discount_amount = min(discount_amount, coupon.max_discount)
                else:
                    discount_amount = coupon.discount_value
                
                if discount_amount > amount_after_offer:
                    discount_amount = amount_after_offer
                    
                discount_amount = Decimal(discount_amount)
        except Coupon.DoesNotExist:
            pass

    total_amount = subtotal - offer_discount - discount_amount

    with transaction.atomic():

        order = Order.objects.create(
            user=request.user,
            order_id=str(uuid.uuid4()).replace("-", "")[:12].upper(),
            coupon=applied_coupon,
            address=address,
            payment_method="RAZORPAY",
            payment_status="Paid",
            order_status="Pending",
            subtotal=subtotal,
            shipping_charge=0,
            tax_amount=0,
            discount_amount=discount_amount,
            offer_discount=offer_discount,
            total_amount=total_amount,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
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
                total_price=(price_data["final_price"] * item.quantity),
            )

            item.variant.stock -= item.quantity

            item.variant.save()

        credit_referral_reward(request, request.user, order)

        cart_items.delete()
        request.session.pop("coupon_id", None)

    return redirect("pay_success", order_id=order.order_id)


@user_required
def pay_success(request, order_id):

    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    context = {"order": order}
    messages.success(request, "payment success")
    return render(request, "payment_success.html", context)


@user_required
def payment_failed(request):

    messages.error(request, "Payment Failed")

    return render(request, "payment_failed.html")


@login_required(login_url="login")
def order_success(request, order_id):

    order = Order.objects.get(order_id=order_id, user=request.user)

    context = {"order": order}

    return render(request, "order_success.html", context)


@user_required
def my_orders(request):

    search = request.GET.get("search", "")

    status = request.GET.get("status", "")

    date_filter = request.GET.get("date", "")

    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related(
            "items",
            "items__variant",
            "items__variant__product",
            "items__variant__images",
            "returns",
        )
        .order_by("-created_at")
    )

    if search:

        orders = orders.filter(
            Q(order_id__icontains=search)
            | Q(items__variant__product__product_name__icontains=search)
        ).distinct()

    today = timezone.now()

    if date_filter == "7":

        orders = orders.filter(created_at__gte=today - timedelta(days=7))

    elif date_filter == "30":

        orders = orders.filter(created_at__gte=today - timedelta(days=30))

    elif date_filter == "90":

        orders = orders.filter(created_at__gte=today - timedelta(days=90))

    for order in orders:

        display_status = order.order_status

        if order.returns.filter(return_status="requested").exists():

            display_status = "Return Requested"

        elif order.returns.filter(return_status="approved").exists():

            display_status = "Return Approved"

        elif order.returns.filter(return_status="rejected").exists():

            display_status = "Return Rejected"

        order.display_status = display_status

    if status:

        filtered_orders = []

        for order in orders:

            if order.display_status == status:

                filtered_orders.append(order)

        orders = filtered_orders

    paginator = Paginator(orders, 6)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    context = {
        "orders": page_obj,
        "page_obj": page_obj,
        "search": search,
        "status": status,
        "date_filter": date_filter,
    }

    return render(request, "my_orders.html", context)


@login_required(login_url="login")
def order_details(request, order_id):

    order = (
        Order.objects.filter(order_id=order_id, user=request.user)
        .prefetch_related(
            "items",
            "items__variant",
            "items__variant__images",
            "items__product",
            "returns",
            "returns__items",
        )
        .first()
    )

    if not order:

        messages.error(request, "Order not found.")

        return redirect("my_orders")

    if order.show_status_message:

        messages.success(request, order.status_message)

        order.show_status_message = False

        order.save()

    for item in order.items.all():

        item.return_request = None

        for return_request in order.returns.all():

            for return_item in return_request.items.all():

                if return_item.order_item_id == item.id:

                    item.return_request = return_request

                    break
    order.has_return_request = order.returns.exists()

    summary_subtotal = 0
    summary_offer_discount = 0

    for item in order.items.filter(item_status="Active"):

        summary_subtotal += item.original_price * item.quantity

        summary_offer_discount += item.offer_discount * item.quantity

    active_items = order.items.filter(item_status="Active")

    if active_items.exists():

        active_total = sum(
            item.total_price
            for item in active_items
        )

        original_total = sum(
            item.total_price
            for item in order.items.all()
        )

        if original_total > 0:

            summary_coupon_discount = (
                order.discount_amount
                * active_total
                / original_total
            ).quantize(Decimal("0.01"))

        else:

            summary_coupon_discount = 0

    else:

        summary_coupon_discount = 0

    summary_total = (
        summary_subtotal
        - summary_offer_discount
        - summary_coupon_discount
        + order.shipping_charge
        + order.tax_amount
    ).quantize(Decimal("0.01"))

    all_items_price_sum = sum(
        i.total_price for i in order.items.all()
    )

    for item in order.items.all():

        if all_items_price_sum > 0:

            item.coupon_share = (
                item.total_price * order.discount_amount
            ) / all_items_price_sum

            item.coupon_share = item.coupon_share.quantize(
                Decimal("0.01")
            )

            item.final_paid_amount = (
                item.total_price - item.coupon_share
            ).quantize(
                Decimal("0.01")
            )

        else:

            item.coupon_share = 0

            item.final_paid_amount = item.total_price

    context = {
        "order": order,
        "summary_subtotal": summary_subtotal,
        "summary_offer_discount": summary_offer_discount,
        "summary_coupon_discount": summary_coupon_discount,
        "summary_total": summary_total,
    }

    return render(request, "order_details.html", context)


@login_required
def remove_coupon(request):

    if "coupon_id" in request.session:

        del request.session["coupon_id"]

    return JsonResponse({"success": True})


@login_required(login_url="login")
def cancel_order_item(request, item_id):

    order_item = (
        OrderItem.objects.filter(id=item_id, order__user=request.user)
        .select_related("variant", "order")
        .first()
    )

    if not order_item:

        messages.error(request, "Order item not found.")

        return redirect("my_orders")

    if order_item.item_status == "Cancelled":

        messages.warning(request, "Item already cancelled.")

        return redirect("order_details", order_id=order_item.order.order_id)

    if order_item.order.order_status in ["Shipped", "Out For Delivery", "Delivered"]:

        messages.error(request, "This item can no longer be cancelled.")

        return redirect("order_details", order_id=order_item.order.order_id)

    if request.method == "POST":

        cancel_reason = request.POST.get("cancel_reason")

        order_item.item_status = "Cancelled"

        order_item.cancel_reason = cancel_reason

        order_item.cancelled_at = timezone.now()

        order_item.save()

        order_item.variant.stock += order_item.quantity

        order_item.variant.save()


        if order_item.order.payment_method in ["RAZORPAY", "WALLET"]:

            wallet, created = Wallet.objects.get_or_create(user=order_item.order.user)

            order = order_item.order
            all_items_price_sum = sum(
                i.total_price for i in order.items.all()
            )
            if all_items_price_sum > 0:
                refund_amount = (
                    order_item.total_price * order.total_amount
                ) / all_items_price_sum
            else:
                refund_amount = Decimal("0")

            refund_amount = refund_amount.quantize(Decimal("0.01"))

            wallet.balance += refund_amount

            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type="CREDIT",
                amount=refund_amount,
                order=order_item.order,
                status="SUCCESS",
                description=(
                    f"Refund for cancelled item "
                    f"in order "
                    f"{order_item.order.order_id}"
                ),
            )

        remaining_items = order_item.order.items.exclude(
            item_status="Cancelled"
        ).exists()

        if not remaining_items:

            order_item.order.order_status = "Cancelled"

            order_item.order.is_cancelled = True

            order_item.order.save()

        messages.success(request, "Item cancelled successfully.")

        return redirect("order_details", order_id=order_item.order.order_id)

    context = {"order_item": order_item}

    return render(request, "cancel_order_item.html", context)


@login_required(login_url="login")
def cancel_entire_order(request, order_id):

    order = (
        Order.objects.filter(order_id=order_id, user=request.user)
        .prefetch_related("items", "items__variant", "items__product")
        .first()
    )

    if not order:

        messages.error(request, "Order not found.")

        return redirect("my_orders")

    if order.order_status in ["Shipped", "Delivered", "Cancelled"]:

        messages.error(request, "This order cannot be cancelled.")

        return redirect("order_details", order_id=order.order_id)

    if request.method == "POST":

        cancel_reason = request.POST.get("cancel_reason")

        active_items = order.items.filter(item_status="Active")

        # Proportional refund: distribute order.total_amount across items
        # by each item's share of the total offer-discounted item prices
        all_items_price_sum = sum(i.total_price for i in order.items.all())

        refund_amount = Decimal("0")

        for item in active_items:

            # Proportional share of what was actually paid
            if all_items_price_sum > 0:
                item_refund = (
                    item.total_price * order.total_amount
                ) / all_items_price_sum
            else:
                item_refund = Decimal("0")

            refund_amount += item_refund

            item.item_status = "Cancelled"

            item.cancel_reason = cancel_reason

            item.cancelled_at = timezone.now()

            item.save()

            item.variant.stock += item.quantity

            item.variant.save()

        refund_amount = refund_amount.quantize(Decimal("0.01"))

        order.order_status = "Cancelled"

        if order.payment_method in ["RAZORPAY", "WALLET"] and refund_amount > 0:

            wallet, created = Wallet.objects.get_or_create(user=order.user)

            wallet.balance += refund_amount
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type="CREDIT",
                amount=refund_amount,
                description=f"Refund for cancelled order {order.order_id}",
            )

            order.refund_processed = True

        order.is_cancelled = True

        order.save()

        messages.success(request, "Entire order cancelled successfully.")

        return redirect("order_details", order_id=order.order_id)

    context = {"order": order}

    return render(request, "cancel_entire_order.html", context)


@login_required(login_url="login")
def return_single_item(request, item_id):

    order_item = get_object_or_404(
        OrderItem.objects.select_related("order", "product", "variant"),
        id=item_id,
        order__user=request.user,
        order__order_status="Delivered",
    )

    existing_return = ReturnItem.objects.filter(order_item=order_item).exists()

    if existing_return:

        messages.error(request, "Return request already submitted.")

        return redirect("order_details", order_id=order_item.order.order_id)

    if request.method == "POST":

        refund_method = request.POST.get("refund_method")

        return_reason = request.POST.get("return_reason")

        return_note = request.POST.get("return_note")
        # Proportional refund based on actual paid amount
        all_items_price_sum = sum(
            i.total_price for i in order_item.order.items.all()
        )

        if all_items_price_sum <= 0:

            messages.error(request, "Invalid order total.")

            return redirect("order_details", order_id=order_item.order.order_id)

        refund_amount = (
            order_item.total_price * order_item.order.total_amount
        ) / all_items_price_sum

        refund_amount = refund_amount.quantize(Decimal("0.01"))

        return_request = ReturnRequest.objects.create(
            order=order_item.order,
            user=request.user,
            refund_method=refund_method,
            return_reason=return_reason,
            return_note=return_note,
            refund_amount=refund_amount,
        )

        ReturnItem.objects.create(
            return_request=return_request,
            order_item=order_item,
            quantity=order_item.quantity,
            refund_amount=refund_amount,
        )

        order_item.item_status = "Return Requested"

        order_item.save()

        messages.success(request, "Return request submitted.")

        return redirect("order_details", order_id=order_item.order.order_id)

    context = {"order_item": order_item}

    return render(request, "return_single_item.html", context)


@login_required(login_url="login")
def return_entire_order(request, order_id):

    order = get_object_or_404(
        Order.objects.prefetch_related("items", "items__product", "items__variant"),
        order_id=order_id,
        user=request.user,
        order_status="Delivered",
    )

    if request.method == "POST":

        selected_items = request.POST.getlist("selected_items")
        if not selected_items:

            messages.error(request, "Select at least one item.")

            return redirect("return_entire_order", order_id=order.order_id)

        refund_method = request.POST.get("refund_method")

        return_reason = request.POST.get("return_reason")

        return_note = request.POST.get("return_note")

        items = order.items.filter(id__in=selected_items, item_status="Active")

        # Proportional refund: each item's share of the actual paid total
        all_items_price_sum = sum(i.total_price for i in order.items.all())

        if all_items_price_sum <= 0:

            messages.error(request, "Invalid order total.")

            return redirect("order_details", order_id=order.order_id)

        # Pre-compute per-item refunds
        item_refunds = {}
        total_refund = Decimal("0")
        for item in items:

            item_refund = (
                item.total_price * order.total_amount
            ) / all_items_price_sum

            item_refund = item_refund.quantize(Decimal("0.01"))

            item_refunds[item.id] = item_refund
            total_refund += item_refund

        return_request = ReturnRequest.objects.create(
            order=order,
            user=request.user,
            refund_method=refund_method,
            return_reason=return_reason,
            return_note=return_note,
            refund_amount=total_refund,
        )

        for item in items:

            ReturnItem.objects.create(
                return_request=return_request,
                order_item=item,
                quantity=item.quantity,
                refund_amount=item_refunds[item.id],
            )

            item.item_status = "Return Requested"

            item.save()

        messages.success(request, "Return request submitted.")

        return redirect("order_details", order_id=order.order_id)

    context = {"order": order}

    return render(request, "return_entire_order.html", context)


@login_required(login_url="login")
def invoice_page(request, order_id):

    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items", "items__variant", "items__variant__images", "items__product"
        ),
        order_id=order_id,
        user=request.user,
    )
    active_items = order.items.filter(item_status="Active")

    cancelled_items = order.items.filter(item_status="Cancelled")

    returned_items = order.items.filter(item_status="Returned")
    summary_subtotal = 0

    for item in active_items:

        summary_subtotal += item.price * item.quantity
    summary_total = (
        summary_subtotal
        - order.discount_amount
        + order.shipping_charge
        + order.tax_amount
    )
    context = {
        "order": order,
        "active_items": active_items,
        "cancelled_items": cancelled_items,
        "returned_items": returned_items,
        "summary_subtotal": summary_subtotal,
        "summary_total": summary_total,
    }

    return render(request, "invoice.html", context)


@login_required(login_url="login")
def download_invoice(request, order_id):

    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items", "items__variant", "items__variant__images", "items__product"
        ),
        order_id=order_id,
        user=request.user,
    )
    active_items = order.items.filter(item_status="Active")

    cancelled_items = order.items.filter(item_status="Cancelled")

    returned_items = order.items.filter(item_status="Returned")
    summary_subtotal = 0

    for item in active_items:

        summary_subtotal += item.price * item.quantity

    template = get_template("invoice_pdf.html")

    summary_total = (
        summary_subtotal
        - order.discount_amount
        + order.shipping_charge
        + order.tax_amount
    )

    context = {
        "order": order,
        "active_items": active_items,
        "cancelled_items": cancelled_items,
        "returned_items": returned_items,
        "summary_subtotal": summary_subtotal,
        "summary_total": summary_total,
    }

    html = template.render(context)

    response = HttpResponse(content_type="application/pdf")

    response["Content-Disposition"] = (
        f'attachment; filename="Invoice-{order.order_id}.pdf"'
    )

    pisa.CreatePDF(html, dest=response)

    return response

