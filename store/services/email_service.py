# email_service.py
# I put all the email-sending logic in here so views.py stays clean.
# Django has a built-in send_mail() function that handles the SMTP connection for me —
# I just tell it what to send and where to send it.
# The SMTP credentials (Gmail address and app password) are read from settings.py,
# which in turn reads them from the .env file so they're never hardcoded in the code.

from django.core.mail import send_mail
from django.conf import settings


def send_order_status_update(order):
    # I call this whenever an admin changes an order's status in the admin panel.
    # It sends a different email depending on whether the order was marked as PAID or SHIPPED.
    # If the status is still PENDING, I don't send anything — there's nothing useful to say yet.

    if order.status == "PAID":
        # I set the subject and body for a payment confirmation email
        subject = f"Payment Confirmed — Proxy #{order.id}"
        body = f"""Hi {order.full_name},

Your payment for Order #{order.id} has been confirmed.

We're now preparing your order for dispatch. You'll receive another
email as soon as it's on its way.

Total: £{order.total_amount:.2f}

— The Proxy Team
"""
    elif order.status == "SHIPPED":
        # I include the delivery address so the customer knows where it's going
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
        # No email needed for PENDING status — just return early
        return

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            fail_silently=False,
        )
    except Exception:
        # I catch any error here so a broken email connection doesn't crash the admin panel
        pass


def send_order_confirmation(order):
    # I call this right after a customer pays, so they immediately get a receipt.
    # I build a plain-text email listing every item they ordered with the price,
    # then send it to whatever email address they entered at checkout.

    # I fetch all the order items and build a simple text list of them
    items = order.items.select_related("product").all()
    lines = []
    for item in items:
        # If the product was deleted from the shop, item.product will be None
        name = item.product.name if item.product else "Deleted product"
        lines.append(f"  {name} x{item.qty}  —  £{item.subtotal():.2f}")
    items_text = "\n".join(lines) if lines else "  (no items)"

    subject = f"Order Confirmed — Proxy #{order.id}"

    # I use an f-string here to insert the actual order values into the email body
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
        # I don't want a failed email to prevent the customer from seeing their thank-you page,
        # so I catch the error and silently move on
        pass
