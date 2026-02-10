from django.shortcuts import render
from .models import Product

def shop(request):
    products = Product.objects.all().order_by("-created_at")
    return render(request, "store/shop.html", {"products": products})
