from django.test import Client, TestCase
from django.urls import reverse

from akun.models import Profile
from pesanan.models import CartItem
from .common import Fixtures


class CartTests(Fixtures, TestCase):
    def setUp(self):
        self.make_data()
        self.client.force_login(self.buyer)

    def test_auth_method_and_csrf(self):
        anonymous = Client()
        for name in ["cart", "orders"]:
            self.assertEqual(anonymous.get(reverse("pesanan:" + name)).status_code, 401)
        self.assertEqual(self.post("cart_add", {"product_id": self.p.pk}, client=anonymous).status_code, 401)
        self.assertEqual(self.client.get(reverse("pesanan:cart_add")).status_code, 405)
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.buyer)
        self.assertEqual(self.post("cart_add", {"product_id": self.p.pk}, client=secure).status_code, 403)
        secure.get(reverse("pesanan:cart"))
        response = secure.post(reverse("pesanan:cart_add"), {"product_id": self.p.pk}, content_type="application/json", HTTP_X_CSRFTOKEN=secure.cookies["csrftoken"].value)
        self.assertEqual(response.status_code, 200)

    def test_explicit_single_unit_and_user_isolation(self):
        for _ in range(2):
            self.assertEqual(self.post("cart_add", {"product_id": self.p.pk}).status_code, 200)
        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(self.post("cart_add", {"product_id": self.p.pk, "quantity": 2}).status_code, 400)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("pesanan:cart")).json()["count"], 0)
        self.post("cart_remove", {"product_id": self.p.pk})
        self.assertEqual(CartItem.objects.count(), 1)

    def test_reject_own_sold_inactive_missing(self):
        own = self.product(self.buyer, "Own", "10.00")
        self.assertEqual(self.post("cart_add", {"product_id": own.pk}).json()["code"], "own_product")
        self.p.status = "sold"; self.p.save()
        self.assertEqual(self.post("cart_add", {"product_id": self.p.pk}).status_code, 409)
        Profile.objects.filter(user=self.seller2).update(is_seller=False)
        self.assertEqual(self.post("cart_add", {"product_id": self.p2.pk}).status_code, 409)
        self.assertEqual(self.post("cart_add", {"product_id": 99999}).status_code, 404)

    def test_unavailable_cart_retained_and_removable(self):
        self.post("cart_add", {"product_id": self.p.pk})
        self.p.status = "sold"; self.p.save()
        data = self.client.get(reverse("pesanan:cart")).json()
        self.assertFalse(data["items"][0]["available"])
        self.assertEqual(len(data["groups"]), 1)
        self.post("cart_remove", {"product_id": self.p.pk})
        self.assertFalse(CartItem.objects.exists())
