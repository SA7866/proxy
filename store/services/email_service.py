# email_service.py
# Sends a styled order confirmation email to the customer after payment.
# Uses Django's send_mail() which reads SMTP settings from settings.py.

from django.core.mail import send_mail
from django.conf import settings


def send_order_status_update(order):
    """
    Sends a short email to the customer when their order status changes to PAID or SHIPPED.
    Called from admin_orders_update_status() in admin_views.py.
    """
    if order.status == "PAID":
        subject = f"Payment Confirmed — Proxy #{order.id}"
        body = f"""Hi {order.full_name},

Your payment for Order #{order.id} has been confirmed.

We're now preparing your order for dispatch. You'll receive another
email as soon as it's on its way.

Total: £{order.total_amount:.2f}

— The Proxy Team
"""
    elif order.status == "SHIPPED":
        subject = f"Your Order Has Shipped — Proxy #{order.id}"
        body = f"""Hi {order.full_name},

Great news — Order #{order.id} is on its way!

DELIVERY ADDRESS
{order.address_line1}
{order.city}, {order.postcode}
{order.country}

Total: £{order.total_amount:.2f}

— The Proxy Team
"""
    else:
        return  # no email for PENDING

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            fail_silently=False,
        )
    except Exception:
        pass


def send_order_confirmation(order):
    """
    Sends a plain-text order confirmation to the customer's email address.
    Called from payment_view() in views.py right after the order is marked PAID.
    If sending fails (e.g. wrong credentials, no internet), the error is caught
    silently so the user still sees their thank-you page.
    """
    items = order.items.select_related("product").all()

    # Build the list of items as plain text lines
    lines = []
    for item in items:
        name = item.product.name if item.product else "Deleted product"
        lines.append(f"  {name} x{item.qty}  —  £{item.subtotal():.2f}")
    items_text = "\n".join(lines) if lines else "  (no items)"

    subject = f"Order Confirmed — Proxy #{order.id}"

    message = f"""Hi {order.full_name},

Thank you for your order! Here's a summary:

Order #{order.id}
Placed: {order.created_at.strftime('%d %b %Y, %H:%M')}

ITEMS
{items_text}

Total: £{order.total_amount:.2f}

DELIVERY ADDRESS
{order.address_line1}
{order.city}, {order.postcode}
{order.country}

We'll update you once your order ships.

— The Proxy Team
"""

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            fail_silently=False,
        )
    except Exception:
        # Don't crash the payment flow if email fails
        pass
