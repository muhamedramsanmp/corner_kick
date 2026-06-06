from django.urls import path
from . import views

urlpatterns = [
    path("wallet/",
    views.wallet_page,
    name="wallet_page"),

    path(
    "wallet/add-money/",
    views.add_money,
    name="add_money"
),

path(
    "wallet-success/",
    views.wallet_success,
    name="wallet_success"
),

path(
    "create-wallet-order/",
    views.create_wallet_order,
    name="create_wallet_order"
),

path(
    "wallet-payment-success/",
    views.wallet_payment_success,
    name="wallet_payment_success"
),

path(
    "wallet-failed/",
    views.wallet_failed,
    name="wallet_failed"
),

path(

    "apply-coupon/",

    views.apply_coupon,

    name="apply_coupon"

),
]
