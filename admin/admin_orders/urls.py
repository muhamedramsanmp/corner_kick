from django.urls import path 
from . import views

urlpatterns = [

    path(
        'order-management',
        views.order_management,
        name='order_management'
    ),
    path(
    'order-view/<str:order_id>/',
    views.admin_order_view,
    name='admin_order_view'
    ),

    path(
    'returns/',
    views.return_management,
    name='return_management'
    ),
    
    path(
    'returns/<int:request_id>/',
    views.return_request_details,
    name='return_request_details'
),
]