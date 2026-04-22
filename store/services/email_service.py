# email_service.py
# I switched from Django's SMTP email to Resend's HTTP API because Railway blocks SMTP.
# Resend sends emails over HTTPS so it works on any host.
# If RESEND_API_KEY isn't set, I fall back to Django's send_mail so local dev still works.
# Resend Python SDK docs: https://resend.com/docs/send-with-python
# Django send_mail docs:  https://docs.djangoproject.com/en/5.0/topics/email/

import os
import logging
import resend
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')


def _send(to_email, subject, body):
    # I use Resend in production (when the API key is set) and fall back to Django SMTP locally.
    if RESEND_API_KEY:
        resend.api_key = RESEND_API_KEY
        try:
            resend.Emails.send({
                "from": "Proxy Store <onboarding@resend.dev>",
                "to": [to_email],
                "subject": subject,
                "text": body,
            })
        except Exception as e:
            logger.error("Resend email failed: %s", e)
    else:
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error("SMTP email failed: %s", e)


def send_order_status_update(order):
    # I call this whenever an admin changes an order's status in the admin panel.
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
        return

    _send(order.email, subject, body)


def send_order_confirmation(order):
    # I call this right after a customer pays so they immediately get a receipt.
    items = order.items.select_related("product").all()
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
    _send(order.email, subject, message)
