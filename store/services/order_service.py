# order_service.py
# Business logic for cart summarisation and order creation.
# Keeping this in a separate "service" file means views stay thin
# (just handle HTTP) and this logic can be tested independently.

# Decimal is used instead of float to avoid rounding errors with money values.
# Docs: https://docs.python.org/3/library/decimal.html
from decimal import Decimal
from django.shortcuts import get_object_or_404
from store.models import Order, OrderItem, Product, Design


def build_cart_summary(cart):
    """
    Converts the raw session cart into usable data for templates and order creation.

    Input:  cart — dict from session, e.g. {"3": {"qty": 2}, "7": {"qty": 1}}
    Output: (items list, total Decimal)

    Each item in the list is a dict with:
      - product: the full Product object (fetched from DB)
      - qty:     how many the user wants
      - subtotal: price × qty for that line
    """
    items = []
    total = Decimal("0.00")

    for product_id_str, data in cart.items():
        # Session keys are always strings, so convert to int for the DB lookup
        product   = get_object_or_404(Product, id=int(product_id_str))
        qty       = int(data.get("qty", 1))
        design_id = data.get("design_id")  # set when adding from My Designs
        subtotal  = Decimal(str(product.price)) * qty  # use Decimal to avoid float rounding issues
        total    += subtotal

        # Fetch the Design object so the cart template can show a preview thumbnail
        design = None
        if design_id:
            try:
                design = Design.objects.get(id=design_id)
            except Design.DoesNotExist:
                pass

        items.append({
            "product":   product,
            "qty":       qty,
            "subtotal":  subtotal,
            "design_id": design_id,
            "design":    design,
        })

    return items, total


def create_order_from_cart(cart, user, delivery_data):
    """
    Creates one Order row + one OrderItem row per product in the cart.

    Inputs:
      cart          — session cart dict
      user          — logged-in User object, or None for guest checkout
      delivery_data — cleaned dict from CheckoutForm (name, address, etc.)

    The ** unpacking spreads delivery_data fields directly into Order.objects.create()
    so we don't have to list each field manually.
    """
    items, total = build_cart_summary(cart)

    # Create the order header row
    order = Order.objects.create(
        user=user,
        total_amount=total,
        status="PENDING",
        **delivery_data  # unpacks full_name, email, address_line1, city, postcode, country
    )

    # Create one OrderItem per product in the cart and deduct from stock
    for item in items:
        design = None
        if item.get("design_id"):
            try:
                design = Design.objects.get(id=item["design_id"])
            except Design.DoesNotExist:
                pass
        OrderItem.objects.create(
            order=order,
            product=item["product"],
            qty=item["qty"],
            unit_price=item["product"].price,  # snapshot price at time of purchase
            design=design,
        )
        # Reduce stock — clamp to 0 so it never goes negative
        product = item["product"]
        product.stock = max(0, product.stock - item["qty"])
        product.save(update_fields=["stock"])

    return order
