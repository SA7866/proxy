from django.db import models
from django.conf import settings

# Create your models here.
class Product(models.Model):
    name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Order(models.Model):
    """
    Simple order model for checkout details.
    This stores delivery info + totals.
    Payment will be "simulated" later (safer for student projects).
    """
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PAID", "Paid (Simulated)"),
        ("SHIPPED", "Shipped"),
    ]

    # Optional: if user is logged in, link the order to them
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

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
    We store product + qty + price at time of purchase.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    qty = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.qty * self.unit_price