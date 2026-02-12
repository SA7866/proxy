from django.urls import path
from . import admin_views

urlpatterns = [
    path("", admin_views.admin_dashboard, name="admin_dashboard"),

    # Products
    path("products/", admin_views.admin_products_list, name="admin_products_list"),
    path("products/create/", admin_views.admin_products_create, name="admin_products_create"),
    path("products/<int:product_id>/edit/", admin_views.admin_products_edit, name="admin_products_edit"),
    path("products/<int:product_id>/delete/", admin_views.admin_products_delete, name="admin_products_delete"),

    # Orders
    path("orders/", admin_views.admin_orders_list, name="admin_orders_list"),
    path("orders/<int:order_id>/", admin_views.admin_orders_detail, name="admin_orders_detail"),
    path("orders/<int:order_id>/status/", admin_views.admin_orders_update_status, name="admin_orders_update_status"),

    # Designs
    path("designs/", admin_views.admin_designs_list, name="admin_designs_list"),
    path("designs/<int:design_id>/", admin_views.admin_designs_detail, name="admin_designs_detail"),

    # Users
    path("users/", admin_views.admin_users_list, name="admin_users_list"),
    path("users/<int:user_id>/toggle-active/", admin_views.admin_users_toggle_active, name="admin_users_toggle_active"),
]
