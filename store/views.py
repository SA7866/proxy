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


from decimal import Decimal
from .models import Order, OrderItem

def checkout_view(request):
    """
    Checkout page:
    - Shows what is in the cart
    - Collects delivery details
    - Creates an Order + OrderItems when you submit
    """
    cart = request.session.get("cart", {})

    # If cart is empty, no point checking out
    if not cart:
        return redirect("cart")

    # Build summary for template
    items = []
    total = Decimal("0.00")

    for product_id_str, data in cart.items():
        product = get_object_or_404(Product, id=int(product_id_str))
        qty = int(data.get("qty", 1))
        subtotal = Decimal(str(product.price)) * qty
        total += subtotal

        items.append({
            "product": product,
            "qty": qty,
            "subtotal": subtotal,
        })

    # If user submitted the form
    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        address_line1 = request.POST.get("address_line1", "").strip()
        city = request.POST.get("city", "").strip()
        postcode = request.POST.get("postcode", "").strip()
        country = request.POST.get("country", "").strip()

        # Simple validation (basic but fine for prototype)
        if not all([full_name, email, address_line1, city, postcode, country]):
            return render(request, "store/checkout.html", {
                "items": items,
                "total": total,
                "error": "Please fill in all delivery fields."
            })

        # Create order
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            full_name=full_name,
            email=email,
            address_line1=address_line1,
            city=city,
            postcode=postcode,
            country=country,
            total_amount=total,
            status="PENDING"
        )

        # Create order items
        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item["product"],
                qty=item["qty"],
                unit_price=item["product"].price
            )

        # Clear cart after placing order (like a real checkout)
        request.session["cart"] = {}
        request.session.modified = True

        return redirect("thank_you", order_id=order.id)

    # Normal GET request shows the page
    return render(request, "store/checkout.html", {"items": items, "total": total})


def thank_you(request, order_id):
    """
    Simple confirmation page.
    Shows order number so it feels real.
    """
    order = get_object_or_404(Order, id=order_id)
    return render(request, "store/thank_you.html", {"order": order})
