from django.urls import path

from . import views

urlpatterns = [
    path("category-management/", views.category_management, name="category_management"),
    path("add-category/", views.add_category, name="add_category"),
    path("edit-category/<int:category_id>/", views.edit_category, name="edit_category"),
    path(
        "toggle-category/<int:category_id>/",
        views.toggle_category_status,
        name="toggle_category_status",
    ),
    path(
        "delete-category/<int:category_id>/",
        views.delete_category,
        name="delete_category",
    ),
]
