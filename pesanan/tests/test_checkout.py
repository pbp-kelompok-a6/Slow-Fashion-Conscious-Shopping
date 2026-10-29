from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from akun.models import Profile
from listing.models import Product
from pesanan.models import CartItem, CheckoutAttempt, Order, OrderItem
from pesanan.services import checkout
from pesanan.validation import DomainError
from .common import Fixtures


class CheckoutTests(Fixtures, TestCase):
    def setUp(self):
        self.make_data()
        self.client.force_login(self.buyer)

    def test_grouped_orders_shipping_snapshots_and_server_amounts(self):
        p3 = self.product(self.seller, "Third", "300.75")
        ids, data = self.payload([self.p, self.p2, p3], method="transfer")
        response = self.post("checkout", {**data, "product_ids": ids, "total": "0", "shipping_cost": "0"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Order.objects.count(), 2)
        self.assertEqual(OrderItem.objects.count(), 3)
        self.assertEqual(list(Order.objects.values_list("shipping_cost", flat=True)), [15000, 15000])
        self.assertEqual(str(Order.objects.get(seller=self.seller).total), "15401.00")
        self.assertFalse(CartItem.objects.filter(user=self.buyer).exists())
        self.assertEqual(Product.objects.filter(status="sold").count(), 3)
        self.p.name = "Changed"; self.p.price = 1; self.p.save()
        item = OrderItem.objects.get(product=self.p)
        self.assertEqual((item.product_name, str(item.price), item.description), ("Linen", "100.25", "Snapshot deskripsi"))
        self.assertEqual(Order.objects.first().payment_status, "paid_simulated")
        self.assertTrue(response.json()["simulation"])

    def test_idempotent_retry_and_conflicting_payload(self):
        ids, data = self.payload()
        first = checkout(self.buyer.pk, ids, data)
        retry = checkout(self.buyer.pk, ids, data)
        self.assertTrue(retry["replayed"])
        self.assertEqual(first["orders"], retry["orders"])
        self.assertEqual(Order.objects.count(), 1)
        with self.assertRaises(DomainError) as error:
            checkout(self.buyer.pk, ids, {**data, "address": "Alamat lain nomor 20"})
        self.assertEqual(error.exception.code, "idempotency_conflict")
        # Key scope is per user, not global.
        ids2, data2 = self.payload([self.p2], self.other)
        checkout(self.other.pk, ids2, data2)
        self.assertEqual(CheckoutAttempt.objects.count(), 2)

    def test_ids_validation_before_database(self):
        for ids in [None, [], {}, "1", [True], [1.2], [0], [-1], ["1e2"], ["01"], [""], ["x"], [self.p.pk, self.p.pk], [2**63], ["9" * 5000], list(range(1, 102))]:
            with self.subTest(ids=str(ids)[:70]):
                self.assertEqual(self.post("checkout_quote", {"product_ids": ids}).status_code, 400)
                self.assertEqual(self.post("checkout", {"product_ids": ids}).status_code, 400)
        self.assertEqual(self.post("checkout_quote", {"product_ids": [999999]}).status_code, 409)

    def test_outside_cart_and_user_quote_rejected(self):
        ids, data = self.payload()
        self.client.force_login(self.other)
        response = self.post("checkout", {**data, "product_ids": ids})
        self.assertEqual(response.json()["code"], "not_in_cart")
        CartItem.objects.create(user=self.other, product=self.p)
        response = self.post("checkout", {**data, "product_ids": ids})
        self.assertEqual(response.json()["code"], "quote_changed")
        self.assertFalse(Order.objects.exists())

    def test_price_change_requires_reconfirmation_even_same_total(self):
        ids, data = self.payload([self.p, self.p2])
        Product.objects.filter(pk=self.p.pk).update(price="101.25")
        Product.objects.filter(pk=self.p2.pk).update(price="199.50")
        response = self.post("checkout", {**data, "product_ids": ids})
        self.assertEqual(response.json()["code"], "quote_changed")
        self.assertFalse(CheckoutAttempt.objects.exists())
        self.assertEqual(CartItem.objects.count(), 2)
        ids, new_data = self.payload([self.p, self.p2])
        self.assertEqual(self.post("checkout", {**new_data, "product_ids": ids}).status_code, 200)

    def test_sold_inactive_and_own_at_checkout(self):
        ids, data = self.payload()
        for change, code in [(dict(status="sold"), "unavailable"), (dict(status="active", seller=self.buyer), "own_product")]:
            Product.objects.filter(pk=self.p.pk).update(**change)
            self.assertEqual(self.post("checkout", {**data, "product_ids": ids}).json()["code"], code)
        Product.objects.filter(pk=self.p.pk).update(seller=self.seller)
        Profile.objects.filter(user=self.seller).update(is_seller=False)
        self.assertEqual(self.post("checkout", {**data, "product_ids": ids}).json()["code"], "unavailable")
        self.assertFalse(Order.objects.exists())

    def test_late_failure_rolls_back_multi_item_multi_seller(self):
        ids, data = self.payload([self.p, self.p2])
        create = OrderItem.objects.create
        calls = []
        def fail_second(**kwargs):
            calls.append(kwargs)
            if len(calls) == 2:
                raise DomainError("injected_failure", "Failure after first order and snapshot", 409)
            return create(**kwargs)
        # Failure injection tests rollback only; concurrency tests use real DB writes.
        with patch.object(OrderItem.objects, "create", side_effect=fail_second):
            with self.assertRaises(DomainError):
                checkout(self.buyer.pk, ids, data)
        self.assertEqual(len(calls), 2)
        for model in [Order, OrderItem, CheckoutAttempt]:
            self.assertEqual(model.objects.count(), 0)
        self.assertEqual(Product.objects.filter(status="active").count(), 2)
        self.assertEqual(CartItem.objects.count(), 2)
        self.assertEqual(len(checkout(self.buyer.pk, ids, data)["orders"]), 2)

    def test_invalid_json_quote_address_method_and_csrf(self):
        ids, data = self.payload()
        for body in ["{bad", "[]"]:
            self.assertEqual(self.client.post(reverse("pesanan:checkout"), body, content_type="application/json").status_code, 400)
        for field, value in [("address", ""), ("phone", "abc"), ("payment_method", "gateway"), ("recipient_name", {}), ("idempotency_key", "a")]:
            self.assertEqual(self.post("checkout", {**data, "product_ids": ids, field: value}).status_code, 400)
        self.assertEqual(self.post("checkout", {**data, "product_ids": ids, "quote_token": "invalid"}).status_code, 409)
        secure = Client(enforce_csrf_checks=True); secure.force_login(self.buyer)
        self.assertEqual(self.post("checkout", {**data, "product_ids": ids}, client=secure).status_code, 403)
        self.assertEqual(self.post("checkout", {**data, "product_ids": ids}, client=Client()).status_code, 401)
        self.assertFalse(Order.objects.exists())

    def test_expired_quote_and_retry_after_expiry(self):
        import time
        from pesanan import services
        ids, data = self.payload()
        with patch("django.core.signing.time.time", return_value=time.time() + 1900):
            with self.assertRaises(DomainError) as error:
                checkout(self.buyer.pk, ids, data)
            self.assertEqual(error.exception.code, "quote_invalid")
        self.assertFalse(CheckoutAttempt.objects.exists())
        checkout(self.buyer.pk, ids, data)
        with patch("django.core.signing.time.time", return_value=time.time() + 1900):
            self.assertTrue(services.checkout(self.buyer.pk, ids, data)["replayed"])
