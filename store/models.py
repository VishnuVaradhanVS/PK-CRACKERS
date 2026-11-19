import uuid
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

class Product(models.Model):
    name = models.CharField(max_length=140)
    category = models.CharField(max_length=80, blank=True, default="", db_index=True)
    description = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to="products/", blank=True)
    image_url = models.URLField(blank=True, help_text="Optional external image URL; uploaded image takes precedence.")
    video_url = models.URLField(blank=True)  # Legacy field retained for existing database data; no longer used by the storefront.
    video_file = models.FileField(upload_to="product_videos/", blank=True)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class CartItem(models.Model):
    """A customer's cart stored in the database so it survives sessions/devices."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="unique_user_cart_product")]
        ordering = ["updated_at"]

    def __str__(self):
        return f"{self.user} · {self.product} × {self.quantity}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        PROCESSING = "PROCESSING", "Processing"
        DISPATCHED = "DISPATCHED", "Dispatched"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    username = models.CharField(max_length=120)
    contact = models.CharField(max_length=40)
    address = models.TextField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Payment pending"
        RECEIVED = "RECEIVED", "Payment received"
        REFUNDED = "REFUNDED", "Refunded"
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    payment_note = models.CharField(max_length=250, blank=True, help_text="Internal admin note; not shown to customers.")
    whatsapp_opt_in = models.BooleanField(default=False, help_text="Customer agreed to receive transactional WhatsApp updates for this order.")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.pk}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    product_name = models.CharField(max_length=140)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"


class StorePaymentSettings(models.Model):
    """Singleton-like settings for the manual payment instructions shown at checkout."""
    instructions = models.TextField(
        blank=True,
        default="Please scan the QR code to pay. Include your order number in the payment note and share the payment confirmation with our team.",
        help_text="Shown to customers during checkout. Do not include confidential account credentials.",
    )
    qr_code = models.ImageField(upload_to="payment_qr/", blank=True)
    notification_emails = models.TextField(
        blank=True,
        help_text="Comma-, semicolon-, or line-separated email addresses notified when a new order is placed.",
    )
    whatsapp_admin_numbers = models.TextField(
        blank=True,
        help_text="Admin WhatsApp numbers with country code, separated by commas, semicolons, or new lines. Add only recipients who have opted in.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Store payment settings"
        verbose_name_plural = "Store payment settings"

    def __str__(self):
        return "Checkout payment instructions"

    @classmethod
    def current(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings


class EmailVerificationOTP(models.Model):
    """Short-lived, single-use email verification code for customer signup."""
    email = models.EmailField(unique=True)
    code_hash = models.CharField(max_length=256)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Email verification code"
        verbose_name_plural = "Email verification codes"

    def __str__(self):
        return f"Email verification for {self.email}"
