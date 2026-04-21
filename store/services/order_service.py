# order_service.py
# Business logic for cart summarisation and order creation.
# Keeping this in a separate "service" file means views stay thin
# (just handle HTTP) and this logic can be tested independently.

from decimal import Decimal
from django.shortcuts import get_object_or_404
from store.models import Order, OrderItem, Product


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
        product  = get_object_or_404(Product, id=int(product_id_str))
        qty      = int(data.get("qty", 1))
        subtotal = Decimal(str(product.price)) * qty  # use Decimal to avoid float rounding issues
        total   += subtotal

        items.append({
            "product":  product,
            "qty":      qty,
            "subtotal": subtotal,
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

    # Create one OrderItem per product in the cart
    for item in items:
        OrderItem.objects.create(
            order=order,
            product=item["product"],
            qty=item["qty"],
            unit_price=item["product"].price  # snapshot price at time of purchase
        )

    return order
