from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, connections, transaction
from django.db.models import F
from django.test import TransactionTestCase

from pesanan.guards import delete_account, delete_listing, set_listing_status
from pesanan.models import CartItem, CheckoutAttempt, Order, OrderItem
from pesanan.services import checkout, transition
from pesanan.validation import DomainError
from .common import Fixtures


class SQLiteConcurrencyTests(Fixtures, TransactionTestCase):
    """Two live DB connections, synchronized starts, real commits; no mock locks."""

    def setUp(self):
        name = str(connection.settings_dict["NAME"])
        if connection.vendor != "sqlite" or "memory" in name:
            self.skipTest("Run with --settings=pesanan.test_settings for real SQLite file concurrency")
        self.make_data()

    def race(self, left, right):
        barrier = Barrier(2)
        def worker(operation):
            close_old_connections()
            connection.ensure_connection()
            identity = id(connection.connection)
            try:
                barrier.wait(timeout=10)
                try:
                    result = ("ok", operation())
                except DomainError as exc:
                    result = ("error", exc.code)
                return identity, result
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker, op) for op in [left, right]]
            results = [future.result(timeout=30) for future in futures]
        self.assertNotEqual(results[0][0], results[1][0], "Must use independent database connections")
        return [result for _, result in results]

    def test_two_buyers_one_listing_exactly_one_checkout(self):
        ids, data = self.payload()
        ids2, data2 = self.payload(buyer=self.other)
        result = self.race(lambda: checkout(self.buyer.pk, ids, data), lambda: checkout(self.other.pk, ids2, data2))
        self.assertEqual(sorted(r[0] for r in result), ["error", "ok"])
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.filter(is_claimed=True).count(), 1)
        self.assertEqual(CheckoutAttempt.objects.count(), 1)
        self.assertEqual(CartItem.objects.count(), 1)
        self.p.refresh_from_db(); self.assertEqual(self.p.status, "sold")

    def test_same_key_simultaneous_retry_returns_one_result(self):
        ids, data = self.payload()
        result = self.race(lambda: checkout(self.buyer.pk, ids, data), lambda: checkout(self.buyer.pk, ids, data))
        self.assertEqual([r[0] for r in result], ["ok", "ok"])
        self.assertEqual(sorted(r[1]["replayed"] for r in result), [False, True])
        self.assertEqual(result[0][1]["orders"], result[1][1]["orders"])
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(CheckoutAttempt.objects.count(), 1)

    def test_overlapping_multi_seller_checkout_has_no_partial_winner(self):
        ids, data = self.payload([self.p, self.p2])
        ids2, data2 = self.payload([self.p, self.p2], buyer=self.other)
        result = self.race(lambda: checkout(self.buyer.pk, ids, data), lambda: checkout(self.other.pk, ids2, data2))
        self.assertEqual(sorted(r[0] for r in result), ["error", "ok"])
        self.assertEqual(Order.objects.count(), 2)
        self.assertEqual(len(set(Order.objects.values_list("buyer_id", flat=True))), 1)
        self.assertEqual(OrderItem.objects.filter(is_claimed=True).count(), 2)
        self.assertEqual(CartItem.objects.count(), 2)

    def test_cancel_competes_with_shipping(self):
        order_id = checkout(self.buyer.pk, *self.payload())["orders"][0]["id"]
        result = self.race(lambda: transition(self.buyer.pk, order_id, "cancel"), lambda: transition(self.seller.pk, order_id, "ship"))
        self.assertEqual(sorted(r[0] for r in result), ["error", "ok"])
        order = Order.objects.get(pk=order_id)
        self.p.refresh_from_db()
        if order.status == "cancelled":
            self.assertFalse(order.items.get().is_claimed)
            self.assertEqual(self.p.status, "active")
        else:
            self.assertEqual(order.status, "shipped")
            self.assertTrue(order.items.get().is_claimed)
            self.assertEqual(self.p.status, "sold")

    def test_listing_activation_cannot_reopen_concurrent_checkout(self):
        ids, data = self.payload()
        result = self.race(lambda: checkout(self.buyer.pk, ids, data), lambda: set_listing_status(self.seller.pk, self.p.pk, "active"))
        self.assertEqual(result[0][0], "ok")
        self.assertEqual(result[1][0], "error")
        self.p.refresh_from_db(); self.assertEqual(self.p.status, "sold")
        self.assertTrue(OrderItem.objects.get().is_claimed)

    def test_account_deletion_competes_with_checkout_without_losing_history(self):
        ids, data = self.payload()
        result = self.race(lambda: checkout(self.buyer.pk, ids, data), lambda: delete_account(self.buyer.pk))
        self.assertEqual(sorted(r[0] for r in result), ["error", "ok"])
        if Order.objects.exists():
            self.assertTrue(get_user_model().objects.filter(pk=self.buyer.pk).exists())
            self.assertEqual(OrderItem.objects.count(), 1)
        else:
            self.assertFalse(get_user_model().objects.filter(pk=self.buyer.pk).exists())
            self.assertFalse(CheckoutAttempt.objects.exists())
            self.p.refresh_from_db(); self.assertEqual(self.p.status, "active")

    def test_listing_deletion_competes_with_checkout(self):
        ids, data = self.payload()
        result = self.race(lambda: checkout(self.buyer.pk, ids, data), lambda: delete_listing(self.seller.pk, self.p.pk))
        self.assertEqual(sorted(r[0] for r in result), ["error", "ok"])
        if Order.objects.exists():
            self.assertTrue(OrderItem.objects.get().is_claimed)
            self.assertTrue(type(self.p).objects.filter(pk=self.p.pk, status="sold").exists())
        else:
            self.assertFalse(type(self.p).objects.filter(pk=self.p.pk).exists())
            self.assertFalse(CheckoutAttempt.objects.exists())

    def test_real_sqlite_contention_returns_retryable_conflict(self):
        ids, data = self.payload()
        def blocked_checkout():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("PRAGMA busy_timeout = 1")
                try:
                    checkout(self.buyer.pk, ids, data)
                except DomainError as exc:
                    return exc.code
                return "unexpected success"
            finally:
                connections.close_all()
        with transaction.atomic():
            # Hold a REAL SQLite RESERVED writer lock until the other connection
            # exhausts its bounded retries. No lock/SQL mocking is involved.
            type(self.p).objects.filter(pk=self.p.pk).update(status=F("status"))
            with ThreadPoolExecutor(max_workers=1) as executor:
                code = executor.submit(blocked_checkout).result(timeout=10)
            self.assertEqual(code, "database_busy")
        self.assertFalse(Order.objects.exists())
        self.assertFalse(CheckoutAttempt.objects.exists())
        self.assertFalse(checkout(self.buyer.pk, ids, data)["replayed"])
