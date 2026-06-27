from django.urls import path

from . import views

app_name = "user_products"

urlpatterns = [
    path("shop/", views.shop, name="shop"),
    path("product/<slug:slug>/", views.product_details, name="product_details"),
    path("add-to-cart/", views.add_to_cart, name="add_to_cart"),
    path("cart/", views.cart, name="cart"),
    path(
        "remove-cart-item/<int:item_id>/",
        views.remove_cart_item,
        name="remove_cart_item",
    ),
    path(
        "update-cart-quantity/<int:item_id>/",
        views.update_cart_quantity,
        name="update_cart_quantity",
    ),
    path(
        "toggle-wishlist/<int:product_id>/",
        views.toggle_wishlist,
        name="toggle_wishlist",
    ),
    path("wishlist/", views.wishlist_page, name="wishlist"),
    path(
        "wishlist-to-cart/<int:product_id>/",
        views.wishlist_to_cart,
        name="wishlist_to_cart",
    ),
    path(
        "review/add/<int:product_id>/",
        views.add_review,
        name="add_review",
    ),
    path("review/<int:review_id>/delete/", views.delete_review, name="delete_review"),
]
