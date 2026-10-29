from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from akun.models import Profile
from listing.models import Product
from .models import WishlistItem


class CatalogWishlistTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="buyer")
        cls.other = get_user_model().objects.create_user(username="other")
        seller = get_user_model().objects.create_user(username="seller")
        Profile.objects.update_or_create(user=seller, defaults={"is_seller": True})
        cls.product = Product.objects.create(
            seller=seller, name="Kemeja linen", brand="Lokal", description="Kemeja",
            category="atasan", size="M", condition="good", price=50000,
        )
        Product.objects.create(
            seller=seller, name="Produk terjual", description="Lama", category="tas",
            size="L", condition="good", price=70000, status="sold",
        )

    def test_catalog_get_filters_and_base(self):
        response = self.client.get(reverse("product_catalog:katalog"))
        self.assertContains(response, self.product.name)
        self.assertNotContains(response, "Produk terjual")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "product_catalog/phase3.js")
        response = self.client.get(reverse("product_catalog:katalog"), {"q": "missing"})
        self.assertContains(response, "Produk tidak ditemukan")
        response = self.client.get(reverse("product_catalog:katalog"), {"category": "tas"})
        self.assertNotContains(response, self.product.name)

    def test_login_and_post_required(self):
        self.assertRedirects(self.client.get(reverse("product_catalog:wishlist")),
                             reverse("akun:login") + "?next=/wishlist/", fetch_redirect_response=False)
        self.client.force_login(self.user)
        for name, pk in [("toggle_wishlist", self.product.pk), ("remove_item", 1), ("update_note", 1)]:
            self.assertEqual(self.client.get(reverse("product_catalog:" + name, args=[pk])).status_code, 405)

    def test_post_lifecycle_and_html_validation(self):
        self.client.force_login(self.user)
        toggle = reverse("product_catalog:toggle_wishlist", args=[self.product.pk])
        self.assertRedirects(self.client.post(toggle, {"next": "/katalog/?q=linen"}),
                             "/katalog/?q=linen", fetch_redirect_response=False)
        item = WishlistItem.objects.get(user=self.user)
        response = self.client.get(reverse("product_catalog:wishlist"))
        self.assertContains(response, self.product.name)
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "product_catalog/phase3.js")
        note = reverse("product_catalog:update_note", args=[item.pk])
        self.assertEqual(self.client.post(note, {"note": "x" * 201}).status_code, 400)
        self.assertRedirects(self.client.post(note, {"note": "Untuk kerja"}), "/wishlist/")
        item.refresh_from_db()
        self.assertEqual(item.note, "Untuk kerja")
        self.assertRedirects(self.client.post(reverse("product_catalog:remove_item", args=[item.pk])), "/wishlist/")
        self.assertFalse(WishlistItem.objects.filter(user=self.user).exists())
        self.client.post(toggle)
        self.client.post(toggle)
        self.assertFalse(WishlistItem.objects.filter(user=self.user).exists())

    def test_ownership_redirect_and_csrf(self):
        item = WishlistItem.objects.create(user=self.other, product=self.product, note="Pribadi")
        self.client.force_login(self.user)
        self.assertNotContains(self.client.get("/wishlist/"), "Pribadi")
        for action in ["update_note", "remove_item"]:
            response = self.client.post(reverse("product_catalog:" + action, args=[item.pk]), {"note": "ubah"})
            self.assertEqual(response.status_code, 404)
        toggle = reverse("product_catalog:toggle_wishlist", args=[self.product.pk])
        self.assertRedirects(self.client.post(toggle, {"next": "https://example.com/"}), "/katalog/", fetch_redirect_response=False)
        secure_client = Client(enforce_csrf_checks=True)
        secure_client.force_login(self.user)
        self.assertEqual(secure_client.post(toggle).status_code, 403)


class CatalogWishlistAjaxTests(TestCase):
    setUpTestData = classmethod(CatalogWishlistTests.setUpTestData.__func__)
    ajax = {"HTTP_ACCEPT": "application/json", "HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

    def test_ajax_filters_render_same_cards_and_canonical_links(self):
        from decimal import Decimal
        self.product.price = Decimal("50000.25")
        self.product.save(update_fields=["price"])
        self.client.force_login(self.user)
        WishlistItem.objects.create(user=self.user, product=self.product)
        response = self.client.get("/katalog/json/", {"q": "linen", "brand": ["Lokal"], "min_price": "50000.25"}, **self.ajax)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["products"][0]["id"], self.product.pk)
        self.assertIn("pc-saved", data["html"])
        self.assertIn('value="/katalog/?', data["html"])
        self.assertNotIn('value="/katalog/json/?', data["html"])
        self.assertIn("50000.25", data["html"])
        empty = self.client.get("/katalog/json/", {"q": "absent"}, **self.ajax).json()
        self.assertEqual(empty["count"], 0)
        self.assertIn("Produk tidak ditemukan", empty["html"])

    def test_ajax_explicit_state_is_idempotent_and_survives_reload(self):
        self.client.force_login(self.user)
        url = reverse("product_catalog:toggle_wishlist", args=[self.product.pk])
        for _ in range(3):
            result = self.client.post(url, {"in_wishlist": "true"}, **self.ajax)
            self.assertEqual(result.status_code, 200)
            self.assertTrue(result.json()["in_wishlist"])
            self.assertEqual(result.json()["count"], 1)
        self.assertEqual(WishlistItem.objects.filter(user=self.user).count(), 1)
        self.assertContains(self.client.get("/katalog/"), 'aria-pressed="true"')
        for _ in range(3):
            result = self.client.post(url, {"in_wishlist": "false"}, **self.ajax)
            self.assertFalse(result.json()["in_wishlist"])
            self.assertEqual(result.json()["count"], 0)
        self.assertContains(self.client.get("/katalog/"), 'aria-pressed="false"')
        self.assertEqual(self.client.post(url, {"in_wishlist": "bad"}, **self.ajax).status_code, 400)

    def test_ajax_notes_remove_and_category(self):
        self.client.force_login(self.user)
        item = WishlistItem.objects.create(user=self.user, product=self.product)
        note_url = reverse("product_catalog:update_note", args=[item.pk])
        invalid = self.client.post(note_url, {"note": "x" * 201}, **self.ajax)
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("note", invalid.json()["errors"])
        result = self.client.post(note_url, {"note": "<script>alert(1)</script>"}, **self.ajax).json()
        self.assertTrue(result["success"])
        response = self.client.get("/wishlist/json/", {"category": "atasan"}, **self.ajax).json()
        self.assertEqual(response["count"], 1)
        self.assertIn("&lt;script&gt;", response["html"])
        self.assertIn('value="/wishlist/?category=atasan"', response["html"])
        filtered = self.client.get("/wishlist/json/", {"category": "tas"}, **self.ajax).json()
        self.assertIn("Belum ada barang di kategori ini", filtered["html"])
        result = self.client.post(reverse("product_catalog:remove_item", args=[item.pk]), **self.ajax).json()
        self.assertEqual(result["product_id"], self.product.pk)
        self.assertEqual(result["count"], 0)
        self.assertFalse(WishlistItem.objects.filter(pk=item.pk).exists())

    def test_ajax_auth_csrf_and_ownership(self):
        toggle = reverse("product_catalog:toggle_wishlist", args=[self.product.pk])
        self.assertEqual(self.client.post(toggle, {"in_wishlist": "true"}, **self.ajax).status_code, 302)
        self.client.force_login(self.user)
        other_item = WishlistItem.objects.create(user=self.other, product=self.product)
        for action in ["update_note", "remove_item"]:
            self.assertEqual(self.client.post(reverse("product_catalog:" + action, args=[other_item.pk]), **self.ajax).status_code, 404)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(toggle, {"in_wishlist": "true"}, **self.ajax).status_code, 403)
        csrf_client.get("/katalog/")
        token = csrf_client.cookies["csrftoken"].value
        self.assertEqual(csrf_client.post(toggle, {"in_wishlist": "true"}, HTTP_X_CSRFTOKEN=token, **self.ajax).status_code, 200)
