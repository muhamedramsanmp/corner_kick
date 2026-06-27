from django.urls import path

from . import views

urlpatterns = [
    path("coupons/", views.coupon_management, name="coupon_management"),
    path(
        "coupon/toggle/<int:coupon_id>/",
        views.toggle_coupon_status,
        name="toggle_coupon_status",
    ),
    path("coupon/delete/<int:coupon_id>/", views.delete_coupon, name="delete_coupon"),
    path("coupon/add/", views.add_coupon, name="add_coupon"),
    path("coupon/edit/<int:coupon_id>/", views.edit_coupon, name="edit_coupon"),
]
