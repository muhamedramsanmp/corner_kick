from django.core.paginator import Paginator
from django.shortcuts import render,redirect
from user.decorators import user_required
from django.urls import reverse
from decimal import Decimal
from django.contrib import messages
from .models import Wallet, WalletTransaction
from admin.admin_coupon.models import Coupon,CouponUsage
from user.user_orders.models import Order

@user_required
def wallet_page(request):

    wallet, created = Wallet.objects.get_or_create(

        user=request.user

    )

    transactions = WalletTransaction.objects.filter(

        wallet=wallet

    ).select_related(

        "order"

    ).order_by(

        "-created_at"

    )

    paginator = Paginator(

        transactions,

        6

    )

    page_number = request.GET.get(

        "page"

    )

    page_obj = paginator.get_page(

        page_number

    )

    context = {

        "wallet": wallet,

        "transactions": page_obj,

        "page_obj": page_obj,

    }

    return render(

        request,

        "wallet.html",

        context

    )



@user_required
def add_money(request):

    if request.method != "POST":

        return redirect(
            "wallet_page"
        )

    amount = request.POST.get(
        "amount"
    )

    if not amount:

        messages.error(

            request,

            "Please enter amount"

        )

        return redirect(
            "wallet_page"
        )

    amount = Decimal(amount)

    if amount < 100:

        messages.error(

            request,

            "Minimum amount is ₹100"

        )

        return redirect(
            "wallet_page"
        )

    wallet = Wallet.objects.get(

        user=request.user

    )

    wallet.balance += amount

    wallet.save()

    WalletTransaction.objects.create(

        wallet=wallet,

        transaction_type="CREDIT",

        status="SUCCESS",

        amount=amount,

        description="Wallet Top Up"

    )

    return redirect(

        reverse(
            "wallet_success"
        ) + f"?amount={amount}"

    )


@user_required
def wallet_success(request):

    amount = request.GET.get(
        "amount"
    )

    context = {

        "amount": amount

    }

    return render(

        request,

        "wallet_success.html",

        context

    )

@user_required
def wallet_failed(request):

    amount = request.GET.get(
        "amount"
    )

    context = {

        "amount": amount

    }

    return render(

        request,

        "wallet_failed.html",

        context

    )

import json
import razorpay

from django.http import JsonResponse
from django.conf import settings


from django.views.decorators.http import require_POST

@require_POST
@user_required
def create_wallet_order(request):

    data = json.loads(request.body)

    amount = int(float(data["amount"]) * 100)

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    razorpay_order = client.order.create({

        "amount": amount,

        "currency": "INR"

    })

    return JsonResponse({

        "key": settings.RAZORPAY_KEY_ID,

        "amount": razorpay_order["amount"],

        "order_id": razorpay_order["id"]

    })


@user_required
def wallet_payment_success(request):

    amount = Decimal(
        request.GET.get(
            "amount"
        )
    )

    wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )

    wallet.balance += amount

    wallet.save()

    WalletTransaction.objects.create(

        wallet=wallet,

        transaction_type="CREDIT",

        status="SUCCESS",

        amount=amount,

        description="Wallet Top Up"

    )

    return redirect(

        reverse(
            "wallet_success"
        ) + f"?amount={amount}"

    )

from django.http import JsonResponse
from django.utils import timezone

@user_required
def apply_coupon(request):
    print("APPLY COUPON VIEW HIT")

    if request.method != "POST":

        return JsonResponse({

            "success": False,

            "message": "Invalid request"

        })

    coupon_code = request.POST.get(
        "coupon_code"
    )

    subtotal = Decimal(

        request.POST.get(
            "subtotal",
            "0"
        )

    )
    print("COUPON =", coupon_code)
    print("SUBTOTAL =", subtotal)

    # ==========================
    # COUPON EXISTS
    # ==========================

    try:

        coupon = Coupon.objects.get(

            code__iexact=coupon_code,

            is_deleted=False

        )

    except Coupon.DoesNotExist:

        return JsonResponse({

            "success": False,

            "message": "Coupon does not exist"

        })
    
    # ==========================
    # TOTAL USAGE LIMIT
    # ==========================

    if coupon.total_usage_limit:

        total_used = Order.objects.filter(

            coupon=coupon

        ).count()

        if total_used >= coupon.total_usage_limit:

            return JsonResponse({

                "success": False,

                "message":
                "Coupon usage limit reached"

            })
    # ==========================
    # USER LIMIT
    # ==========================

    if coupon.usage_limit_per_user:

        user_used = Order.objects.filter(

            user=request.user,

            coupon=coupon

        ).count()

        if user_used >= coupon.usage_limit_per_user:

            return JsonResponse({

                "success": False,

                "message":
                "You have already used this coupon"

            })
    # ==========================
    # ACTIVE STATUS
    # ==========================

    if not coupon.is_active:

        return JsonResponse({

            "success": False,

            "message": "Coupon is currently inactive"

        })

    today = timezone.now().date()

    # ==========================
    # START DATE
    # ==========================

    if coupon.start_date:

        if today < coupon.start_date:

            return JsonResponse({

                "success": False,

                "message":
                f"Coupon starts on {coupon.start_date}"

            })

    # ==========================
    # END DATE
    # ==========================

    if coupon.end_date:

        if today > coupon.end_date:

            return JsonResponse({

                "success": False,

                "message":
                "Coupon has expired"

            })

    # ==========================
    # MIN PURCHASE
    # ==========================

    if coupon.min_purchase:

        if subtotal < coupon.min_purchase:

            return JsonResponse({

                "success": False,

                "message":
                f"Minimum purchase ₹{coupon.min_purchase} required"

            })

    # ==========================
    # DISCOUNT
    # ==========================

    discount = 0

    if coupon.discount_type == "PERCENTAGE":

        discount = (

            subtotal *
            Decimal(
                coupon.discount_value
            )

        ) / Decimal("100")

        if coupon.max_discount:

            discount = min(

                discount,

                coupon.max_discount

            )

    else:

        discount = Decimal(
            coupon.discount_value
        )

    # ==========================
    # PREVENT NEGATIVE TOTAL
    # ==========================

    if discount > subtotal:

        discount = subtotal

    total = subtotal - discount

    # ==========================
    # SUCCESS
    # ==========================

    return JsonResponse({

        "success": True,

        "message":
        f"{coupon.code} applied successfully",

        "coupon": coupon.code,

        "discount": round(discount, 2),

        "total": round(total, 2)

    })