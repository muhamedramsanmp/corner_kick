from django.urls import path
from . import views

app_name = "addressinfo"

urlpatterns = [
    path('', views.address_view, name='address_view'),
    path('add-address/', views.add_address, name='add_address'),
    path('edit-address/<int:id>/', views.edit_address, name='edit_address'),
    path('delete-address/<int:id>/', views.delete_address, name='delete_address'),
]