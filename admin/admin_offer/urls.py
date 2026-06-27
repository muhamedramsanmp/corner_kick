from django.urls import path

from . import views

app_name = "admin_offer"
urlpatterns = [
    path("offers/", views.offer_management, name="offer_management"),
    path("offers/add/", views.add_offer, name="add_offer"),
    path("offers/edit/<int:offer_id>/", views.edit_offer, name="edit_offer"),
    path("offers/delete/<int:offer_id>/", views.delete_offer, name="delete_offer"),
]
