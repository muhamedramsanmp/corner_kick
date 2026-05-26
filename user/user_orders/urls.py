from django.urls import path
from . import views

urlpatterns = [

    path(
        'checkout/',
        views.checkout_page,
        name='checkout_page'
    ),

    path(
    'success/<str:order_id>/',
    views.order_success,
    name='order_success'
),

    path(
        'my-orders/',
        views.my_orders,
        name='my_orders'
),

    path(
    'details/<str:order_id>/',
    views.order_details,
    name='order_details'
),

  path(
    'cancel-item/<int:item_id>/',
    views.cancel_order_item,
    name='cancel_order_item'
),

path(
    'cancel-order/<str:order_id>/',
    views.cancel_entire_order,
    name='cancel_entire_order'
),

path(
    'return-item/<int:item_id>/',
    views.return_single_item,
    name='return_single_item'
),

path(
    'return-order/<str:order_id>/',
    views.return_entire_order,
    name='return_entire_order'
),


path(
    'invoice/<str:order_id>/',
    views.invoice_page,
    name='invoice_page'
),

path(
    'invoice/download/<str:order_id>/',
    views.download_invoice,
    name='download_invoice'
),

]