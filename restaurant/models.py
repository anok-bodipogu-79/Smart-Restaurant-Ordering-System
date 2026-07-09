import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

def validate_image_file(file):
    # Enforce size limit (5MB)
    if file.size > 5 * 1024 * 1024:
        raise ValidationError("Image size exceeds 5MB limit.")
    # Verify it is an image and check format
    try:
        from PIL import Image as PILImage
        pos = file.tell()
        img = PILImage.open(file)
        fmt = img.format.lower() if img.format else ""
        img.verify()
        file.seek(pos)
    except Exception:
        raise ValidationError("Invalid image file.")

    if fmt not in ['jpeg', 'jpg', 'png', 'webp']:
        raise ValidationError("Unsupported format. Only JPEG, PNG, and WebP are allowed.")


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
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True, validators=[validate_image_file])

    @property
    def display_image_url(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        return "https://via.placeholder.com/300x200"

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
        ("CANCELLED", "Cancelled"),
    ]

    tracking_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    customer_name = models.CharField(max_length=100, null=False, blank=False)
    customer_phone = models.CharField(max_length=15, null=False, blank=False)
    table_number = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)]
    )
    subtotal_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    tax_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0500"),
        validators=[MinValueValidator(Decimal("0.0000"))]
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
        default="RECEIVED",
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    estimated_preparation_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(5), MaxValueValidator(180)]
    )
    priority = models.CharField(
        max_length=10,
        choices=[("NORMAL", "Normal"), ("PRIORITY", "Priority"), ("URGENT", "Urgent")],
        default="NORMAL",
        db_index=True
    )
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)

    @property
    def is_delayed(self):
        if self.estimated_preparation_minutes and self.status not in ["COMPLETED", "CANCELLED"]:
            from django.utils import timezone
            import datetime
            elapsed = timezone.now() - self.created_at
            return elapsed > datetime.timedelta(minutes=self.estimated_preparation_minutes)
        return False

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        order_id = self.id if self.id is not None else "Unsaved"
        return f"Order #{order_id} by {self.customer_name} ({self.get_status_display()})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(20)]
    )
    price_at_order = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )
    item_name_at_order = models.CharField(max_length=100, default="", blank=True)
    category_name_at_order = models.CharField(max_length=100, null=True, blank=True)
    special_instructions = models.CharField(max_length=250, default="", blank=True)

    @property
    def total_price(self):
        return (self.price_at_order * self.quantity).quantize(Decimal("0.01"))

    def __str__(self):
        name = self.item_name_at_order
        if not name and self.menu_item:
            name = self.menu_item.name
        if not name:
            name = "Unknown Item"
        return f"{self.quantity}x {name}"


class AuditLog(models.Model):
    actor = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100)
    target_id = models.CharField(max_length=50, blank=True, default="")
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        actor_name = self.actor.username if self.actor else "System"
        return f"{self.timestamp} - {actor_name}: {self.action} on {self.target_type}"
