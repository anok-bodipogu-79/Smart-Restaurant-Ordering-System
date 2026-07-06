from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True, null=False, blank=False)
    icon = models.CharField(max_length=50, default="bi-journal", null=False, blank=False)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=100, null=False, blank=False)
    description = models.TextField(null=False, blank=False)
    price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=False,
        blank=False,
        validators=[MinValueValidator(Decimal("0.01"))]
    )
    is_vegetarian = models.BooleanField(default=False)
    is_spicy = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    image_url = models.URLField(blank=True, default="https://via.placeholder.com/300x200")

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} (${self.price})"


class Order(models.Model):
    STATUS_CHOICES = [
        ("RECEIVED", "Order Received"),
        ("PREPARING", "In Kitchen - Preparing"),
        ("READY", "Ready for Pickup / Delivery"),
        ("COMPLETED", "Completed"),
    ]

    customer_name = models.CharField(max_length=100, null=False, blank=False)
    customer_phone = models.CharField(max_length=15, null=False, blank=False)
    table_number = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)]
    )
    total_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="RECEIVED"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        order_id = self.id if self.id is not None else "Unsaved"
        return f"Order #{order_id} by {self.customer_name} ({self.get_status_display()})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(20)]
    )
    price_at_order = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )

    def __str__(self):
        item_name = self.menu_item.name if self.menu_item else "Unknown Item"
        return f"{self.quantity}x {item_name}"
