from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Sum
from user.user_orders.models import Order
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from user.user_orders.models import ReturnRequest,ReturnItem




def order_management(request):

    # =====================================
    # GET SEARCH
    # =====================================

    query = request.GET.get(
        'q',
        ''
    )

    # =====================================
    # BASE QUERYSET
    # =====================================

    orders = Order.objects.select_related(
        'user'
    ).prefetch_related(
        'items'
    ).order_by(
        '-created_at'
    )

    # =====================================
    # SEARCH FILTER
    # =====================================

    if query:

        orders = orders.filter(
            order_id__icontains=query
        )

    # =====================================
    # PAGINATION
    # =====================================

    paginator = Paginator(
        orders,
        5
    )

    page_number = request.GET.get(
        'page'
    )

    orders = paginator.get_page(
        page_number
    )

    # =====================================
    # STATISTICS
    # =====================================

    total_orders = Order.objects.count()

    pending_orders = Order.objects.filter(
        order_status='Pending'
    ).count()

    delivered_orders = Order.objects.filter(
        order_status='Delivered'
    ).count()

    cancelled_orders = Order.objects.filter(
        order_status='Cancelled'
    ).count()

    total_revenue = Order.objects.filter(
        payment_status='Paid'
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    # =====================================
    # CONTEXT
    # =====================================

    context = {

        'orders': orders,

        'query': query,

        'total_orders': total_orders,

        'pending_orders': pending_orders,

        'delivered_orders': delivered_orders,

        'cancelled_orders': cancelled_orders,

        'total_revenue': total_revenue,

    }

    return render(

        request,

        'order_management.html',

        context

    )


def admin_order_view(request, order_id):

    order = get_object_or_404(

        Order.objects.select_related(
            'user',
            'address'
        ).prefetch_related(
            'items',
            'items__product',
            'items__variant'
        ),

        order_id=order_id

    )

    # =====================================
    # STATUS UPDATE
    # =====================================

    if request.method == 'POST':

        new_status = request.POST.get(
            'order_status'
        )

        admin_note = request.POST.get(
            'admin_note'
        )

        allowed_statuses = order.allowed_next_statuses()

        # =================================
        # INVALID STATUS MOVEMENT
        # =================================

        if new_status not in allowed_statuses:

            messages.error(

                request,

                'Invalid status transition.'

            )

            return redirect(

                'admin_order_view',

                order_id=order.order_id

            )
        # =================================
        # UPDATE STATUS
        # =================================

        order.order_status = new_status

        order.admin_note = admin_note
        order.status_message = (

            f'Your order status changed to {new_status}.'

        )

        order.show_status_message = True


        # =================================
        # DELIVERY TIME
        # =================================

        if new_status == 'Delivered':

            order.delivered_at = timezone.now()

            order.payment_status = 'Paid'

        # =================================
        # CANCEL
        # =================================

        if new_status == 'Cancelled':

            order.is_cancelled = True

            # RESTORE STOCK

            for item in order.items.all():

                item.variant.stock += item.quantity

                item.variant.save()

        order.save()

        messages.success(

            request,

            f'Order status updated to {new_status}.'

        )

        return redirect(

            'admin_order_view',

            order_id=order.order_id

        )

    context = {

        'order': order,

        'allowed_statuses': order.allowed_next_statuses()

    }

    return render(

        request,

        'admin_order_view.html',

        context

    )






# =========================================================
# RETURN MANAGEMENT
# =========================================================

def return_management(request):

    # =====================================
    # SEARCH
    # =====================================

    search = request.GET.get(
        'search',
        ''
    )

    # =====================================
    # ONLY REQUESTED RETURNS
    # =====================================

    returns = ReturnRequest.objects.filter(

        return_status='requested'

    ).select_related(

        'user',
        'order'

    ).prefetch_related(

        'items',
        'items__order_item',
        'items__order_item__product'

    ).order_by(

        '-created_at'

    )

    # =====================================
    # SEARCH FILTER
    # =====================================

    if search:

        returns = returns.filter(

            Q(order__order_id__icontains=search) |

            Q(user__username__icontains=search) |

            Q(user__email__icontains=search)

        )

    # =====================================
    # STATISTICS
    # =====================================

    total_returns = ReturnRequest.objects.count()

    pending_returns = ReturnRequest.objects.filter(
        return_status='requested'
    ).count()

    approved_returns = ReturnRequest.objects.filter(
        return_status='approved'
    ).count()

    rejected_returns = ReturnRequest.objects.filter(
        return_status='rejected'
    ).count()

    # =====================================
    # PAGINATION
    # =====================================

    paginator = Paginator(
        returns,
        8
    )

    page_number = request.GET.get(
        'page'
    )

    returns = paginator.get_page(
        page_number
    )

    context = {

        'returns': returns,

        'search': search,

        'total_returns': total_returns,

        'pending_returns': pending_returns,

        'approved_returns': approved_returns,

        'rejected_returns': rejected_returns,

    }

    return render(

        request,

        'return_management.html',

        context

    )


# =========================================================
# RETURN REQUEST DETAILS
# =========================================================

def return_request_details(request, request_id):

    return_request = get_object_or_404(

        ReturnRequest.objects.select_related(

            'user',
            'order'

        ).prefetch_related(

            'items',
            'items__order_item',
            'items__order_item__product',
            'items__order_item__variant',
            'items__order_item__variant__images'

        ),

        id=request_id

    )

    # =====================================
    # POST ACTIONS
    # =====================================

    if request.method == 'POST':

        # =================================
        # ALREADY PROCESSED CHECK
        # =================================

        if return_request.return_status != 'requested':

            messages.error(

                request,

                'This return request already processed.'

            )

            return redirect(

                'return_request_details',

                request_id=return_request.id

            )

        action = request.POST.get(
            'action'
        )

        # =================================
        # APPROVE RETURN
        # =================================

        if action == 'approve':

            # UPDATE RETURN STATUS

            return_request.return_status = (
                'approved'
            )

            return_request.save()
            # =================================
            # USER TOAST MESSAGE
            # =================================

            order = return_request.order

            order.status_message = (
                'Your return request has been approved.'
            )

            order.show_status_message = True

            order.save()

            # UPDATE ITEMS

            for item in return_request.items.all():

                order_item = item.order_item

                # ITEM STATUS

                order_item.item_status = (
                    'Returned'
                )

                order_item.save()

                # RESTORE STOCK

                variant = order_item.variant

                variant.stock += item.quantity

                variant.save()

            messages.success(

                request,

                'Return request approved successfully.'

            )

        # =================================
        # REJECT RETURN
        # =================================

        elif action == 'reject':

            return_request.return_status = (
                'rejected'
            )

            return_request.save()

            order = return_request.order

            order.status_message = (
                'Your return request has been rejected.'
            )

            order.show_status_message = True

            order.save()

            messages.error(

                request,

                'Return request rejected.'

            )

        return redirect(

            'return_management'

        )

    context = {

        'return_request': return_request

    }

    return render(

        request,

        'return_request_details.html',

        context

    )


