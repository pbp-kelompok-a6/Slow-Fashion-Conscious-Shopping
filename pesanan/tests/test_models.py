from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from pesanan.models import CartItem, CheckoutAttempt, Order, OrderItem
from pesanan.services import checkout
from .common import Fixtures


class ModelTests(Fixtures, TestCase):
    def setUp(self):
        self.make_data()

    def test_cart_unique_and_history_protected(self):
        CartItem.objects.create(user=self.buyer, product=self.p)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItem.objects.create(user=self.buyer, product=self.p)
        checkout(self.buyer.pk, *self.payload())
        for instance in [self.buyer, self.seller, self.p, Order.objects.get(), CheckoutAttempt.objects.get()]:
            with self.subTest(model=type(instance).__name__), self.assertRaises(ProtectedError):
                instance.delete()

    def test_live_claim_unique_and_one_order_per_seller(self):
        checkout(self.buyer.pk, *self.payload())
        item = OrderItem.objects.get()
        attempt = CheckoutAttempt.objects.create(user=self.other, key="attempt-other", fingerprint="x" * 64)
        order = Order.objects.create(attempt=attempt, buyer=self.other, seller=self.seller,
                                     subtotal=item.price, shipping_cost=15000, total=item.price + 15000,
                                     payment_method="cod", payment_status="unpaid")
        item.pk = None
        item.order = order
        with self.assertRaises(IntegrityError), transaction.atomic():
            item.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            order.pk = None
            order.save()
