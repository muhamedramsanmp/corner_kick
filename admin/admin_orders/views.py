from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Sum
from user.user_orders.models import Order
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from user.user_orders.models import ReturnRequest, ReturnItem
from admin.decorators import admin_required
from user.user_wallet.models import Wallet, WalletTransaction
from user.accounts.utils import credit_referral_reward
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from user.products.models import Review

@admin_required
def order_management(request):

    query = request.GET.get("q", "")
    status = request.GET.get("status", "")

    orders = (
        Order.objects.select_related("user")
        .prefetch_related("items")
        .order_by("-created_at")
    )

    if query:

        orders = orders.filter(order_id__icontains=query)

    if status:

        orders = orders.filter(order_status=status)

    paginator = Paginator(orders, 8)

    page_number = request.GET.get("page")

    orders = paginator.get_page(page_number)

    total_orders = Order.objects.count()

    pending_orders = Order.objects.filter(order_status="Pending").count()

    delivered_orders = Order.objects.filter(order_status="Delivered").count()

    cancelled_orders = Order.objects.filter(order_status="Cancelled").count()

    total_revenue = (
        Order.objects.filter(payment_status="Paid").aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    context = {
        "orders": orders,
        "query": query,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "delivered_orders": delivered_orders,
        "cancelled_orders": cancelled_orders,
        "total_revenue": total_revenue,
        "status": status,
    }

    return render(request, "order_management.html", context)


def admin_order_view(request, order_id):

    order = get_object_or_404(
        Order.objects.select_related("user", "address").prefetch_related(
            "items", "items__product", "items__variant"
        ),
        order_id=order_id,
    )

    if request.method == "POST":

        new_status = request.POST.get("order_status")

        admin_note = request.POST.get("admin_note")

        allowed_statuses = order.allowed_next_statuses()

        if new_status not in allowed_statuses:

            messages.error(request, "Invalid status transition.")

            return redirect("admin_order_view", order_id=order.order_id)

        order.order_status = new_status

        order.admin_note = admin_note
        order.status_message = f"Your order status changed to {new_status}."

        order.show_status_message = True

        if new_status == "Delivered":

            order.delivered_at = timezone.now()

            order.payment_status = "Paid"

            credit_referral_reward(request, order.user, order)

        order.save()
        if new_status == "Cancelled":

            order.is_cancelled = True

            for item in order.items.filter(item_status="Active"):

                item.item_status = "Cancelled"

                item.variant.stock += item.quantity

                item.variant.save()

                item.save()

        messages.success(request, f"Order status updated to {new_status}.")

        return redirect("admin_order_view", order_id=order.order_id)
    summary_subtotal = 0
    summary_offer_discount = 0

    for item in order.items.filter(item_status="Active"):

        summary_subtotal += item.original_price * item.quantity

        summary_offer_discount += item.offer_discount * item.quantity

    summary_total = (
        summary_subtotal
        - summary_offer_discount
        - order.discount_amount
        + order.shipping_charge
        + order.tax_amount
    )
    active_items = order.items.filter(item_status="Active")

    cancelled_items = order.items.filter(item_status="Cancelled")

    cancelled_items = order.items.filter(item_status="Cancelled")
    context = {
        "order": order,
        "allowed_statuses": order.allowed_next_statuses(),
        "summary_subtotal": summary_subtotal,
        "summary_offer_discount": summary_offer_discount,
        "summary_total": summary_total,
        "active_items": active_items,
        "cancelled_items": cancelled_items,
    }

    return render(request, "admin_order_view.html", context)


from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


@admin_required
def generate_invoice(request, order_id):

    order = get_object_or_404(Order, order_id=order_id)

    response = HttpResponse(content_type="application/pdf")

    response["Content-Disposition"] = (
        f"attachment; " f'filename="invoice_{order.order_id}.pdf"'
    )

    p = canvas.Canvas(response)

    y = 800

    p.setFont("Helvetica-Bold", 18)

    p.drawString(50, y, "INVOICE")

    y -= 40

    p.setFont("Helvetica", 12)

    p.drawString(50, y, f"Order ID : {order.order_id}")

    y -= 20

    p.drawString(50, y, f"Date : {order.created_at.strftime('%d-%m-%Y')}")

    y -= 20

    p.drawString(50, y, f"Customer : {order.user.get_full_name()}")

    y -= 40

    p.setFont("Helvetica-Bold", 12)

    p.drawString(50, y, "Product")

    p.drawString(250, y, "Qty")

    p.drawString(320, y, "Price")

    p.drawString(420, y, "Total")

    y -= 25

    p.line(50, y, 550, y)

    y -= 20

    p.setFont("Helvetica", 11)

    for item in order.items.all():

        p.drawString(50, y, item.product.product_name)

        p.drawString(250, y, str(item.quantity))

        p.drawString(320, y, f"₹{item.price}")

        p.drawString(420, y, f"₹{item.total_price}")

        y -= 25

    y -= 20

    p.line(50, y, 550, y)

    y -= 30

    p.drawString(320, y, "Subtotal")

    p.drawString(420, y, f"₹{order.subtotal}")

    y -= 20

    p.drawString(320, y, "Offer Discount")

    p.drawString(420, y, f"-₹{order.offer_discount}")

    y -= 20

    p.drawString(320, y, "Coupon Discount")

    p.drawString(420, y, f"-₹{order.discount_amount}")

    y -= 20

    p.drawString(320, y, "Shipping")

    p.drawString(420, y, f"₹{order.shipping_charge}")

    y -= 30

    p.setFont("Helvetica-Bold", 13)

    p.drawString(320, y, "Grand Total")

    p.drawString(420, y, f"₹{order.total_amount}")

    p.showPage()
    p.save()

    return response


@admin_required
def return_management(request):

    search = request.GET.get("search", "")

    returns = (
        ReturnRequest.objects.all()
        .select_related("user", "order")
        .prefetch_related("items", "items__order_item", "items__order_item__product")
        .order_by("-created_at")
    )
    status = request.GET.get("status", "")
    if status:

        returns = returns.filter(return_status=status)

    if search:

        returns = returns.filter(
            Q(order__order_id__icontains=search)
            | Q(user__username__icontains=search)
            | Q(user__email__icontains=search)
        )

    total_returns = ReturnRequest.objects.count()

    pending_returns = ReturnRequest.objects.filter(return_status="requested").count()

    approved_returns = ReturnRequest.objects.filter(return_status="approved").count()

    rejected_returns = ReturnRequest.objects.filter(return_status="rejected").count()

    paginator = Paginator(returns, 8)

    page_number = request.GET.get("page")

    returns = paginator.get_page(page_number)

    context = {
        "returns": returns,
        "search": search,
        "total_returns": total_returns,
        "pending_returns": pending_returns,
        "approved_returns": approved_returns,
        "rejected_returns": rejected_returns,
        "status": status,
    }

    return render(request, "return_management.html", context)


def return_request_details(request, request_id):

    return_request = get_object_or_404(
        ReturnRequest.objects.select_related("user", "order").prefetch_related(
            "items",
            "items__order_item",
            "items__order_item__product",
            "items__order_item__variant",
            "items__order_item__variant__images",
        ),
        id=request_id,
    )

    if request.method == "POST":

        if return_request.return_status != "requested":

            messages.error(request, "This return request already processed.")

            return redirect("return_request_details", request_id=return_request.id)

        action = request.POST.get("action")

        if action == "approve":
            if return_request.processed_at:

                messages.error(request, "Return already processed.")

                return redirect("return_management")

            return_request.return_status = "approved"

            return_request.save()

            order = return_request.order

            order.status_message = "Your return request has been approved."

            order.show_status_message = True

            order.save()

            # WALLET REFUND

            if (
                return_request.refund_method == "Store Wallet"
                and return_request.return_status == "approved"
            ):

                wallet, created = Wallet.objects.get_or_create(user=return_request.user)

                wallet.balance += return_request.refund_amount

                wallet.save()

                WalletTransaction.objects.create(
                    wallet=wallet,
                    order=order,
                    transaction_type="CREDIT",
                    status="SUCCESS",
                    amount=return_request.refund_amount,
                    description=(
                        f"Return refund credited " f"for order {order.order_id}"
                    ),
                )

            # UPDATE ITEMS

            for item in return_request.items.all():

                order_item = item.order_item

                # ITEM STATUS

                order_item.item_status = "Returned"

                order_item.save()

                # RESTORE STOCK

                variant = order_item.variant

                variant.stock += item.quantity

                variant.save()

            messages.success(request, "Return request approved successfully.")

        elif action == "reject":

            return_request.return_status = "rejected"

            return_request.save()

            order = return_request.order

            order.status_message = "Your return request has been rejected."

            order.show_status_message = True

            order.save()

            messages.error(request, "Return request rejected.")

        return redirect("return_management")

    context = {"return_request": return_request}

    return render(request, "return_request_details.html", context)

from django.db.models import Avg, Q

from django.core.paginator import Paginator

def review_management(request):

    reviews = Review.objects.select_related(
        "user",
        "product"
    ).order_by("-created_at")

    query = request.GET.get("q", "").strip()

    if query:
        reviews = reviews.filter(
            Q(user__username__icontains=query) |
            Q(product__product_name__icontains=query) |
            Q(review_text__icontains=query)
        )

    paginator = Paginator(reviews, 5)  # 10 reviews per page

    page_number = request.GET.get("page")

    reviews = paginator.get_page(page_number)

    total_reviews = Review.objects.count()

    pending_reviews = Review.objects.filter(
        status="pending"
    ).count()

    rejected_reviews = Review.objects.filter(
        status="rejected"
    ).count()

    average_rating = round(
        Review.objects.aggregate(
            avg=Avg("rating")
        )["avg"] or 0,
        1
    )

    context = {
        "reviews": reviews,
        "query": query,
        "total_reviews": total_reviews,
        "pending_reviews": pending_reviews,
        "rejected_reviews": rejected_reviews,
        "average_rating": average_rating,
    }

    return render(
        request,
        "review_management.html",
        context
    )


def approve_review(request, review_id):

    review = get_object_or_404(
        Review,
        id=review_id
    )

    review.status = "approved"


    review.review_message = "Your review has been approved."
    review.show_message = True

    review.save()

    messages.success(
        request,
        "Review approved successfully."
    )

    return redirect(
        "review_management"
    )



def reject_review(request, review_id):

    review = get_object_or_404(
        Review,
        id=review_id
    )

    review.status = "rejected"

    review.review_message = "Your review has been rejected."
    review.show_message = True
    
    review.save()

    messages.success(
        request,
        "Review rejected successfully."
    )

    return redirect(
        "review_management"
    )


