from django.urls import path
from . import views

urlpatterns = [
    path("order-management", views.order_management, name="order_management"),
    path("order-view/<str:order_id>/", views.admin_order_view, name="admin_order_view"),
    path("returns/", views.return_management, name="return_management"),
    path(
        "returns/<int:request_id>/",
        views.return_request_details,
        name="return_request_details",
    ),
    path("invoice/<str:order_id>/", views.generate_invoice, name="generate_invoice"),

   path(
    "reviews/",
    views.review_management,
    name="review_management"
),

path(
    "reviews/<int:review_id>/approve/",
    views.approve_review,
    name="approve_review"
),

path(
    "reviews/<int:review_id>/reject/",
    views.reject_review,
    name="reject_review"
),
]
