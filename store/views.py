# views.py
# This file contains all the "view" functions for the store.
# A view is just a Python function that:
#   1. Receives an HTTP request from the browser
#   2. Does some work (reads the database, processes a form, etc.)
#   3. Returns an HTTP response (usually a rendered HTML page, or a redirect)
#
# Django routes each URL to the correct view function (see urls.py).

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile

import base64   # for decoding base64 image strings
import json     # for parsing and building JSON data
import uuid     # for generating unique filenames

from .models import Product, Order, Design
from .forms import CheckoutForm
from .services.order_service import build_cart_summary, create_order_from_cart
from .services.payment_service import mark_order_paid
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegisterForm


# ============================================================
# BASIC PAGES
# These views just render a template — no complex logic needed.
# ============================================================

def home(request):
    # Grab the 4 newest products to show as "featured" on the homepage
    featured = Product.objects.all().order_by("-created_at")[:4]
    return render(request, "store/home.html", {"featured": featured})


def about(request):
    # Static page — no database needed, just render the template
    return render(request, "store/about.html")


def shop(request):
    # Show all products, newest first
    products = Product.objects.all().order_by("-created_at")

    # If the user typed something in the search box, filter by name
    # request.GET.get("q") reads the ?q= value from the URL
    q = request.GET.get("q", "").strip()
    if q:
        products = products.filter(name__icontains=q)  # case-insensitive "contains" search

    return render(request, "store/shop.html", {"products": products, "q": q})


def product_detail(request, product_id):
    # get_object_or_404 fetches the product from the database.
    # If no product with that ID exists, it shows a 404 page automatically.
    product = get_object_or_404(Product, id=product_id)
    return render(request, "store/product_detail.html", {"product": product})


# ============================================================
# CART (SESSION-BASED)
# The cart is stored in the user's server-side session.
# No login needed — guests can shop too.
# Cart format in session: {"product_id": {"qty": 2}, "7": {"qty": 1}, ...}
# ============================================================

def cart_view(request):
    # Read the cart dict from the session (empty dict if nothing added yet)
    cart = request.session.get("cart", {})
    # build_cart_summary converts raw IDs + quantities into full product objects + totals
    items, total = build_cart_summary(cart)
    return render(request, "store/cart.html", {"items": items, "total": total})


def cart_add(request, product_id):
    # Only accept POST — prevents adding items by just typing a URL
    if request.method != "POST":
        return redirect("product_detail", product_id=product_id)

    product = get_object_or_404(Product, id=product_id)

    # I check stock here so nobody can add an out-of-stock product to their cart
    if product.stock <= 0:
        return redirect("product_detail", product_id=product_id)

    cart = request.session.get("cart", {})
    key = str(product_id)  # session keys must always be strings

    try:
        qty = max(1, int(request.POST.get("qty", 1)))
    except ValueError:
        qty = 1

    # design_id is passed as a hidden field when the user clicks "Add to Cart" from My Designs.
    # I store it in the cart so I can link the custom design to the OrderItem when they checkout.
    try:
        design_id = int(request.POST.get("design_id") or 0) or None
    except ValueError:
        design_id = None

    # I work out how many of this product are already in the cart,
    # then cap the quantity so the total never exceeds what's actually in stock
    current_qty = cart[key]["qty"] if key in cart else 0
    qty = min(qty, product.stock - current_qty)
    if qty <= 0:
        return redirect("cart")

    if key in cart:
        cart[key]["qty"] += qty
        if design_id:
            cart[key]["design_id"] = design_id
    else:
        entry = {"qty": qty}
        if design_id:
            entry["design_id"] = design_id
        cart[key] = entry

    request.session["cart"] = cart
    request.session.modified = True  # tell Django the session has changed so it saves it
    return redirect("cart")


def cart_remove(request, product_id):
    cart = request.session.get("cart", {})
    key = str(product_id)

    if key in cart:
        del cart[key]  # remove this product from the cart
        request.session["cart"] = cart
        request.session.modified = True

    return redirect("cart")


def cart_update(request, product_id):
    # Called when the user types a new quantity or clicks +/- buttons
    if request.method != "POST":
        return redirect("cart")

    cart = request.session.get("cart", {})
    key = str(product_id)

    try:
        qty = int(request.POST.get("qty", 1))
    except ValueError:
        qty = 1  # default to 1 if the value isn't a valid number

    if qty < 1:
        cart.pop(key, None)  # quantity 0 or less = remove from cart
    elif key in cart:
        # Cap at available stock so the user can't order more than exists
        from .models import Product as P
        try:
            p = P.objects.get(id=int(product_id))
            qty = min(qty, p.stock)
        except P.DoesNotExist:
            pass
        cart[key]["qty"] = qty

    request.session["cart"] = cart
    request.session.modified = True
    return redirect("cart")


# ============================================================
# CHECKOUT + PAYMENT
# The flow is:
#   checkout page (fill in address) → payment page (click Pay) → thank you page
#
# Responsibilities are separated:
#   - View  → handles the HTTP request/response
#   - Form  → validates user input (required fields, email format, etc.)
#   - Service → creates the Order rows in the database
# ============================================================

def checkout_view(request):
    cart = request.session.get("cart", {})

    # Don't let users reach checkout with an empty cart
    if not cart:
        return redirect("cart")

    items, total = build_cart_summary(cart)

    if request.method == "POST":
        form = CheckoutForm(request.POST)

        if form.is_valid():
            delivery_data = form.cleaned_data  # validated dict of field values

            # Create Order + OrderItems in the database
            order = create_order_from_cart(
                cart=cart,
                user=request.user if request.user.is_authenticated else None,
                delivery_data=delivery_data
            )

            # Clear the cart so it's empty for next time
            request.session["cart"] = {}

            # Record this order ID in the session so only this browser can pay/view it
            allowed = request.session.get("allowed_orders", [])
            allowed.append(order.id)
            request.session["allowed_orders"] = allowed
            request.session.modified = True

            # Redirect to the payment page, passing the new order's ID
            return redirect("payment", order_id=order.id)

    else:
        form = CheckoutForm()  # show a blank form on GET request

    return render(request, "store/checkout.html", {
        "form": form,
        "items": items,
        "total": total
    })


def _user_can_access_order(request, order):
    # I wrote this helper to fix a security issue called IDOR (Insecure Direct Object Reference).
    # Without this check, anyone could visit /payment/5/ and pay for (or view) someone else's order
    # just by guessing the order ID in the URL.
    #
    # My fix: a user can only access an order if:
    #   - They're logged in AND the order belongs to their account, OR
    #   - The order ID is stored in their session (set when they completed checkout)
    #
    # The session check covers guest users — when checkout creates the order,
    # I store its ID in request.session["allowed_orders"] so only that browser can pay it.
    if request.user.is_authenticated and order.user == request.user:
        return True
    if order.id in request.session.get("allowed_orders", []):
        return True
    return False


def payment_view(request, order_id):
    # Simulated payment — no real card processing.
    # GET: show the "Pay Now" button.
    # POST: mark the order as PAID and redirect to confirmation.
    order = get_object_or_404(Order, id=order_id)

    if not _user_can_access_order(request, order):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You do not have permission to access this order.")

    if request.method == "POST":
        mark_order_paid(order)  # sets order.status = "PAID" and saves
        from .services.email_service import send_order_confirmation
        send_order_confirmation(order)  # sends confirmation email to customer
        return redirect("thank_you", order_id=order.id)

    return render(request, "store/payment.html", {"order": order})


def thank_you(request, order_id):
    # Order confirmation page — just shows the order details
    order = get_object_or_404(Order, id=order_id)

    if not _user_can_access_order(request, order):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You do not have permission to access this order.")

    return render(request, "store/thank_you.html", {"order": order})


# ============================================================
# CUSTOMISER + DESIGNS
# @login_required means only logged-in users can access these views.
# If not logged in, Django redirects to the login page automatically.
#
# The customiser runs entirely in the browser (customise.js).
# When the user saves, the browser sends:
#   - design_data: JSON string with all elements (text, images, positions)
#   - preview_data_url: a base64 PNG screenshot of the canvas
#   - size: the clothing size chosen
# ============================================================

@login_required
def customise_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Show a friendly error if the admin forgot to upload a template image
    if not product.template_image:
        return render(request, "store/customise_missing_template.html", {"product": product})

    # If ?design=<id> is in the URL (from "Edit Again"), load the saved design JSON
    # so the customiser can restore the previous state
    initial_design = None
    design_id = request.GET.get("design")
    if design_id:
        try:
            saved = Design.objects.get(id=design_id, user=request.user, product=product)
            # json.loads converts the stored JSON string back into a Python dict
            initial_design = json.loads(saved.design_data)
        except (Design.DoesNotExist, json.JSONDecodeError):
            pass  # if anything goes wrong, just start with a blank canvas

    context = {
        "product": product,
        "print_area": {
            "x": product.print_x,
            "y": product.print_y,
            "w": product.print_w,
            "h": product.print_h,
        },
        "initial_design": initial_design,
    }
    return render(request, "store/customise.html", context)


@login_required
def save_design_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method != "POST":
        return redirect("customise", product_id=product.id)

    design_json      = request.POST.get("design_data", "")
    preview_data_url = request.POST.get("preview_data_url", "")
    size             = request.POST.get("size", "")

    # design_json is the minimum required — preview is optional
    if not design_json:
        return redirect("customise", product_id=product.id)

    # --- Convert embedded base64 images to saved files ---
    # When a user uploads an image in the customiser, it's stored in the JSON
    # as a huge base64 string (e.g. "data:image/png;base64,iVBORw0KGgo...").
    # We extract each one, save it as a real file in media/design_images/,
    # and replace the base64 blob with a normal server URL.
    # This keeps the design JSON small and lets the admin preview load images normally.
    try:
        data = json.loads(design_json)
        elements = data.get("elements")
        if isinstance(elements, list):
            for el in elements:
                if not isinstance(el, dict) or el.get("type") != "image":
                    continue
                src = el.get("src", "")
                if not src.startswith("data:"):
                    continue  # already a URL — nothing to do
                try:
                    # A data URL looks like: "data:image/png;base64,<actual data>"
                    header, b64 = src.split(",", 1)
                    # Work out the file extension from the header
                    ext = "gif" if "gif" in header else ("jpg" if "jpeg" in header else "png")
                    img_bytes = base64.b64decode(b64)  # decode base64 → raw bytes
                    filename = f"design_img_{uuid.uuid4().hex}.{ext}"  # unique filename
                    from django.core.files.storage import default_storage
                    # Save the file into media/design_images/ and get back the path
                    path = default_storage.save(f"design_images/{filename}", ContentFile(img_bytes))
                    el["src"] = default_storage.url(path)  # replace blob with URL
                except Exception:
                    el["src"] = None  # if saving fails, remove the broken blob
        design_json = json.dumps(data)  # convert the updated dict back to a JSON string
    except (json.JSONDecodeError, Exception):
        pass  # if JSON parsing fails, save whatever we received

    # Create the Design row in the database
    design = Design.objects.create(
        user=request.user,
        product=product,
        design_data=design_json,
        size=size
    )

    # --- Save the canvas screenshot as a preview image ---
    # The browser sends the canvas as a base64 PNG string.
    # We decode it and save it as a real image file.
    try:
        _, data = preview_data_url.split(";base64,")
        file_data = base64.b64decode(data)
        design.preview.save(
            f"design_{design.id}.png",
            ContentFile(file_data),
            save=True
        )
    except Exception:
        pass  # preview is optional — keep the design even if this fails

    return redirect("my_designs")


@login_required
def my_orders_view(request):
    # prefetch_related loads all order items and their linked designs in 2 extra queries
    # instead of one query per item (much more efficient with multiple orders)
    orders = Order.objects.filter(user=request.user).prefetch_related(
        "items__product", "items__design"
    ).order_by("-created_at")
    return render(request, "store/my_orders.html", {"orders": orders})


@login_required
def my_designs_view(request):
    # Show all saved designs for the currently logged-in user, newest first
    designs = Design.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "store/my_designs.html", {"designs": designs})


@login_required
def delete_design_view(request, design_id):
    # Only allow POST to prevent accidental deletion via a link
    if request.method == "POST":
        design = get_object_or_404(Design, id=design_id, user=request.user)
        design.delete()
    return redirect("my_designs")


# ============================================================
# AUTHENTICATION
# Django handles password hashing automatically — we never store plain text.
# CSRF tokens in forms protect against cross-site request forgery attacks.
# ============================================================

def register_view(request):
    # If already logged in, no need to register — send them home
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()    # creates the user with a hashed password
            login(request, user)  # auto-login after signup — better user experience
            return redirect("home")
    else:
        form = RegisterForm()  # show a blank form on GET

    return render(request, "store/register.html", {"form": form})


def login_view(request):
    # If already logged in, redirect away from the login page
    if request.user.is_authenticated:
        return redirect("home")

    next_url = request.GET.get("next") or request.POST.get("next") or ""

    # I added rate limiting to protect against brute force attacks —
    # where someone writes a script that tries thousands of passwords automatically.
    # My approach: I store a list of failure timestamps in the session.
    # On each request I throw away anything older than 10 minutes,
    # then check if 5 or more failures remain. If so, I block the form entirely.
    import time
    MAX_ATTEMPTS = 5
    WINDOW_SECONDS = 600  # 10 minutes

    now = time.time()
    attempts = [t for t in request.session.get("login_attempts", []) if now - t < WINDOW_SECONDS]
    rate_limited = len(attempts) >= MAX_ATTEMPTS

    if request.method == "POST" and not rate_limited:
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            request.session.pop("login_attempts", None)  # clear the failure count on a successful login
            if next_url:
                return redirect(next_url)
            return redirect("admin_dashboard" if user.is_staff else "home")
        else:
            # Wrong credentials — I record this failure timestamp so I can count it later
            attempts.append(now)
            request.session["login_attempts"] = attempts
    else:
        form = AuthenticationForm()

    form.fields["username"].widget.attrs.update({"class": "input-field", "placeholder": "Username"})
    form.fields["password"].widget.attrs.update({"class": "input-field", "placeholder": "Password"})

    return render(request, "store/login.html", {"form": form, "next": next_url, "rate_limited": rate_limited})


def logout_view(request):
    # Clears the user's session and sends them back to the homepage
    logout(request)
    return redirect("home")


# ============================================================
# ACCOUNT SETTINGS
# I built this page so logged-in users can update their email or change their password
# without needing to contact an admin.
# I use Django's built-in PasswordChangeForm which handles all the validation
# (checking old password is correct, new passwords match, meets strength rules).
# I also call update_session_auth_hash after a password change — without this,
# Django would log the user out immediately because the session hash no longer matches.
# ============================================================

@login_required
def account_settings_view(request):
    from django.contrib.auth.forms import PasswordChangeForm
    from django.contrib.auth import update_session_auth_hash

    email_saved    = False
    password_saved = False
    password_form  = PasswordChangeForm(request.user)

    # I apply the same CSS class used everywhere else so the inputs look consistent
    for field in ("old_password", "new_password1", "new_password2"):
        password_form.fields[field].widget.attrs.update({"class": "input-field"})

    if request.method == "POST":
        # I use a hidden "action" field in each form to tell the view which form was submitted,
        # since both the email form and password form post to the same URL
        action = request.POST.get("action")

        if action == "email":
            new_email = request.POST.get("email", "").strip()
            if new_email:
                request.user.email = new_email
                request.user.save()
                email_saved = True  # I pass this to the template to show a success message

        elif action == "password":
            password_form = PasswordChangeForm(request.user, request.POST)
            for field in ("old_password", "new_password1", "new_password2"):
                password_form.fields[field].widget.attrs.update({"class": "input-field"})
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # keeps the user logged in after changing password
                password_saved = True  # I pass this to the template to show a success message

    return render(request, "store/account_settings.html", {
        "password_form":  password_form,
        "email_saved":    email_saved,
        "password_saved": password_saved,
    })
