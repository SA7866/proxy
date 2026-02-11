def mark_order_paid(order, method="SIMULATED_CARD"):
    """
    For the prototype: mark order as paid.
    In a real system you'd integrate Stripe/PayPal etc.
    """
    order.status = "PAID"
    order.save()
    return order
