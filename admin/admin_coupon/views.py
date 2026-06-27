from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from admin.decorators import admin_required

from .models import Coupon


@admin_required
def coupon_management(request):

    search = request.GET.get("search", "")

    coupons = Coupon.objects.filter(is_deleted=False).order_by("-id")

    today = timezone.now().date()

    total_coupons = Coupon.objects.filter(is_deleted=False).count()

    active_coupons = Coupon.objects.filter(
        is_deleted=False, is_active=True, end_date__gte=today
    ).count()

    expired_coupons = Coupon.objects.filter(
        is_deleted=False, end_date__lt=today
    ).count()

    if search:

        coupons = coupons.filter(Q(code__icontains=search))

    paginator = Paginator(coupons, 10)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search": search,
        "total_coupons": total_coupons,
        "active_coupons": active_coupons,
        "expired_coupons": expired_coupons,
    }

    return render(request, "coupon_management.html", context)


@admin_required
def toggle_coupon_status(request, coupon_id):

    coupon = get_object_or_404(Coupon, id=coupon_id, is_deleted=False)

    coupon.is_active = not coupon.is_active

    coupon.save()

    messages.success(request, "Coupon status updated successfully.")

    return redirect("coupon_management")


@admin_required
def delete_coupon(request, coupon_id):

    if request.method == "POST":

        coupon = get_object_or_404(Coupon, id=coupon_id)

        coupon.delete()

        messages.success(request, "Coupon deleted successfully.")

    return redirect("coupon_management")


@admin_required
def add_coupon(request):

    if request.method == "POST":

        try:

            coupon = Coupon(
                code=request.POST.get("code"),
                discount_type=request.POST.get("discount_type"),
                discount_value=Decimal(request.POST.get("discount_value")),
                min_purchase=Decimal(request.POST.get("min_purchase")),
                max_discount=(
                    Decimal(request.POST.get("max_discount"))
                    if request.POST.get("max_discount")
                    else None
                ),
                usage_limit_per_user=int(request.POST.get("usage_limit_per_user")),
                total_usage_limit=int(request.POST.get("total_usage_limit")),
                start_date=request.POST.get("start_date"),
                end_date=request.POST.get("end_date"),
                is_active=("is_active" in request.POST),
            )

            coupon.save()

            messages.success(request, "Coupon created successfully.")

            return redirect("coupon_management")

        except ValidationError as e:

            for field, errors in e.message_dict.items():

                for error in errors:

                    messages.error(request, error)

        except Exception as e:

            messages.error(request, str(e))

    return render(request, "add_coupon.html")


@admin_required
def edit_coupon(request, coupon_id):

    coupon = get_object_or_404(Coupon, id=coupon_id, is_deleted=False)

    if request.method == "POST":

        try:

            coupon.code = request.POST.get("code")

            coupon.discount_type = request.POST.get("discount_type")

            coupon.discount_value = Decimal(request.POST.get("discount_value"))

            coupon.min_purchase = Decimal(request.POST.get("min_purchase"))

            coupon.max_discount = (
                Decimal(request.POST.get("max_discount"))
                if request.POST.get("max_discount")
                else None
            )

            coupon.usage_limit_per_user = int(request.POST.get("usage_limit_per_user"))

            coupon.total_usage_limit = int(request.POST.get("total_usage_limit"))

            coupon.start_date = request.POST.get("start_date")

            coupon.end_date = request.POST.get("end_date")

            coupon.is_active = "is_active" in request.POST

            coupon.save()

            messages.success(request, "Coupon updated successfully.")

            return redirect("coupon_management")

        except ValidationError as e:

            for field, errors in e.message_dict.items():

                for error in errors:

                    messages.error(request, error)

        except Exception as e:

            messages.error(request, str(e))

    return render(request, "edit_coupon.html", {"coupon": coupon})
