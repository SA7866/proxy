# admin_views.py
# Custom admin panel views — only accessible by staff users (is_staff = True).
# This replaces Django's built-in /admin/ with a purpose-built interface
# that matches the site's styling and only exposes what this project needs.

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User

import json

from .models import Product, Order, Design


# -------------------------------------------------------
# Access guard — wraps every admin view
# -------------------------------------------------------
def staff_only(user):
    """Returns True only if the user is logged in AND has is_staff = True."""
    return user.is_authenticated and user.is_staff

# Decorator created from the check above.
# Applied to every view below with @staff_required.
# If the check fails, Django redirects to the login page automatically.
staff_required = user_passes_test(staff_only)


# -------------------------------------------------------
# Dashboard — admin home page
# -------------------------------------------------------
@staff_required
def admin_dashboard(request):
    # Collect counts and recent orders to display on the dashboard
    return render(request, "store/admin/dashboard.html", {
        "product_count": Product.objects.count(),
        "order_count":   Order.objects.count(),
        "design_count":  Design.objects.count(),
        "user_count":    User.objects.count(),
        "recent_orders": Order.objects.order_by("-created_at")[:5]
    })


# -------------------------------------------------------
# PRODUCTS — full CRUD (Create, Read, Update, Delete)
# -------------------------------------------------------

@staff_required
def admin_products_list(request):
    # List all products, newest first
    products = Product.objects.all().order_by("-created_at")
    return render(request, "store/admin/products_list.html", {"products": products})


@staff_required
def admin_products_create(request):
    """
    GET:  Show the blank product form.
    POST: Read the submitted values, create a new Product row, then redirect.
    Manual form handling (no Django Form class) keeps it simple for admin use.
    """
    if request.method == "POST":
        Product.objects.create(
            name           = request.POST.get("name", "").strip(),
            price          = request.POST.get("price") or 0,
            description    = request.POST.get("description", "").strip(),
            image          = request.FILES.get("image"),           # shop image
            template_image = request.FILES.get("template_image"),  # customiser PNG
            print_x        = int(request.POST.get("print_x") or 270),
            print_y        = int(request.POST.get("print_y") or 210),
            print_w        = int(request.POST.get("print_w") or 300),
            print_h        = int(request.POST.get("print_h") or 360),
        )
        return redirect("admin_products_list")

    # GET: render empty form
    return render(request, "store/admin/products_form.html", {
        "mode": "create",
        "product": None
    })


@staff_required
def admin_products_edit(request, product_id):
    """
    GET:  Show the form pre-filled with the product's current values.
    POST: Update only the fields that were changed.
          Images are only replaced if a new file was actually uploaded.
    """
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        product.name        = request.POST.get("name", "").strip()
        product.price       = request.POST.get("price") or 0
        product.description = request.POST.get("description", "").strip()

        # Only update images if a new file was uploaded — keeps existing images otherwise
        if request.FILES.get("image"):
            product.image = request.FILES["image"]
        if request.FILES.get("template_image"):
            product.template_image = request.FILES["template_image"]

        # Fall back to current value if the field was left blank
        product.print_x = int(request.POST.get("print_x") or product.print_x)
        product.print_y = int(request.POST.get("print_y") or product.print_y)
        product.print_w = int(request.POST.get("print_w") or product.print_w)
        product.print_h = int(request.POST.get("print_h") or product.print_h)

        product.save()
        return redirect("admin_products_list")

    # GET: render form pre-filled with existing product data
    return render(request, "store/admin/products_form.html", {
        "mode": "edit",
        "product": product
    })


@staff_required
def admin_products_delete(request, product_id):
    """
    GET:  Show a confirmation page (prevents accidental deletion).
    POST: Actually delete the product.
    Always confirm before deleting — a GET request alone cannot delete anything.
    """
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        product.delete()
        return redirect("admin_products_list")

    # Show a "are you sure?" page before deleting
    return render(request, "store/admin/confirm_delete.html", {
        "title":      "Delete product",
        "message":    f"Are you sure you want to delete '{product.name}'?",
        "cancel_url": "admin_products_list"
    })


# -------------------------------------------------------
# ORDERS — view and update status
# -------------------------------------------------------

@staff_required
def admin_orders_list(request):
    # All orders, newest first
    orders = Order.objects.all().order_by("-created_at")
    return render(request, "store/admin/orders_list.html", {"orders": orders})


@staff_required
def admin_orders_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = order.items.all()  # uses related_name="items" set on OrderItem
    return render(request, "store/admin/orders_detail.html", {"order": order, "items": items})


@staff_required
def admin_orders_update_status(request, order_id):
    """
    Admin can move an order through: PENDING → PAID → SHIPPED.
    Only accepts POST so status can't be changed by visiting a URL.
    Invalid status values are silently ignored.
    """
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        new_status = request.POST.get("status")
        # Whitelist valid statuses — rejects any unexpected value
        if new_status in ["PENDING", "PAID", "SHIPPED"]:
            order.status = new_status
            order.save()

    return redirect("admin_orders_detail", order_id=order.id)


# -------------------------------------------------------
# DESIGNS — read-only view for admin
# -------------------------------------------------------

@staff_required
def admin_designs_list(request):
    # select_related fetches user + product in the same query (more efficient)
    designs = Design.objects.select_related("user", "product").order_by("-created_at")
    return render(request, "store/admin/designs_list.html", {"designs": designs})


@staff_required
def admin_designs_detail(request, design_id):
    design = get_object_or_404(Design, id=design_id)
    try:
        design_json = json.loads(design.design_data)
    except (json.JSONDecodeError, TypeError):
        design_json = {}

    # Build scaled preview elements (900×650 canvas → 450×325 preview, scale = 0.5)
    SCALE = 0.5
    raw_els = design_json.get("elements") if isinstance(design_json.get("elements"), list) else []
    preview_elements = []
    for el in raw_els:
        if not isinstance(el, dict):
            continue
        preview_elements.append({
            "type":       el.get("type"),
            "x":          round((el.get("x") or 0) * SCALE),
            "y":          round((el.get("y") or 0) * SCALE),
            "w":          round((el.get("w") or 0) * SCALE),
            "h":          round((el.get("h") or 0) * SCALE),
            "opacity":    el.get("opacity") or 1,
            "text":       el.get("text") or "",
            "fontSize":   round((el.get("fontSize") or 24) * SCALE),
            "color":      el.get("color") or "#000000",
            "fontFamily": el.get("fontFamily") or "Arial",
            "bold":       bool(el.get("bold")),
            "italic":     bool(el.get("italic")),
            "useBg":      bool(el.get("useBg")),
            "bgColor":    el.get("bgColor") or "#ffffff",
            "src":        el.get("src") if el.get("type") == "image" else None,
        })

    return render(request, "store/admin/designs_detail.html", {
        "design":           design,
        "design_json":      design_json,
        "preview_elements": preview_elements,
        "shirt_color":      design_json.get("shirtColor") or "#ffffff",
    })


# -------------------------------------------------------
# USERS — list and toggle active/inactive
# -------------------------------------------------------

@staff_required
def admin_users_list(request):
    # All users, newest registrations first
    users = User.objects.all().order_by("-date_joined")
    return render(request, "store/admin/users_list.html", {"users": users})


@staff_required
def admin_users_toggle_active(request, user_id):
    """
    Flips a user's is_active flag (active → inactive or vice versa).
    is_active = False means they can no longer log in.
    Safety check: you cannot deactivate your own account.
    """
    user = get_object_or_404(User, id=user_id)

    # Prevent admins from accidentally locking themselves out
    if user.id != request.user.id:
        user.is_active = not user.is_active
        user.save()

    return redirect("admin_users_list")
