from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from listing.models import Product
from .services import database_operation
from .validation import DomainError


@database_operation
def set_listing_status(user_id, product_id, status):
    with transaction.atomic():
        changed = Product.objects.filter(pk=product_id, seller_id=user_id).exclude(
            order_items__is_claimed=True).exclude(
            order_items__order__status__in=["processing", "shipped", "completed"]
        ).exclude(status=status).update(status=status, updated_at=timezone.now())
        if changed != 1:
            raise DomainError("listing_status_conflict", "Status tidak berubah: produk sudah berstatus tersebut atau terikat pesanan.", 409)


@database_operation
def delete_listing(user_id, product_id):
    with transaction.atomic():
        Product.objects.filter(pk=product_id, seller_id=user_id).update(status=F("status"))
        try:
            Product.objects.filter(pk=product_id, seller_id=user_id).delete()
        except ProtectedError as exc:
            raise DomainError("order_history_exists", "Produk dengan riwayat pesanan tidak dapat dihapus.", 409) from exc


@database_operation
def delete_account(user_id):
    with transaction.atomic():
        # Serialize with SQLite checkout before the deletion collector reads.
        User = get_user_model()
        User.objects.filter(pk=user_id).update(username=F("username"))
        try:
            User.objects.get(pk=user_id).delete()
        except ProtectedError as exc:
            raise DomainError("order_history_exists", "Akun dengan riwayat pesanan tidak dapat dihapus, termasuk pesanan yang dibatalkan.", 409) from exc
