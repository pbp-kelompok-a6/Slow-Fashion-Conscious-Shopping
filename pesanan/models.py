from django.conf import settings
from django.db import models
from django.db.models import Q


class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey("listing.Product", on_delete=models.CASCADE, related_name="cart_items")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="cart_user_product_unique")]
        ordering = ["pk"]


class CheckoutAttempt(models.Model):
    """Only committed together with its orders; a failed attempt leaves no record."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="checkout_attempts")
    key = models.CharField(max_length=80)
    fingerprint = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "key"], name="checkout_user_key_unique")]


class Order(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "processing", "Diproses"
        SHIPPED = "shipped", "Dikirim"
        COMPLETED = "completed", "Selesai"
        CANCELLED = "cancelled", "Dibatalkan"

    class PaymentMethod(models.TextChoices):
        TRANSFER = "transfer", "Transfer (simulasi)"
        EWALLET = "ewallet", "E-wallet (simulasi)"
        COD = "cod", "COD (simulasi)"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Belum dibayar"
        PAID = "paid_simulated", "Dibayar (simulasi)"
        REFUNDED = "refunded_simulated", "Dikembalikan (simulasi)"
        VOID = "void", "Dibatalkan tanpa pembayaran"

    attempt = models.ForeignKey(CheckoutAttempt, on_delete=models.PROTECT, related_name="orders")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="purchases")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales")
    recipient_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=25)
    address = models.CharField(max_length=1000)
    subtotal = models.DecimalField(max_digits=16, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=16, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PROCESSING)
    payment_method = models.CharField(max_length=12, choices=PaymentMethod.choices)
    payment_status = models.CharField(max_length=24, choices=PaymentStatus.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(fields=["attempt", "seller"], name="checkout_one_order_per_seller"),
            models.CheckConstraint(condition=~Q(buyer=models.F("seller")), name="order_not_own_seller"),
            models.CheckConstraint(condition=Q(total=models.F("subtotal") + models.F("shipping_cost")), name="order_total_matches"),
            models.CheckConstraint(condition=Q(subtotal__gte=0, shipping_cost__gte=0), name="order_nonnegative_amounts"),
            models.CheckConstraint(condition=Q(status__in=["processing", "shipped", "completed", "cancelled"]), name="order_valid_status"),
        ]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="items")
    product = models.ForeignKey("listing.Product", on_delete=models.PROTECT, related_name="order_items")
    # Remains true after completion: a preloved listing cannot be sold twice.
    is_claimed = models.BooleanField(default=True)
    product_name = models.CharField(max_length=150)
    brand = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    category = models.CharField(max_length=30)
    size = models.CharField(max_length=30)
    condition = models.CharField(max_length=20)
    image_url = models.CharField(max_length=1000, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(fields=["order", "product"], name="order_product_unique"),
            models.UniqueConstraint(fields=["product"], condition=Q(is_claimed=True), name="one_live_claim_per_product"),
            models.CheckConstraint(condition=Q(price__gt=0), name="order_item_positive_price"),
        ]
