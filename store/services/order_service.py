from decimal import Decimal
from django.shortcuts import get_object_or_404
from store.models import Order, OrderItem, Product

def build_cart_summary(cart):
    """
    Turns the session cart into a list of items + a total.
    Keeping this outside views makes it reusable + testable.
    """
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
            "subtotal": subtotal
        })

    return items, total


def create_order_from_cart(cart, user, delivery_data):
    """
    Creates an Order + OrderItems using cart session data.
    """
    items, total = build_cart_summary(cart)

    order = Order.objects.create(
        user=user,
        total_amount=total,
        status="PENDING",
        **delivery_data
    )

    for item in items:
        OrderItem.objects.create(
            order=order,
            product=item["product"],
            qty=item["qty"],
            unit_price=item["product"].price
        )

    return order
