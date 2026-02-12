from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path("about/", views.about, name="about"),

    path("product/<int:product_id>/", views.product_detail, name="product_detail"),

    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),

    path("checkout/", views.checkout_view, name="checkout"),
    path("thank-you/<int:order_id>/", views.thank_you, name="thank_you"),
    path("payment/<int:order_id>/", views.payment_view, name="payment"),

    path("customise/<int:product_id>/", views.customise_view, name="customise"),
    path("save-design/<int:product_id>/", views.save_design_view, name="save_design"),
    path("my-designs/", views.my_designs_view, name="my_designs"),

    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    
    path("admin-panel/", include("store.admin_urls")),  # custom admin

]
