from django.db import models
from django.conf import settings


class Product(models.Model):
    """
    Product in the shop (e.g. T-shirt, hoodie).
    - image = normal product image for shop display
    - template_image = transparent PNG used inside the customiser canvas
    - print_* = printable area (box) inside the template image
    """
    name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField(blank=True)

    # Normal product image for shop page
    image = models.ImageField(upload_to="products/", blank=True, null=True)

    # Transparent PNG used for the customiser (important)
    template_image = models.ImageField(upload_to="templates/", blank=True, null=True)

    # Printable area inside template image (pixels)
    print_x = models.IntegerField(default=150)
    print_y = models.IntegerField(default=200)
    print_w = models.IntegerField(default=300)
    print_h = models.IntegerField(default=400)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Design(models.Model):
    """
    Saved custom design made by a user for a product.
    - design_data stores the design JSON (text, positions, colours, etc.)
    - preview stores a PNG screenshot so cart/order pages can show it easily
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="designs"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="designs"
    )

    design_data = models.TextField()
    preview = models.ImageField(upload_to="design_previews/", blank=True, null=True)

    # size chosen (S/M/L/XL)
    size = models.CharField(max_length=10, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Design #{self.id} - {self.product.name}"


class Order(models.Model):
    """
    Simple order model for checkout details.
    Stores delivery info + totals.
    Payment is simulated (safe for student project).
    """
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PAID", "Paid (Simulated)"),
        ("SHIPPED", "Shipped"),
    ]

    # Link order to a user if logged in
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    full_name = models.CharField(max_length=120)
    email = models.EmailField()

    address_line1 = models.CharField(max_length=200)
    city = models.CharField(max_length=120)
    postcode = models.CharField(max_length=20)
    country = models.CharField(max_length=60)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.full_name}"


class OrderItem(models.Model):
    """
    Each row is one item in an order.
    Stores product + qty + unit_price at time of purchase.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")

    # If product gets deleted later, we keep order history by setting NULL
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)

    qty = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.qty * self.unit_price

    def __str__(self):
        return f"OrderItem #{self.id} (Order #{self.order.id})"
