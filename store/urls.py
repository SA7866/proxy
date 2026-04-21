# urls.py
# Maps URL patterns to view functions.
# When a user visits a URL, Django checks this list top-to-bottom
# and calls the matching view function.
# 'name' lets templates use {% url 'name' %} instead of hard-coding paths.

from django.urls import path, include
from . import views

urlpatterns = [

    # --- Public pages ---
    path("",        views.home,           name="home"),
    path("shop/",   views.shop,           name="shop"),
    path("about/",  views.about,          name="about"),

    # <int:product_id> captures the ID from the URL and passes it to the view
    path("product/<int:product_id>/", views.product_detail, name="product_detail"),

    # --- Cart (session-based, no login required) ---
    path("cart/",                          views.cart_view,   name="cart"),
    path("cart/add/<int:product_id>/",     views.cart_add,    name="cart_add"),
    path("cart/remove/<int:product_id>/",  views.cart_remove, name="cart_remove"),
    path("cart/update/<int:product_id>/",  views.cart_update, name="cart_update"),

    # --- Checkout flow: form → payment → confirmation ---
    path("checkout/",                  views.checkout_view, name="checkout"),
    path("payment/<int:order_id>/",    views.payment_view,  name="payment"),
    path("thank-you/<int:order_id>/",  views.thank_you,     name="thank_you"),

    # --- Customiser (login required) ---
    path("customise/<int:product_id>/",     views.customise_view,   name="customise"),
    path("save-design/<int:product_id>/",   views.save_design_view, name="save_design"),
    path("my-designs/",                        views.my_designs_view,    name="my_designs"),
    path("my-designs/delete/<int:design_id>/", views.delete_design_view, name="delete_design"),
    path("my-orders/",                      views.my_orders_view,   name="my_orders"),

    # --- Authentication ---
    path("register/", views.register_view, name="register"),
    path("login/",    views.login_view,    name="login"),
    path("logout/",   views.logout_view,   name="logout"),

    # --- Custom admin panel (staff only) ---
    # All /admin-panel/... URLs are defined in store/admin_urls.py
    path("admin-panel/", include("store.admin_urls")),

]
