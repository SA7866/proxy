from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User

from .models import Product, Order, OrderItem, Design

# -----------------------------
# Helper: only allow staff users
# -----------------------------
def staff_only(user):
    # "is_staff" is built-in Django flag
    return user.is_authenticated and user.is_staff

staff_required = user_passes_test(staff_only)


# -----------------------------
# Dashboard
# -----------------------------
@staff_required
def admin_dashboard(request):
    # quick stats for the admin home page
    return render(request, "store/admin/dashboard.html", {
        "product_count": Product.objects.count(),
        "order_count": Order.objects.count(),
        "design_count": Design.objects.count(),
        "user_count": User.objects.count(),
        "recent_orders": Order.objects.order_by("-created_at")[:5]
    })


# -----------------------------
# PRODUCTS (CRUD)
# -----------------------------
@staff_required
def admin_products_list(request):
    products = Product.objects.all().order_by("-created_at")
    return render(request, "store/admin/products_list.html", {"products": products})


@staff_required
def admin_products_create(request):
    # keeping it simple: manual form handling
    if request.method == "POST":
        Product.objects.create(
            name=request.POST.get("name", "").strip(),
            price=request.POST.get("price") or 0,
            description=request.POST.get("description", "").strip(),
            image=request.FILES.get("image"),
            template_image=request.FILES.get("template_image"),
            print_x=int(request.POST.get("print_x") or 270),
            print_y=int(request.POST.get("print_y") or 210),
            print_w=int(request.POST.get("print_w") or 300),
            print_h=int(request.POST.get("print_h") or 360),
        )
        return redirect("admin_products_list")

    return render(request, "store/admin/products_form.html", {
        "mode": "create",
        "product": None
    })


@staff_required
def admin_products_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        product.name = request.POST.get("name", "").strip()
        product.price = request.POST.get("price") or 0
        product.description = request.POST.get("description", "").strip()

        # optional image updates
        if request.FILES.get("image"):
            product.image = request.FILES["image"]
        if request.FILES.get("template_image"):
            product.template_image = request.FILES["template_image"]

        product.print_x = int(request.POST.get("print_x") or product.print_x)
        product.print_y = int(request.POST.get("print_y") or product.print_y)
        product.print_w = int(request.POST.get("print_w") or product.print_w)
        product.print_h = int(request.POST.get("print_h") or product.print_h)

        product.save()
        return redirect("admin_products_list")

    return render(request, "store/admin/products_form.html", {
        "mode": "edit",
        "product": product
    })


@staff_required
def admin_products_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # simple safety: only delete on POST
    if request.method == "POST":
        product.delete()
        return redirect("admin_products_list")

    return render(request, "store/admin/confirm_delete.html", {
        "title": "Delete product",
        "message": f"Are you sure you want to delete '{product.name}'?",
        "cancel_url": "admin_products_list"
    })


# -----------------------------
# ORDERS
# -----------------------------
@staff_required
def admin_orders_list(request):
    orders = Order.objects.all().order_by("-created_at")
    return render(request, "store/admin/orders_list.html", {"orders": orders})


@staff_required
def admin_orders_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = order.items.all()  # because related_name="items"
    return render(request, "store/admin/orders_detail.html", {"order": order, "items": items})


@staff_required
def admin_orders_update_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in ["PENDING", "PAID", "SHIPPED"]:
            order.status = new_status
            order.save()
    return redirect("admin_orders_detail", order_id=order.id)


# -----------------------------
# DESIGNS
# -----------------------------
@staff_required
def admin_designs_list(request):
    designs = Design.objects.select_related("user", "product").order_by("-created_at")
    return render(request, "store/admin/designs_list.html", {"designs": designs})


@staff_required
def admin_designs_detail(request, design_id):
    design = get_object_or_404(Design, id=design_id)
    return render(request, "store/admin/designs_detail.html", {"design": design})


# -----------------------------
# USERS
# -----------------------------
@staff_required
def admin_users_list(request):
    users = User.objects.all().order_by("-date_joined")
    return render(request, "store/admin/users_list.html", {"users": users})


@staff_required
def admin_users_toggle_active(request, user_id):
    user = get_object_or_404(User, id=user_id)

    # don't allow disabling yourself (basic safety)
    if user.id != request.user.id:
        user.is_active = not user.is_active
        user.save()

    return redirect("admin_users_list")
