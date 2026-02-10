from django.shortcuts import render, get_object_or_404, redirect
from .models import Product

# Home page - simple landing page for now
def home(request):
    # In a real site we might show featured items here
    featured = Product.objects.all().order_by("-created_at")[:4]
    return render(request, "store/home.html", {"featured": featured})

# About page - explains the project
def about(request):
    return render(request, "store/about.html")

# Shop page - lists all products
def shop(request):
    products = Product.objects.all().order_by("-created_at")
    return render(request, "store/shop.html", {"products": products})

# Product detail page - shows one product
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, "store/product_detail.html", {"product": product})

# ---- CART (session-based) ----
# We store the cart in request.session so it works without creating cart tables.
# Format example:
# cart = {"3": {"qty": 2}, "7": {"qty": 1}}

def cart_view(request):
    cart = request.session.get("cart", {})

    # Build a list of items for the template (product + qty + subtotal)
    items = []
    total = 0

    for product_id_str, data in cart.items():
        product = get_object_or_404(Product, id=int(product_id_str))
        qty = int(data.get("qty", 1))
        subtotal = float(product.price) * qty
        total += subtotal

        items.append({
            "product": product,
            "qty": qty,
            "subtotal": subtotal,
        })

    return render(request, "store/cart.html", {"items": items, "total": total})


def cart_add(request, product_id):
    # Only allow POST so people don’t add items by just opening a URL
    if request.method != "POST":
        return redirect("product_detail", product_id=product_id)

    cart = request.session.get("cart", {})
    key = str(product_id)

    if key in cart:
        cart[key]["qty"] += 1
    else:
        cart[key] = {"qty": 1}

    request.session["cart"] = cart
    request.session.modified = True  # tells Django “session changed”

    return redirect("cart")


def cart_remove(request, product_id):
    cart = request.session.get("cart", {})
    key = str(product_id)

    if key in cart:
        del cart[key]
        request.session["cart"] = cart
        request.session.modified = True

    return redirect("cart")
