def cart_count(request):
    """
    Adds cart item count to every template.
    Using session cart: {"product_id": {"qty": number}}
    """
    cart = request.session.get("cart", {})

    # Total quantity of items (so if qty=3 it counts as 3)
    count = sum(item.get("qty", 0) for item in cart.values())

    return {"cart_count": count}
