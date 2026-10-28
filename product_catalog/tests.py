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
        self.assertNotContains(response, "<script")
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
        self.assertNotContains(response, "<script")
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
