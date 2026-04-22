# models.py
# Defines the database tables (called "models" in Django).
# Each class = one table. Each attribute = one column.
# Docs: https://docs.djangoproject.com/en/5.0/topics/db/models/

from django.db import models
from django.conf import settings


class Product(models.Model):
    """
    Represents a product in the shop (e.g. T-shirt, hoodie, mug).

    Two images are stored:
    - image: shown on the shop/product pages
    - template_image: transparent PNG used on the customiser canvas
      so users can place text/images inside the printed area

    print_x/y/w/h define the rectangular "printable zone" on the
    template image (in pixels). The customiser uses these to stop
    designs going outside the printed area.
    """
    name        = models.CharField(max_length=120)
    price       = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField(blank=True)

    # Shown in shop and product detail pages
    image = models.ImageField(upload_to="products/", blank=True, null=True)

    # Used only in the customiser — should be a transparent PNG of the product
    template_image = models.ImageField(upload_to="templates/", blank=True, null=True)

    # How many units are available to purchase — decremented when an order is placed
    stock = models.PositiveIntegerField(default=10)

    # Coordinates + size of the printable zone on the template (pixels)
    print_x = models.IntegerField(default=150)  # left edge
    print_y = models.IntegerField(default=200)  # top edge
    print_w = models.IntegerField(default=300)  # width
    print_h = models.IntegerField(default=400)  # height

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Design(models.Model):
    """
    A custom design saved by a logged-in user for a specific product.

    design_data: JSON string holding all canvas elements
                 (text content, position, font size, colour; image src, position, size).
                 Saved so the design can be displayed later.

    preview: a PNG screenshot of the finished canvas (taken client-side with
             canvas.toDataURL() and sent as a base64 string). Stored as a real
             image file so it can be shown on the My Designs page without
             re-rendering the canvas.

    size: clothing size chosen by the user (S / M / L / XL).
    """
    # If the user account is deleted, all their designs are deleted too (CASCADE)
    # Docs on on_delete options: https://docs.djangoproject.com/en/5.0/ref/models/fields/#django.db.models.ForeignKey.on_delete
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="designs"
    )
    # If the product is deleted, designs linked to it are also deleted
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="designs"
    )

    STATUS_PENDING  = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"
    STATUS_CHOICES  = [
        ("PENDING",  "Pending Review"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    design_data = models.TextField()  # JSON string
    # ImageField handles file uploads and stores the path in the database
    # Docs: https://docs.djangoproject.com/en/5.0/ref/models/fields/#imagefield
    preview     = models.ImageField(upload_to="design_previews/", blank=True, null=True)
    size        = models.CharField(max_length=10, blank=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default="APPROVED")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Design #{self.id} - {self.product.name}"


class Order(models.Model):
    """
    One completed checkout = one Order row.

    Stores the delivery address + total at the time of purchase.
    Payment is simulated (no real card processing), so status moves:
      PENDING → PAID (on the payment page) → SHIPPED (admin sets this)

    user is nullable because we allow guest checkout (not logged in).
    If the account is later deleted, we keep the order history (SET_NULL).
    """
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PAID",    "Paid (Simulated)"),
        ("SHIPPED", "Shipped"),
    ]

    # Nullable so guests (not logged in) can still place orders
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # keep order even if user deleted
        null=True,
        blank=True
    )

    # Delivery details filled in at checkout
    full_name     = models.CharField(max_length=120)
    email         = models.EmailField()
    address_line1 = models.CharField(max_length=200)
    city          = models.CharField(max_length=120)
    postcode      = models.CharField(max_length=20)
    country       = models.CharField(max_length=60)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.full_name}"


class OrderItem(models.Model):
    """
    Each row is one line item inside an Order (one product + quantity).

    unit_price is stored at time of purchase so the order history stays
    accurate even if the product price changes later.

    product uses SET_NULL so if a product is deleted from the shop, old
    order records are not destroyed — just the product link becomes null.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")

    # Keep order history even if product is deleted later
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)

    # If the customer added to cart from My Designs, we store which design they chose
    design = models.ForeignKey(Design, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items")

    qty        = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        """Returns the cost for this line: qty × unit_price."""
        return self.qty * self.unit_price

    def __str__(self):
        return f"OrderItem #{self.id} (Order #{self.order.id})"
