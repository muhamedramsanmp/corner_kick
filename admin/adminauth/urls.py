from django.urls import path
from . import views

urlpatterns = [
    path('admin-login/', views.admin_login, name='admin_login'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('user-management/',views.user_management,name='user_management'),
    path('toggle-user/<int:user_id>/', views.toggle_user_status, name='toggle_user'),
    path('admin/logout/', views.admin_logout, name='admin_logout'),
    path(
    "sales-report/",
    views.sales_report,
    name="sales_report"
),
path(
    "sales-report/excel/",
    views.export_sales_excel,
    name="export_sales_excel"
),

path(
    "sales-report/pdf/",
    views.export_sales_pdf,
    name="export_sales_pdf"
),
]
