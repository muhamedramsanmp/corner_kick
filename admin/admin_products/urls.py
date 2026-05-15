from django.urls import path 
from . import views 

app_name = "admin_products"

urlpatterns = [

    path('product-management/',views.product_management,name='product_management'),
    path('add-product/',views.add_product,name='add_product'),

    path('edit-product/<int:product_id>/',views.edit_product,name='edit_product'),

    path('delete-product/<int:product_id>/',views.delete_product,name='delete_product'),

    path("variant-management/<int:product_id>/",views.variant_management,name="variant_management"),

    path("add-variant/<int:product_id>/",views.add_variant,name="add_variant"),

    path("edit-variant/<int:variant_id>/",views.edit_variant,name="edit_variant"),
    path("delete-variant/<int:variant_id>/",views.delete_variant,name="delete_variant"),

]
