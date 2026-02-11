from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile

import base64

from .models import Product, Order, Design
from .forms import CheckoutForm
from .services.order_service import build_cart_summary, create_order_from_cart
from .services.payment_service import mark_order_paid


# ----------------------------
# BASIC PAGES
# ----------------------------

def home(request):
    featured = Product.objects.all().order_by("-created_at")[:4]
    return render(request, "store/home.html", {"featured": featured})


def about(request):
    return render(request, "store/about.html")


def shop(request):
    products = Product.objects.all().order_by("-created_at")
    return render(request, "store/shop.html", {"products": products})


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, "store/product_detail.html", {"product": product})


# ----------------------------
# CART (SESSION-BASED)
# ----------------------------

def cart_view(request):
    cart = request.session.get("cart", {})
    items, total = build_cart_summary(cart)
    return render(request, "store/cart.html", {"items": items, "total": total})


def cart_add(request, product_id):
    # Only allow add via POST (prevents “add by typing URL”)
    if request.method != "POST":
        return redirect("product_detail", product_id=product_id)

    cart = request.session.get("cart", {})
    key = str(product_id)

    if key in cart:
        cart[key]["qty"] += 1
    else:
        cart[key] = {"qty": 1}

    request.session["cart"] = cart
    request.session.modified = True
    return redirect("cart")


def cart_remove(request, product_id):
    cart = request.session.get("cart", {})
    key = str(product_id)

    if key in cart:
        del cart[key]
        request.session["cart"] = cart
        request.session.modified = True

    return redirect("cart")


# ----------------------------
# CHECKOUT + PAYMENT
# ----------------------------

def checkout_view(request):
    """
    - View handles request/response only
    - Form handles validation
    - Service handles order creation logic
    """
    cart = request.session.get("cart", {})

    if not cart:
        return redirect("cart")

    items, total = build_cart_summary(cart)

    if request.method == "POST":
        form = CheckoutForm(request.POST)

        if form.is_valid():
            delivery_data = form.cleaned_data

            order = create_order_from_cart(
                cart=cart,
                user=request.user if request.user.is_authenticated else None,
                delivery_data=delivery_data
            )

            # Clear cart after order is created
            request.session["cart"] = {}
            request.session.modified = True

            # Send them to payment step
            return redirect("payment", order_id=order.id)

    else:
        form = CheckoutForm()

    return render(request, "store/checkout.html", {
        "form": form,
        "items": items,
        "total": total
    })


def payment_view(request, order_id):
    """
    Payment step (simulated).
    View is thin: it just updates the order using a service.
    """
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        mark_order_paid(order)
        return redirect("thank_you", order_id=order.id)

    return render(request, "store/payment.html", {"order": order})


def thank_you(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "store/thank_you.html", {"order": order})


# ----------------------------
# CUSTOMISER + DESIGNS
# ----------------------------

@login_required
def customise_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # If template_image is missing, show a friendly page instead of crashing
    if not product.template_image:
        return render(request, "store/customise_missing_template.html", {"product": product})

    context = {
        "product": product,
        "print_area": {
            "x": product.print_x,
            "y": product.print_y,
            "w": product.print_w,
            "h": product.print_h,
        }
    }
    return render(request, "store/customise.html", context)


@login_required
def save_design_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method != "POST":
        return redirect("customise", product_id=product.id)

    design_json = request.POST.get("design_data", "")
    preview_data_url = request.POST.get("preview_data_url", "")
    size = request.POST.get("size", "")

    # If the JS didn't send design data, just bounce back
    if not design_json or not preview_data_url:
        return redirect("customise", product_id=product.id)

    # Save design row in SQL
    design = Design.objects.create(
        user=request.user,
        product=product,
        design_data=design_json,
        size=size
    )

    # Save preview image (canvas screenshot) as a real file
    try:
        header, data = preview_data_url.split(";base64,")
        file_data = base64.b64decode(data)
        design.preview.save(
            f"design_{design.id}.png",
            ContentFile(file_data),
            save=True
        )
    except Exception:
        # If image saving fails, we still keep the design JSON
        pass

    return redirect("my_designs")


@login_required
def my_designs_view(request):
    designs = Design.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "store/my_designs.html", {"designs": designs})
