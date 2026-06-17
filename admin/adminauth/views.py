from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.cache import never_cache
from django.contrib.auth import logout
from admin.decorators import admin_required
from django.db.models.functions import TruncMonth
from django.db.models import Sum
from django.db.models import Count
from datetime import timedelta
from user.user_orders.models import (
    Order,
    OrderItem,
    ReturnRequest,
    ReturnItem,
)
from admin.admin_products.models import Product, Variant
from admin.admin_category.models import Category
from openpyxl import Workbook
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

from reportlab.lib import colors
from io import BytesIO

User = get_user_model()


@never_cache
def admin_login(request):

    if request.user.is_authenticated:

        if request.user.is_staff:

            return redirect("admin_dashboard")

        return redirect("home")

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.is_staff or user.is_superuser:
                login(request, user)
                return redirect("admin_dashboard")
            else:
                messages.error(request, "You are not authorized as admin.")
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "admin_login.html")


from django.db.models import Sum
from django.contrib.auth import get_user_model

User = get_user_model()


@never_cache
@admin_required
def admin_dashboard(request):
    import json
    from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear

    total_revenue = Order.objects.filter(payment_status="Paid").aggregate(total=Sum("total_amount"))["total"] or 0
    total_orders = Order.objects.count()
    active_users = User.objects.filter(is_active=True, is_superuser=False).count()
    pending_orders = Order.objects.filter(order_status="Pending").count()

    # ── Chart filter ───────────────────────────────────────────────────────────
    chart_filter = request.GET.get("chart_filter", "monthly")
    today = timezone.now()

    if chart_filter == "daily":
        start = today - timedelta(days=29)
        orders_qs = Order.objects.filter(payment_status="Paid", created_at__gte=start)
        trunc_fn = TruncDay("created_at")
        label_fmt = "%d %b"
    elif chart_filter == "weekly":
        start = today - timedelta(weeks=11)
        orders_qs = Order.objects.filter(payment_status="Paid", created_at__gte=start)
        trunc_fn = TruncWeek("created_at")
        label_fmt = "%d %b"
    elif chart_filter == "yearly":
        orders_qs = Order.objects.filter(payment_status="Paid")
        trunc_fn = TruncYear("created_at")
        label_fmt = "%Y"
    else:  # monthly (default)
        orders_qs = Order.objects.filter(payment_status="Paid")
        trunc_fn = TruncMonth("created_at")
        label_fmt = "%b %Y"

    chart_data = (
        orders_qs.annotate(period=trunc_fn)
        .values("period")
        .annotate(revenue=Sum("total_amount"))
        .order_by("period")
    )
    chart_labels = []
    chart_revenue = []
    for row in chart_data:
        chart_labels.append(row["period"].strftime(label_fmt))
        chart_revenue.append(float(row["revenue"]))

    # ── Top 10 Best-Selling Products ──────────────────────────────────────────
    top_products = (
        OrderItem.objects.values(
            "product__id",
            "product__product_name",
        )
        .annotate(
            total_qty=Sum("quantity"),
            total_revenue=Sum("total_price"),
        )
        .order_by("-total_qty")[:10]
    )
    # Attach primary image for each top product
    from admin.admin_products.models import Variant as V
    top_products_display = []
    for i, p in enumerate(top_products):
        variant = (
            V.objects.filter(product_id=p["product__id"], is_deleted=False)
            .select_related()
            .first()
        )
        top_products_display.append({
            "rank": i + 1,
            "name": p["product__product_name"],
            "total_qty": p["total_qty"],
            "total_revenue": p["total_revenue"],
            "image": variant.primary_image if variant else None,
        })

    # ── Top 10 Best-Selling Categories ───────────────────────────────────────
    top_categories = (
        OrderItem.objects.values(
            "product__category__id",
            "product__category__category_name",
        )
        .annotate(
            total_qty=Sum("quantity"),
            total_revenue=Sum("total_price"),
        )
        .order_by("-total_qty")[:10]
    )
    top_categories_display = []
    for i, c in enumerate(top_categories):
        cat = Category.objects.filter(id=c["product__category__id"]).first()
        top_categories_display.append({
            "rank": i + 1,
            "name": c["product__category__category_name"],
            "total_qty": c["total_qty"],
            "total_revenue": c["total_revenue"],
            "image": cat.category_img.url if cat and cat.category_img else None,
        })

    # ── Top 10 Best-Selling Brands (using category as brand proxy) ────────────
    # Since no separate brand model exists, we group by product name prefix word
    # (i.e. brand = first word of product_name, e.g. "Nike Air" → "Nike")
    from django.db.models import CharField
    from django.db.models.functions import Substr, StrIndex, Coalesce
    top_brands_raw = (
        OrderItem.objects.values("product__category__category_name")
        .annotate(
            total_qty=Sum("quantity"),
            total_revenue=Sum("total_price"),
        )
        .order_by("-total_qty")[:10]
    )
    top_brands_display = []
    for i, b in enumerate(top_brands_raw):
        top_brands_display.append({
            "rank": i + 1,
            "name": b["product__category__category_name"],
            "total_qty": b["total_qty"],
            "total_revenue": b["total_revenue"],
        })

    context = {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "active_users": active_users,
        "pending_orders": pending_orders,
        # chart
        "chart_labels": json.dumps(chart_labels),
        "chart_revenue": json.dumps(chart_revenue),
        "chart_filter": chart_filter,
        # top lists
        "top_products": top_products_display,
        "top_categories": top_categories_display,
        "top_brands": top_brands_display,
    }

    return render(request, "admin_dashboard.html", context)


@never_cache
@admin_required
def sales_report(request):
    today = timezone.now().date()

    period = request.GET.get("period")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    orders = Order.objects.all()

    # Period filter
    if period == "daily":

        orders = orders.filter(created_at__date=today)

    elif period == "weekly":

        orders = orders.filter(created_at__date__gte=today - timedelta(days=6))

    elif period == "monthly":

        orders = orders.filter(
            created_at__year=today.year, created_at__month=today.month
        )

    elif period == "yearly":

        orders = orders.filter(created_at__year=today.year)

    # Custom date range
    if start_date and end_date:

        orders = orders.filter(created_at__date__range=[start_date, end_date])

    total_orders = orders.count()

    offer_discounts = orders.aggregate(total=Sum("offer_discount"))["total"] or 0

    coupon_discounts = orders.aggregate(total=Sum("discount_amount"))["total"] or 0

    total_discounts = offer_discounts + coupon_discounts

    cancelled_amount = (
        orders.filter(order_status="Cancelled").aggregate(total=Sum("total_amount"))[
            "total"
        ]
        or 0
    )

    returns = ReturnRequest.objects.all()

    if period == "daily":

        returns = returns.filter(created_at__date=today)

    elif period == "weekly":

        returns = returns.filter(created_at__date__gte=today - timedelta(days=6))

    elif period == "monthly":

        returns = returns.filter(
            created_at__year=today.year, created_at__month=today.month
        )

    elif period == "yearly":

        returns = returns.filter(created_at__year=today.year)

    if start_date and end_date:

        returns = returns.filter(created_at__date__range=[start_date, end_date])

    total_revenue = orders.aggregate(total=Sum("total_amount"))["total"] or 0

    returned_amount = (
        returns.filter(return_status="approved").aggregate(total=Sum("refund_amount"))[
            "total"
        ]
        or 0
    )

    net_revenue = total_revenue - cancelled_amount - returned_amount
    today = timezone.now().date()

    week_labels = []
    week_revenue = []

    for i in range(6, -1, -1):

        day = today - timedelta(days=i)

        sales = (
            Order.objects.filter(created_at__date=day)
            .exclude(order_status="Cancelled")
            .aggregate(total=Sum("total_amount"))["total"]
            or 0
        )

        cancelled = (
            Order.objects.filter(
                order_status="Cancelled", updated_at__date=day
            ).aggregate(total=Sum("total_amount"))["total"]
            or 0
        )

        returned = (
            ReturnRequest.objects.filter(
                return_status="approved", updated_at__date=day
            ).aggregate(total=Sum("refund_amount"))["total"]
            or 0
        )

        graph_revenue = sales - cancelled - returned

        week_labels.append(day.strftime("%a"))

        week_revenue.append(float(graph_revenue))
    recent_transactions = (
        orders.select_related("user")
        .prefetch_related("items__product")
        .order_by("-created_at")[:5]
    )

    import json

    context = {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "net_revenue": net_revenue,
        "total_discounts": total_discounts,
        "offer_discounts": offer_discounts,
        "coupon_discounts": coupon_discounts,
        "cancelled_amount": cancelled_amount,
        "returned_amount": returned_amount,
        "recent_transactions": recent_transactions,
        "week_labels": json.dumps(week_labels),
        "week_revenue": json.dumps(week_revenue),
    }
    return render(request, "sales_report.html", context)


@admin_required
def export_sales_excel(request):

    orders = Order.objects.all()

    period = request.GET.get("period")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    today = timezone.now().date()

    if period == "daily":

        orders = orders.filter(created_at__date=today)

    elif period == "weekly":

        orders = orders.filter(created_at__date__gte=today - timedelta(days=6))

    elif period == "monthly":

        orders = orders.filter(
            created_at__year=today.year, created_at__month=today.month
        )

    elif period == "yearly":

        orders = orders.filter(created_at__year=today.year)

    if start_date and end_date:

        orders = orders.filter(created_at__date__range=[start_date, end_date])

    workbook = Workbook()

    worksheet = workbook.active

    worksheet.title = "Sales Report"

    worksheet.append(
        ["Order ID", "Customer", "Amount", "Status", "Payment Method", "Date"]
    )

    for order in orders:

        worksheet.append(
            [
                order.order_id,
                order.user.username,
                float(order.total_amount),
                order.order_status,
                order.payment_method,
                order.created_at.strftime("%d-%m-%Y"),
            ]
        )

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response["Content-Disposition"] = 'attachment; filename="sales_report.xlsx"'

    workbook.save(response)

    return response


@admin_required
def export_sales_pdf(request):

    orders = Order.objects.all()

    period = request.GET.get("period")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    today = timezone.now().date()

    if period == "daily":

        orders = orders.filter(created_at__date=today)

    elif period == "weekly":

        orders = orders.filter(created_at__date__gte=today - timedelta(days=6))

    elif period == "monthly":

        orders = orders.filter(
            created_at__year=today.year, created_at__month=today.month
        )

    elif period == "yearly":

        orders = orders.filter(created_at__year=today.year)

    if start_date and end_date:

        orders = orders.filter(created_at__date__range=[start_date, end_date])

    buffer = BytesIO()

    pdf = SimpleDocTemplate(buffer)

    data = [["Order ID", "Customer", "Amount", "Status"]]

    for order in orders:

        data.append(
            [
                order.order_id,
                order.user.username,
                f"₹{order.total_amount}",
                order.order_status,
            ]
        )

    table = Table(data)

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )

    pdf.build([table])

    pdf_data = buffer.getvalue()

    buffer.close()

    response = HttpResponse(pdf_data, content_type="application/pdf")

    response["Content-Disposition"] = 'attachment; filename="sales_report.pdf"'

    return response


@never_cache
def admin_logout(request):
    logout(request)  # ✅ clears session
    messages.success(request, "You have been logged out successfully")
    return redirect("admin_login")


@admin_required
def user_management(request):

    query = request.GET.get("q", "").strip()

    status = request.GET.get("status", "")

    users_list = User.objects.filter(is_staff=False).order_by("-id")

    # 🔥 IMPROVED SEARCH (multi-field + startswith behavior)
    if query:
        users_list = users_list.filter(
            Q(username__istartswith=query)
            | Q(email__istartswith=query)
            | Q(first_name__istartswith=query)
            | Q(last_name__istartswith=query)
        )
    if status == "active":

        users_list = users_list.filter(is_active=True)

    elif status == "blocked":

        users_list = users_list.filter(is_active=False)

    paginator = Paginator(users_list, 5)
    page_number = request.GET.get("page")
    users = paginator.get_page(page_number)

    # stats based on filtered result
    total_users = users_list.count()
    active_users = users_list.filter(is_active=True).count()
    banned_users = users_list.filter(is_active=False).count()

    today = timezone.localdate()
    new_today = users_list.filter(date_joined__date=today).count()

    return render(
        request,
        "user_management.html",
        {
            "users": users,
            "query": query,  # 🔥 IMPORTANT (to keep value in search box)
            "total_users": total_users,
            "active_users": active_users,
            "banned_users": banned_users,
            "new_today": new_today,
            "status": status,
        },
    )


def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if user.is_staff:
        messages.error(request, "Cannot modify admin user.")
        return redirect("user_management")

    user.is_active = not user.is_active
    user.save()

    # 👇 Better message (with user info)
    name = f"{user.first_name} {user.last_name}".strip() or user.email

    if user.is_active:
        messages.success(request, f"{name} has been activated")
    else:
        messages.error(request, f"{name} has been blocked")

    return redirect("user_management")
