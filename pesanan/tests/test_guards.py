from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from listing.forms import ProductForm
from listing.models import Product
from pesanan.models import Order
from pesanan.services import checkout, transition
from .common import Fixtures


class GuardTests(Fixtures, TestCase):
    def setUp(self):
        self.make_data()

    def test_seller_cannot_activate_ordered_listing_or_delete_history(self):
        order = checkout(self.buyer.pk, *self.payload())["orders"][0]
        self.client.force_login(self.seller)
        activate = reverse("listing:product_mark_active", args=[self.p.pk])
        self.assertEqual(self.client.post(activate).status_code, 409)
        self.assertEqual(self.client.post(reverse("listing:product_delete", args=[self.p.pk])).status_code, 409)
        transition(self.seller.pk, order["id"], "ship")
        transition(self.buyer.pk, order["id"], "complete")
        self.assertEqual(self.client.post(activate).status_code, 409)
        self.p.refresh_from_db(); self.assertEqual(self.p.status, "sold")

    def test_listing_edit_does_not_restore_stale_status(self):
        ids, data = self.payload()
        self.client.force_login(self.seller)
        post = {name: getattr(self.p, name) for name in ProductForm.Meta.fields}
        post.update({"name": "Updated name", "images-TOTAL_FORMS": "0", "images-INITIAL_FORMS": "0", "images-MIN_NUM_FORMS": "0", "images-MAX_NUM_FORMS": "5"})
        # Checkout occurs after the view fetched a Product, before it persists
        # its bound form. This injection verifies the stale-model write guard.
        from unittest.mock import patch
        original = ProductForm.is_valid
        def validate(form):
            result = original(form)
            checkout(self.buyer.pk, ids, data)
            return result
        with patch.object(ProductForm, "is_valid", validate):
            self.assertEqual(self.client.post(reverse("listing:product_edit", args=[self.p.pk]), post).status_code, 302)
        self.p.refresh_from_db()
        self.assertEqual((self.p.name, self.p.status), ("Updated name", "sold"))

    def test_account_history_blocks_endpoint_and_direct_delete_even_cancelled(self):
        order = checkout(self.buyer.pk, *self.payload())["orders"][0]
        transition(self.buyer.pk, order["id"], "cancel")
        for user in [self.buyer, self.seller]:
            self.client.force_login(user)
            response = self.client.post(reverse("akun:hapus_akun"), HTTP_ACCEPT="application/json")
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()["code"], "order_history_exists")
            html = self.client.post(reverse("akun:hapus_akun"))
            self.assertContains(html, "riwayat pesanan", status_code=409)
            with self.assertRaises(ProtectedError):
                user.delete()
        self.assertEqual(Order.objects.count(), 1)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(reverse("akun:hapus_akun")).status_code, 302)
