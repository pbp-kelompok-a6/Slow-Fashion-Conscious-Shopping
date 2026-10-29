from django.test import TestCase
from django.urls import reverse

from pesanan.models import Order, OrderItem
from pesanan.services import checkout, transition
from pesanan.validation import DomainError
from .common import Fixtures


class TransitionTests(Fixtures, TestCase):
    def setUp(self):
        self.make_data()
        self.order_id = checkout(self.buyer.pk, *self.payload())["orders"][0]["id"]

    def test_cod_unpaid_until_completed_and_actor_enforcement(self):
        order = Order.objects.get(pk=self.order_id)
        self.assertEqual(order.payment_status, "unpaid")
        for actor, action in [(self.other, "ship"), (self.buyer, "ship"), (self.seller, "complete"), (self.seller, "cancel")]:
            self.client.force_login(actor)
            self.assertEqual(self.post(action, args=[order.pk]).status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("pesanan:order_detail", args=[order.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("pesanan:orders")).json()["orders"], [])
        shipped = transition(self.seller.pk, order.pk, "ship")
        self.assertEqual(shipped["payment_status"], "unpaid")
        with self.assertRaises(DomainError):
            transition(self.buyer.pk, order.pk, "cancel")
        completed = transition(self.buyer.pk, order.pk, "complete")
        self.assertEqual((completed["status"], completed["payment_status"]), ("completed", "paid_simulated"))
        self.assertTrue(OrderItem.objects.get().is_claimed)

    def test_cancel_releases_only_its_claim_and_cannot_reopen_resale(self):
        result = transition(self.buyer.pk, self.order_id, "cancel")
        self.assertEqual(result["payment_status"], "void")
        self.p.refresh_from_db(); self.assertEqual(self.p.status, "active")
        ids, data = self.payload(buyer=self.other, key="resale-attempt")
        new_order = checkout(self.other.pk, ids, data)["orders"][0]["id"]
        with self.assertRaises(DomainError):
            transition(self.buyer.pk, self.order_id, "cancel")
        self.p.refresh_from_db(); self.assertEqual(self.p.status, "sold")
        self.assertEqual(OrderItem.objects.get(product=self.p, is_claimed=True).order_id, new_order)
        with self.assertRaises(DomainError):
            transition(self.seller.pk, self.order_id, "ship")

    def test_paid_simulation_cancel_refund(self):
        ids, data = self.payload([self.p2], key="ewallet-attempt", method="ewallet")
        order_id = checkout(self.buyer.pk, ids, data)["orders"][0]["id"]
        self.assertEqual(transition(self.buyer.pk, order_id, "cancel")["payment_status"], "refunded_simulated")
