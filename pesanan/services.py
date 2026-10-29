"""Transaction boundary for carts, checkout and transitions, including SQLite.

No correctness assumption relies on select_for_update. Conditional writes and
unique constraints arbitrate claims; SQLite lock contention retries the WHOLE
transaction, never an individual statement in a partially executed checkout.
"""
import hashlib
import json
import time
from collections import defaultdict
from decimal import Decimal
from functools import wraps

from django.core import signing
from django.db import IntegrityError, OperationalError, connection, transaction
from django.db.models import F
from django.utils import timezone

from listing.models import Product
from .models import CartItem, CheckoutAttempt, Order, OrderItem
from .validation import DomainError

SHIPPING = Decimal("15000.00")
QUOTE_SALT = "pesanan.checkout.quote.v1"


def database_operation(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        for attempt in range(6):
            try:
                return func(*args, **kwargs)
            except OperationalError as exc:
                locked = connection.vendor == "sqlite" and any(word in str(exc).lower() for word in ("locked", "busy"))
                if not locked:
                    raise
                if attempt == 5:
                    raise DomainError("database_busy", "Transaksi lain sedang berjalan. Ulangi dengan kunci percobaan yang sama.", 409) from exc
                time.sleep(0.02 * (2**attempt))
            except IntegrityError as exc:
                raise DomainError("transaction_conflict", "Produk atau pesanan berubah. Muat ulang dan coba lagi.", 409) from exc
    return wrapped


def selected_products(user_id, ids):
    items = list(CartItem.objects.filter(user_id=user_id, product_id__in=ids)
                 .select_related("product__seller__profile").prefetch_related("product__images"))
    if {item.product_id for item in items} != set(ids):
        raise DomainError("not_in_cart", "Semua produk harus masih berada di keranjang Anda.", 409)
    products = sorted((item.product for item in items), key=lambda p: p.pk)
    claimed = set(OrderItem.objects.filter(product_id__in=ids, is_claimed=True).values_list("product_id", flat=True))
    for p in products:
        if p.seller_id == user_id:
            raise DomainError("own_product", "Tidak dapat membeli produk sendiri.", 409)
        if p.status != "active" or not getattr(getattr(p.seller, "profile", None), "is_seller", False) or p.pk in claimed or p.price <= 0:
            raise DomainError("unavailable", "Ada produk yang sudah tidak tersedia.", 409)
    return products


def quote_payload(user_id, products):
    return {"user_id": user_id, "shipping": str(SHIPPING), "items": [
        {"id": p.pk, "seller_id": p.seller_id, "price": str(p.price)} for p in products
    ]}


def quote(user_id, ids):
    products = selected_products(user_id, ids)
    payload = quote_payload(user_id, products)
    groups = defaultdict(list)
    for p in products:
        groups[p.seller_id].append(p)
    sellers = []
    for seller_id, items in sorted(groups.items()):
        subtotal = sum((p.price for p in items), Decimal("0.00"))
        sellers.append({"seller_id": seller_id, "product_ids": [p.pk for p in items],
                        "subtotal": str(subtotal), "shipping_cost": str(SHIPPING), "total": str(subtotal + SHIPPING)})
    return {**payload, "groups": sellers, "total": str(sum((p.price for p in products), SHIPPING * len(groups))),
            "quote_token": signing.dumps(payload, salt=QUOTE_SALT), "expires_in": 1800, "simulation": True}


@database_operation
def add_to_cart(user_id, product_id):
    with transaction.atomic():
        # First write obtains SQLite's writer slot, even if the cart is empty.
        CartItem.objects.filter(user_id=user_id, product_id=product_id).update(product_id=F("product_id"))
        p = Product.objects.select_related("seller__profile").filter(pk=product_id).first()
        if p is None:
            raise DomainError("not_found", "Produk tidak ditemukan.", 404)
        if p.seller_id == user_id:
            raise DomainError("own_product", "Tidak dapat menambahkan produk sendiri.")
        if p.status != "active" or not getattr(getattr(p.seller, "profile", None), "is_seller", False) or OrderItem.objects.filter(product=p, is_claimed=True).exists() or p.price <= 0:
            raise DomainError("unavailable", "Produk tidak tersedia.", 409)
        item, _ = CartItem.objects.get_or_create(user_id=user_id, product=p)
        return item.pk


@database_operation
def remove_from_cart(user_id, product_id):
    CartItem.objects.filter(user_id=user_id, product_id=product_id).delete()


def serialize_order(order):
    return {"id": order.pk, "buyer_id": order.buyer_id, "seller_id": order.seller_id,
            "status": order.status, "status_display": order.get_status_display(),
            "payment_method": order.payment_method, "payment_status": order.payment_status,
            "payment_display": order.get_payment_status_display(), "simulation": True,
            "recipient_name": order.recipient_name, "phone": order.phone, "address": order.address,
            "subtotal": str(order.subtotal), "shipping_cost": str(order.shipping_cost), "total": str(order.total),
            "items": [{"product_id": i.product_id, "name": i.product_name, "brand": i.brand,
                       "description": i.description, "category": i.category, "size": i.size,
                       "condition": i.condition, "image_url": i.image_url, "price": str(i.price)} for i in order.items.all()]}


@database_operation
def checkout(user_id, ids, data):
    fingerprint = hashlib.sha256(json.dumps({"ids": ids, **data}, sort_keys=True).encode()).hexdigest()
    with transaction.atomic():
        # A write BEFORE reads serializes SQLite writers. Unique key makes a
        # concurrent same-key retry observe the original committed attempt.
        CheckoutAttempt.objects.filter(user_id=user_id, key=data["idempotency_key"]).update(key=F("key"))
        attempt, created = CheckoutAttempt.objects.get_or_create(
            user_id=user_id, key=data["idempotency_key"], defaults={"fingerprint": fingerprint})
        if not created:
            if attempt.fingerprint != fingerprint:
                raise DomainError("idempotency_conflict", "Kunci percobaan sudah digunakan untuk permintaan berbeda.", 409)
            return {"orders": [serialize_order(o) for o in attempt.orders.prefetch_related("items")], "replayed": True}
        try:
            confirmed = signing.loads(data["quote_token"], salt=QUOTE_SALT, max_age=1800)
        except signing.BadSignature as exc:
            raise DomainError("quote_invalid", "Ringkasan tidak valid atau kedaluwarsa. Minta ringkasan dan konfirmasi ulang.", 409) from exc
        products = selected_products(user_id, ids)
        if confirmed != quote_payload(user_id, products):
            raise DomainError("quote_changed", "Harga atau isi ringkasan berubah. Minta ringkasan dan konfirmasi ulang.", 409)
        groups = defaultdict(list)
        for p in products:
            # The UPDATE is also the arbitration point on databases with row locks.
            claimed = Product.objects.filter(pk=p.pk, status="active", price=p.price,
                                             seller_id=p.seller_id, seller__profile__is_seller=True).exclude(
                order_items__is_claimed=True).update(status="sold", updated_at=timezone.now())
            if claimed != 1:
                raise DomainError("product_conflict", "Produk baru saja berubah atau dibeli pengguna lain.", 409)
            groups[p.seller_id].append(p)
        orders = []
        for seller_id, products in sorted(groups.items()):
            subtotal = sum((p.price for p in products), Decimal("0.00"))
            order = Order.objects.create(attempt=attempt, buyer_id=user_id, seller_id=seller_id,
                recipient_name=data["recipient_name"], phone=data["phone"], address=data["address"],
                subtotal=subtotal, shipping_cost=SHIPPING, total=subtotal + SHIPPING,
                payment_method=data["payment_method"], payment_status=Order.PaymentStatus.UNPAID if data["payment_method"] == "cod" else Order.PaymentStatus.PAID)
            for p in products:
                image = next(iter(p.images.all()), None)
                OrderItem.objects.create(order=order, product=p, product_name=p.name, brand=p.brand,
                    description=p.description, category=p.category, size=p.size, condition=p.condition,
                    image_url=image.image.url if image else "", price=p.price)
            orders.append(order)
        CartItem.objects.filter(user_id=user_id, product_id__in=ids).delete()
        return {"orders": [serialize_order(o) for o in orders], "replayed": False}


@database_operation
def transition(user_id, order_id, action):
    with transaction.atomic():
        # UPDATE predicates combine actor + previous state. Ship and cancel
        # compete for processing; exactly one can change it.
        rules = {"ship": ("seller_id", Order.Status.PROCESSING, Order.Status.SHIPPED),
                 "complete": ("buyer_id", Order.Status.SHIPPED, Order.Status.COMPLETED),
                 "cancel": ("buyer_id", Order.Status.PROCESSING, Order.Status.CANCELLED)}
        actor, previous, target = rules[action]
        matched = Order.objects.filter(pk=order_id, **{actor: user_id}, status=previous).update(status=target, updated_at=timezone.now())
        if matched != 1:
            if not Order.objects.filter(pk=order_id, **{actor: user_id}).exists():
                raise DomainError("not_found", "Pesanan tidak ditemukan atau aksi tidak diizinkan.", 404)
            raise DomainError("status_conflict", "Status pesanan sudah berubah; aksi tidak dapat dilakukan.", 409)
        order = Order.objects.get(pk=order_id)
        if action == "cancel":
            # Only this order's still-live claims may be released, never another
            # transaction's products or already released historical items.
            ids = list(order.items.filter(is_claimed=True).values_list("product_id", flat=True))
            Product.objects.filter(pk__in=ids, status="sold", order_items__order=order,
                                   order_items__is_claimed=True).update(status="active", updated_at=timezone.now())
            order.items.filter(is_claimed=True).update(is_claimed=False)
            order.payment_status = Order.PaymentStatus.REFUNDED if order.payment_status == Order.PaymentStatus.PAID else Order.PaymentStatus.VOID
        elif action == "complete" and order.payment_method == Order.PaymentMethod.COD:
            order.payment_status = Order.PaymentStatus.PAID
        order.save(update_fields=["payment_status"])
        return serialize_order(order)
