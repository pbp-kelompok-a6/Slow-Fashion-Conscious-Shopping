from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.template import TemplateDoesNotExist
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from akun.models import Profile
from listing.forms import ProductForm, ProductImageFormSet
from listing.models import Product, ProductImage
from listing.utils import product_card_data
from product_catalog.models import WishlistItem
from profil_toko.models import Store


class PhaseRegressionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media = TemporaryDirectory(prefix="lapakaian-test-media-")
        cls.addClassCleanup(cls.media.cleanup)
        cls.settings_override = override_settings(MEDIA_ROOT=cls.media.name)
        cls.settings_override.enable()
        cls.addClassCleanup(cls.settings_override.disable)

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.buyer = User.objects.create_user("phase-buyer", password="Password-7654!")
        cls.seller = User.objects.create_user("phase-seller")
        Profile.objects.filter(user=cls.seller).update(is_seller=True)
        cls.product = Product.objects.create(seller=cls.seller, name="Linen desimal", price=Decimal("100.25"), category="atasan", size="M", condition="good", description="Deskripsi")
        cls.store = Store.objects.create(owner=cls.seller, name="Toko Linen", city="Jakarta", whatsapp_number="081234567890")

    def test_navbar_roles_and_script_order(self):
        anonymous = self.client.get("/")
        self.assertNotContains(anonymous, "data-seller-nav")
        for user, hidden in [(self.buyer, True), (self.seller, False)]:
            self.client.force_login(user)
            response = self.client.get("/")
            self.assertContains(response, "data-seller-nav", count=2)
            self.assertContains(response, 'action="/akun/logout/"')
            self.assertContains(response, 'data-seller-nav hidden' if hidden else 'data-seller-nav >')
            html = response.content.decode()
            self.assertLess(html.index("js/utils.js"), html.index("product_catalog/product_catalog.js"))

    def test_store_empty_and_populated_optional_reviews(self):
        response = self.client.get(reverse("profil_toko:detail", args=[self.seller.username]))
        self.assertContains(response, self.product.name)
        self.assertTemplateUsed(response, "partials/product_card.html")
        Product.objects.all().delete()
        self.assertContains(self.client.get(reverse("profil_toko:detail", args=[self.seller.username])), "Belum ada produk")

    def test_optional_reviews_does_not_swallow_other_dependencies(self):
        with patch("profil_toko.views.get_template", side_effect=TemplateDoesNotExist("other/dependency.html")):
            with self.assertRaises(TemplateDoesNotExist):
                self.client.get(reverse("profil_toko:detail", args=[self.seller.username]))

    def test_detail_one_and_multiple_products_and_missing_store(self):
        url = reverse("listing:product_detail", args=[self.product.pk])
        self.assertContains(self.client.get(url), self.product.name)
        second = Product.objects.create(seller=self.seller, name="Produk kedua", price=200, category="tas", size="L", condition="good", description="Tes")
        response = self.client.get(url)
        self.assertContains(response, reverse("listing:product_detail", args=[second.pk]))
        self.store.delete()
        self.assertContains(self.client.get(url), "Seller belum membuka toko.")
        data = self.client.get(reverse("listing:product_detail_json", args=[self.product.pk])).json()
        self.assertIsNone(data["product"]["store_url"])
        self.client.force_login(self.seller)
        self.assertRedirects(self.client.get(reverse("profil_toko:toko_saya")), reverse("profil_toko:buka_toko"))

    def test_new_admin_and_legacy_users_have_profile(self):
        User = get_user_model()
        admin = User.objects.create_superuser("phase-admin", password="Password-7654!")
        self.assertEqual(Profile.objects.filter(user=admin).count(), 1)
        Profile.objects.filter(user=self.buyer).delete()
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(reverse("akun:profil")).status_code, 200)
        self.assertEqual(Profile.objects.filter(user=self.buyer).count(), 1)

    def test_registration_does_not_duplicate_profile(self):
        self.client.post(reverse("akun:register"), {"username": "new-phase-user", "password1": "Long-unique-Password-7654!", "password2": "Long-unique-Password-7654!"})
        self.assertEqual(Profile.objects.filter(user__username="new-phase-user").count(), 1)

    def test_login_safe_next_get_post_and_rejection(self):
        login = reverse("akun:login")
        credentials = {"username": self.buyer.username, "password": "Password-7654!"}
        for target, expected in [("/wishlist/?category=tas", "/wishlist/?category=tas"), ("https://evil.example/", "/"), ("//evil.example/", "/"), ("/\\evil.example/", "/")]:
            self.client.logout()
            self.assertRedirects(self.client.post(login, {**credentials, "next": target}), expected, fetch_redirect_response=False)
        self.client.logout()
        self.assertRedirects(self.client.post(login + "?next=/wishlist/", credentials), "/wishlist/", fetch_redirect_response=False)
        self.assertContains(self.client.get(login, {"next": "/wishlist/"}), 'value="/wishlist/"')

    def test_logout_requires_post_and_csrf(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(reverse("akun:logout")).status_code, 405)
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.buyer)
        self.assertEqual(secure.post(reverse("akun:logout")).status_code, 403)
        secure.get("/")
        self.assertRedirects(secure.post(reverse("akun:logout"), HTTP_X_CSRFTOKEN=secure.cookies["csrftoken"].value), "/")

    def test_bio_validation_and_seller_toggle(self):
        self.client.force_login(self.buyer)
        invalid = self.client.post(reverse("akun:edit_profil"), {"bio": "a" * 201})
        self.assertEqual(invalid.status_code, 400)
        self.assertTrue(invalid.context["form"].errors)
        self.assertEqual(Profile.objects.get(user=self.buyer).bio, "")
        self.client.post(reverse("akun:edit_profil"), {"bio": "Bio baru"})
        self.assertEqual(Profile.objects.get(user=self.buyer).bio, "Bio baru")
        for expected in [True, False]:
            self.assertEqual(self.client.post(reverse("akun:toggle_seller")).json()["is_seller"], expected)

    def test_unavailable_public_detail_wishlist_and_owner_access(self):
        self.client.force_login(self.buyer)
        item = WishlistItem.objects.create(user=self.buyer, product=self.product)
        for sold in [True, False]:
            self.product.status = "sold" if sold else "active"
            self.product.save()
            Profile.objects.filter(user=self.seller).update(is_seller=sold)
            self.assertNotContains(self.client.get("/katalog/"), self.product.name)
            response = self.client.get(reverse("listing:product_detail", args=[self.product.pk]))
            self.assertContains(response, "Terjual" if sold else "seller nonaktif")
            self.assertContains(self.client.get("/wishlist/"), "Hapus dari wishlist")
        self.assertRedirects(self.client.post(reverse("product_catalog:remove_item", args=[item.pk])), "/wishlist/")
        self.assertEqual(self.client.post(reverse("product_catalog:toggle_wishlist", args=[self.product.pk]), {"in_wishlist": "true"}).status_code, 404)
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(reverse("listing:product_edit", args=[self.product.pk])).status_code, 200)

    def test_filtered_wishlist_counts_global_ids_and_unique_constraint(self):
        self.client.force_login(self.buyer)
        WishlistItem.objects.create(user=self.buyer, product=self.product)
        data = self.client.get("/wishlist/json/", {"category": "tas"}).json()
        self.assertEqual(data["items"], [])
        self.assertEqual(data["total_count"], 1)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["filtered_count"], 0)
        self.assertEqual(data["wishlist_product_ids"], [self.product.pk])
        with self.assertRaises(IntegrityError), transaction.atomic():
            WishlistItem.objects.create(user=self.buyer, product=self.product)

    def test_price_precision_ranges_and_pagination(self):
        form = ProductForm(instance=self.product)
        self.assertEqual(Decimal(form.initial["price"]), Decimal("100.25"))
        self.assertEqual(product_card_data(self.product)["price"], "100.25")
        self.assertEqual(product_card_data(self.product)["price_display"], "Rp100,25")
        data = self.client.get("/katalog/json/", {"min_price": "100.25", "max_price": "100.25"}).json()
        self.assertEqual(data["filters"]["min_price"], "100.25")
        self.assertEqual(data["count"], 1)
        invalid = self.client.get("/katalog/json/", {"min_price": "200", "max_price": "100"}).json()
        self.assertIn("minimum", invalid["price_error"])
        self.assertIn(invalid["price_error"], invalid["html"])
        for i in range(13):
            Product.objects.create(seller=self.seller, name=f"Produk {i}", price=200, category="tas", size="M", condition="good", description="Tes")
        data = self.client.get("/katalog/json/", {"page": 2}).json()
        self.assertEqual((data["count"], data["page"], data["num_pages"], len(data["products"])), (14, 2, 2, 2))

    def test_detail_links_and_explicit_state_fallback_in_ajax_html(self):
        self.client.force_login(self.buyer)
        detail = reverse("listing:product_detail", args=[self.product.pk])
        for path in ["/katalog/", "/katalog/json/"]:
            response = self.client.get(path)
            html = response.json()["html"] if path.endswith("json/") else response.content.decode()
            self.assertGreaterEqual(html.count(f'href="{detail}"'), 2)
            self.assertIn('name="in_wishlist" value="true"', html)
        toggle = reverse("product_catalog:toggle_wishlist", args=[self.product.pk])
        for _ in range(2):
            self.assertRedirects(self.client.post(toggle, {"in_wishlist": "true", "next": detail}), detail)
        html = self.client.get("/wishlist/json/").json()["html"]
        self.assertGreaterEqual(html.count(f'href="{detail}"'), 2)
        self.assertEqual(WishlistItem.objects.filter(user=self.buyer).count(), 1)

    def test_listing_ownership_csrf_status_delete_and_filter(self):
        self.client.force_login(self.buyer)
        delete = reverse("listing:product_delete", args=[self.product.pk])
        self.assertEqual(self.client.post(delete).status_code, 403)
        Profile.objects.filter(user=self.buyer).update(is_seller=True)
        self.assertEqual(self.client.post(delete).status_code, 404)
        self.client.force_login(self.seller)
        for name in ["product_mark_sold", "product_mark_active"]:
            response = self.client.post(reverse("listing:" + name, args=[self.product.pk]))
            self.assertTrue(response.json()["success"])
        self.assertNotContains(self.client.get(reverse("listing:my_listings"), {"category": "tas"}), self.product.name)
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.seller)
        self.assertEqual(secure.post(delete).status_code, 403)
        self.assertTrue(self.client.post(delete).json()["success"])

    def test_photo_limit_and_image_formset_ownership(self):
        # The formset accepts at most five photos, even if a client tampers with management data.
        from io import BytesIO
        from PIL import Image
        image = BytesIO(); Image.new("RGB", (1, 1)).save(image, format="PNG")
        data = {"images-TOTAL_FORMS": "6", "images-INITIAL_FORMS": "0", "images-MIN_NUM_FORMS": "0", "images-MAX_NUM_FORMS": "5"}
        files = {f"images-{i}-image": SimpleUploadedFile(f"photo-{i}.png", image.getvalue(), "image/png") for i in range(6)}
        formset = ProductImageFormSet(data, files, instance=self.product)
        self.assertFalse(formset.is_valid())
        self.assertTrue(formset.non_form_errors())
        data["images-TOTAL_FORMS"] = "5"
        formset = ProductImageFormSet(data, {k: v for k, v in files.items() if "-5-" not in k}, instance=self.product)
        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()
        self.assertEqual(ProductImage.objects.filter(product=self.product).count(), 5)

    def test_landing_real_products_and_empty_state(self):
        self.assertContains(self.client.get("/"), self.product.name)
        Product.objects.all().delete()
        self.assertContains(self.client.get("/"), "Belum ada produk tersedia.")
