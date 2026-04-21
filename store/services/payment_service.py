# payment_service.py
# Handles marking an order as paid.
# In this prototype payment is simulated — no real card details are processed.
# In a real system you would call the Stripe or PayPal API here,
# verify the payment succeeded, then update the order status.


def mark_order_paid(order):
    """
    Marks the given order as PAID and saves it to the database.
    In a real system you would call Stripe/PayPal here and verify
    the payment before updating the status.
    """
    order.status = "PAID"
    order.save()
    return order
