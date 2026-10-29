from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from akun.models import Profile
from listing.models import Product
from pesanan.models import CartItem, Order
from pesanan.services import checkout, transition
from product_catalog.models import WishlistItem
from .common import Fixtures


class PageTests(Fixtures, TestCase):
    def setUp(self):
        self.make_data()
        self.client.force_login(self.buyer)

    def test_all_pages_and_json_fragments(self):
        ids, data = self.payload([self.p, self.p2])
        response = self.client.get(reverse("pesanan:checkout_page"), {"product_ids": ids})
        self.assertContains(response, "Rp100,25")
        self.assertContains(response, "Rp200,50")
        self.assertContains(response, "Total 2 toko")
        self.assertNotContains(response, data["address"])
        result = checkout(self.buyer.pk, ids, data)
        pk = result["orders"][0]["id"]
        for name, args in [("cart_page", None), ("purchases_page", None), ("sales_page", None), ("order_page", [pk]), ("success_page", [pk])]:
            url = reverse("pesanan:" + name, args=args)
            self.assertEqual(self.client.get(url).status_code, 200)
            fragment = self.client.get(url, HTTP_ACCEPT="application/json").json()
            self.assertTrue(fragment["success"])
            self.assertIn('data-ps-page=', fragment["html"])
            self.assertNotIn('<script', fragment["html"])
        self.assertContains(self.client.get(reverse("pesanan:success_page", args=[pk])), "Rp30.300,75")

    def test_login_next_safe_post_and_external_rejection(self):
        self.buyer.set_password("Phase5-secure-password!"); self.buyer.save()
        self.client.logout()
        target = reverse("pesanan:checkout_page") + "?product_ids=1&product_ids=2"
        response = self.client.get(target)
        self.assertEqual(response.status_code, 302)
        login = reverse("akun:login")
        page = self.client.get(login, {"next": target})
        self.assertContains(page, 'name="next"')
        credentials = {"username": self.buyer.username, "password": "Phase5-secure-password!"}
        self.assertRedirects(self.client.post(login, {**credentials, "next": target}), target, fetch_redirect_response=False)
        self.client.logout()
        self.assertRedirects(self.client.post(login, {**credentials, "next": "https://evil.invalid/"}), "/", fetch_redirect_response=False)
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(reverse("akun:logout")).status_code, 405)

    def test_badge_means_purchasable_not_total_cart(self):
        self.payload([self.p, self.p2])
        Product.objects.filter(pk=self.p2.pk).update(status="sold")
        response = self.client.get(reverse("pesanan:cart_page"))
        self.assertEqual(response.context["cart_purchasable_count"], 1)
        self.assertContains(response, 'aria-label="1 barang bisa dibeli"')
        self.assertEqual(self.client.get(reverse("pesanan:cart")).json()["count"], 2)  # Phase 4 count unchanged.
        Profile.objects.filter(user=self.seller).update(is_seller=False)
        response = self.client.get(reverse("pesanan:cart_page"))
        self.assertEqual(response.context["cart_purchasable_count"], 0)
        self.assertContains(response, "Seller nonaktif")

    def test_cart_slot_states_and_ajax_wishlist(self):
        detail = reverse("listing:product_detail", args=[self.p.pk])
        self.client.logout()
        self.assertContains(self.client.get(detail), "Masuk untuk membeli")
        self.client.force_login(self.seller)
        self.assertContains(self.client.get(detail), "Listing milikmu")
        self.client.force_login(self.buyer)
        self.assertContains(self.client.get(detail), "Tambah ke keranjang")
        CartItem.objects.create(user=self.buyer, product=self.p)
        self.assertContains(self.client.get(detail), "Di keranjang")
        WishlistItem.objects.create(user=self.buyer, product=self.p)
        html = self.client.get("/wishlist/json/", {"category": "atasan"}).json()["html"]
        self.assertIn('data-cart-slot', html)
        self.assertIn("Di keranjang", html)
        Product.objects.filter(pk=self.p.pk).update(status="sold")
        html = self.client.get("/wishlist/json/").json()["html"]
        self.assertIn('data-availability="Terjual"', html)
        self.assertIn("Hapus dari wishlist", html)

    def test_checkout_then_cancel_refreshes_catalog_wishlist_cart_and_detail(self):
        WishlistItem.objects.create(user=self.buyer, product=self.p)
        ids, data = self.payload()
        order = checkout(self.buyer.pk, ids, data)["orders"][0]
        self.assertNotContains(self.client.get("/katalog/"), self.p.name)
        self.assertNotIn(self.p.pk, [p["id"] for p in self.client.get("/katalog/json/").json()["products"]])
        self.assertIn('data-availability="Terjual"', self.client.get("/wishlist/json/").json()["html"])
        self.assertEqual(self.client.get(reverse("pesanan:cart")).json()["count"], 0)
        transition(self.buyer.pk, order["id"], "cancel")
        self.assertContains(self.client.get("/katalog/"), self.p.name)
        self.assertIn('data-availability="Tersedia"', self.client.get("/wishlist/json/").json()["html"])
        self.assertContains(self.client.get(reverse("listing:product_detail", args=[self.p.pk])), "Tambah ke keranjang")

    def test_native_checkout_repeat_and_success_isolation(self):
        ids, data = self.payload([self.p, self.p2])
        url = reverse("pesanan:checkout_submit_page")
        first = self.client.post(url, {**data, "product_ids": ids})
        repeat = self.client.post(url, {**data, "product_ids": ids})
        self.assertEqual(first.url, repeat.url)
        self.assertEqual(Order.objects.count(), 2)
        self.assertContains(self.client.get(first.url), "Checkout tercatat")
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(first.url).status_code, 404)
        self.assertEqual(self.client.get(reverse("pesanan:order_page", args=[Order.objects.first().pk])).status_code, 404)

    def test_native_validation_price_reconfirmation_and_recovery_shell(self):
        ids, data = self.payload()
        response = self.client.post(reverse("pesanan:checkout_submit_page"), {**data, "product_ids": ids, "address": ""})
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.context["checkout_form"].errors)
        Product.objects.filter(pk=self.p.pk).update(price=Decimal("102.50"))
        response = self.client.post(reverse("pesanan:checkout_submit_page"), {**data, "product_ids": ids})
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "Rp102,50", status_code=409)
        CartItem.objects.filter(user=self.buyer).delete()
        response = self.client.get(reverse("pesanan:checkout_page"), {"product_ids": ids})
        self.assertContains(response, "data-checkout-recovery")
        self.assertContains(response, "keranjang Anda")

    def test_order_filters_roles_and_native_transitions(self):
        ids, data = self.payload()
        pk = checkout(self.buyer.pk, ids, data)["orders"][0]["id"]
        self.assertContains(self.client.get(reverse("pesanan:purchases_page"), {"status": "processing"}), self.p.name)
        self.assertNotContains(self.client.get(reverse("pesanan:purchases_page"), {"status": "shipped"}), self.p.name)
        self.client.force_login(self.seller)
        Profile.objects.filter(user=self.seller).update(is_seller=False)
        self.assertContains(self.client.get(reverse("pesanan:sales_page")), self.p.name)
        self.assertContains(self.client.get(reverse("pesanan:sales_page")), "Pesanan masuk")
        self.assertEqual(self.client.post(reverse("pesanan:ship_page", args=[pk])).status_code, 302)
        self.client.force_login(self.buyer)
        self.assertContains(self.client.get(reverse("pesanan:order_page", args=[pk])), "Selesaikan pesanan")
        self.assertEqual(self.client.post(reverse("pesanan:complete_page", args=[pk])).status_code, 302)
        self.assertContains(self.client.get(reverse("pesanan:order_page", args=[pk])), "Dibayar (simulasi)")

    def test_page_csrf_safe_redirect_and_huge_order_id(self):
        secure = Client(enforce_csrf_checks=True); secure.force_login(self.buyer)
        self.assertEqual(secure.post(reverse("pesanan:cart_add_page"), {"product_id": self.p.pk}).status_code, 403)
        response = self.client.post(reverse("pesanan:cart_add_page"), {"product_id": self.p.pk, "next": "//evil.invalid/"})
        self.assertRedirects(response, reverse("pesanan:cart_page"))
        self.assertEqual(self.client.get(reverse("pesanan:order_page", args=[2**70])).status_code, 404)
        self.assertEqual(self.client.post(reverse("pesanan:cancel_page", args=[2**70])).status_code, 404)

    def test_page_assets_once_and_no_review_dependency(self):
        response = self.client.get(reverse("pesanan:cart_page"))
        self.assertContains(response, 'src="/static/pesanan/pesanan.js"', count=1)
        self.assertContains(response, 'src="/static/pesanan/checkout_state.js"', count=1)
        self.assertContains(response, 'href="/static/pesanan/pesanan.css"', count=1)
        self.assertNotContains(response, "ulasan/")

    def test_order_pagination_and_unique_routes(self):
        from pesanan.urls import urlpatterns
        patterns = [str(pattern.pattern) for pattern in urlpatterns]
        names = [pattern.name for pattern in urlpatterns]
        self.assertEqual(len(patterns), len(set(patterns)))
        self.assertEqual(len(names), len(set(names)))
        for index in range(13):
            product = self.product(self.seller, f"Pagination {index}", "10.00")
            checkout(self.buyer.pk, *self.payload([product], key=f"pagination-{index}"))
        response = self.client.get(reverse("pesanan:purchases_page"), {"page": 2, "status": "processing"})
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["page_obj"]), 1)
        self.assertContains(response, "status=processing&amp;page=1")
