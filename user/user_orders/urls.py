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

]