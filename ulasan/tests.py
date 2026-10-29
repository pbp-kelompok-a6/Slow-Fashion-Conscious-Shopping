import uuid
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from listing.models import Product
from .forms import ReviewForm
from .models import Review


class ReviewTestBase(TestCase):
    """Data dasar yang dipakai semua test: 1 seller, 2 buyer, 1 produk."""

    def setUp(self):
        self.seller = User.objects.create_user(username="seller", password="pass12345!")
        self.buyer = User.objects.create_user(username="buyer", password="pass12345!")
        self.other = User.objects.create_user(username="other", password="pass12345!")
        self.product = Product.objects.create(
            seller=self.seller,
            name="Kemeja Flanel",
            description="Kemeja flanel bekas, masih bagus.",
            category="atasan",
            size="M",
            condition="good",
            price=75000,
        )

    def create_review(self, user, rating=4, komentar="Bagus"):
        return Review.objects.create(product=self.product, user=user, rating=rating, komentar=komentar)


class ReviewModelTest(ReviewTestBase):
    def test_str(self):
        review = self.create_review(self.buyer, rating=5)
        self.assertEqual(str(review), "buyer - Kemeja Flanel (5)")

    def test_one_review_per_user_per_product(self):
        self.create_review(self.buyer)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_review(self.buyer)

    def test_review_deleted_with_product(self):
        self.create_review(self.buyer)
        self.product.delete()
        self.assertEqual(Review.objects.count(), 0)


class ReviewFormTest(TestCase):
    def test_valid_form_strips_html_tags(self):
        form = ReviewForm(data={"rating": 5, "komentar": "<script>x</script>Bagus <b>banget</b>"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["komentar"], "xBagus banget")

    def test_comment_only_tags_is_invalid(self):
        form = ReviewForm(data={"rating": 5, "komentar": "<b></b>   "})
        self.assertFalse(form.is_valid())
        self.assertIn("Komentar tidak boleh kosong.", form.errors["komentar"])

    def test_rating_required(self):
        form = ReviewForm(data={"komentar": "Bagus"})
        self.assertFalse(form.is_valid())
        self.assertIn("Pilih rating 1 sampai 5.", form.errors["rating"])

    def test_rating_out_of_range(self):
        form = ReviewForm(data={"rating": 6, "komentar": "Bagus"})
        self.assertFalse(form.is_valid())
        self.assertIn("rating", form.errors)


class ProductReviewsPageTest(ReviewTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse("ulasan:product_reviews", args=[self.product.pk])

    def test_page_uses_templates(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ulasan/product_reviews.html")
        self.assertTemplateUsed(response, "ulasan/slots/product_reviews.html")
        self.assertContains(response, "Kemeja Flanel")

    def test_page_product_not_found(self):
        response = self.client.get(reverse("ulasan:product_reviews", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_guest_sees_login_note_without_form(self):
        response = self.client.get(self.url)
        self.assertContains(response, "untuk menulis ulasan")
        self.assertNotContains(response, 'id="review-form"')

    def test_seller_cannot_see_form_for_own_product(self):
        self.client.force_login(self.seller)
        response = self.client.get(self.url)
        self.assertContains(response, "Ini produkmu sendiri")
        self.assertNotContains(response, 'id="review-form"')

    def test_buyer_sees_form(self):
        self.client.force_login(self.buyer)
        response = self.client.get(self.url)
        self.assertContains(response, 'id="review-form"')


class ShowJsonTest(ReviewTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse("ulasan:show_json", args=[self.product.pk])

    def test_empty_reviews(self):
        data = self.client.get(self.url).json()
        self.assertEqual(data["jumlah"], 0)
        self.assertEqual(data["rata_rata"], 0)
        self.assertEqual(data["reviews"], [])

    def test_summary(self):
        self.create_review(self.buyer, rating=5)
        self.create_review(self.other, rating=2)
        data = self.client.get(self.url).json()
        self.assertEqual(data["jumlah"], 2)
        self.assertEqual(data["rata_rata"], 3.5)

    def test_sort_terbaru_is_default(self):
        old = self.create_review(self.buyer, rating=5)
        Review.objects.filter(pk=old.pk).update(created_at=old.created_at - timedelta(days=1))
        self.create_review(self.other, rating=1)

        data = self.client.get(self.url).json()
        self.assertEqual(data["sort"], "terbaru")
        self.assertEqual([r["username"] for r in data["reviews"]], ["other", "buyer"])

    def test_sort_rating(self):
        old = self.create_review(self.buyer, rating=5)
        Review.objects.filter(pk=old.pk).update(created_at=old.created_at - timedelta(days=1))
        self.create_review(self.other, rating=1)

        data = self.client.get(self.url, {"sort": "rating"}).json()
        self.assertEqual(data["sort"], "rating")
        self.assertEqual([r["username"] for r in data["reviews"]], ["buyer", "other"])

    def test_unknown_sort_falls_back_to_terbaru(self):
        data = self.client.get(self.url, {"sort": "ngawur"}).json()
        self.assertEqual(data["sort"], "terbaru")

    def test_guest_is_not_owner(self):
        self.create_review(self.buyer)
        review = self.client.get(self.url).json()["reviews"][0]
        self.assertFalse(review["is_owner"])
        self.assertIsNone(review["edit_url"])
        self.assertIsNone(review["delete_url"])

    def test_owner_gets_edit_and_delete_url(self):
        mine = self.create_review(self.buyer)
        self.create_review(self.other)
        self.client.force_login(self.buyer)

        reviews = {r["username"]: r for r in self.client.get(self.url).json()["reviews"]}
        self.assertTrue(reviews["buyer"]["is_owner"])
        self.assertEqual(reviews["buyer"]["edit_url"], reverse("ulasan:edit_review", args=[mine.id]))
        self.assertEqual(reviews["buyer"]["delete_url"], reverse("ulasan:delete_review", args=[mine.id]))
        self.assertFalse(reviews["other"]["is_owner"])
        self.assertIsNone(reviews["other"]["edit_url"])

    def test_is_edited(self):
        review = self.create_review(self.buyer)
        self.assertFalse(self.client.get(self.url).json()["reviews"][0]["is_edited"])

        Review.objects.filter(pk=review.pk).update(updated_at=review.created_at + timedelta(minutes=5))
        self.assertTrue(self.client.get(self.url).json()["reviews"][0]["is_edited"])

    def test_product_not_found(self):
        response = self.client.get(reverse("ulasan:show_json", args=[99999]))
        self.assertEqual(response.status_code, 404)


class CreateReviewTest(ReviewTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse("ulasan:create_review", args=[self.product.pk])
        self.valid_data = {"rating": 4, "komentar": "Sesuai foto"}

    def test_guest_forbidden(self):
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Review.objects.count(), 0)

    def test_seller_cannot_review_own_product(self):
        self.client.force_login(self.seller)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Review.objects.count(), 0)

    def test_create_success(self):
        self.client.force_login(self.buyer)
        response = self.client.post(self.url, {"rating": 5, "komentar": "<i>Mantap</i>"})
        self.assertEqual(response.status_code, 201)

        review = Review.objects.get()
        self.assertEqual(review.user, self.buyer)
        self.assertEqual(review.product, self.product)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.komentar, "Mantap")

    def test_invalid_data(self):
        self.client.force_login(self.buyer)
        response = self.client.post(self.url, {"rating": "", "komentar": ""})
        self.assertEqual(response.status_code, 400)
        self.assertIn("rating", response.json()["errors"])
        self.assertIn("komentar", response.json()["errors"])
        self.assertEqual(Review.objects.count(), 0)

    def test_cannot_review_twice(self):
        self.create_review(self.buyer)
        self.client.force_login(self.buyer)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Kamu sudah mengulas produk ini.")
        self.assertEqual(Review.objects.count(), 1)

    def test_get_not_allowed(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_product_not_found(self):
        self.client.force_login(self.buyer)
        response = self.client.post(reverse("ulasan:create_review", args=[99999]), self.valid_data)
        self.assertEqual(response.status_code, 404)


class EditReviewTest(ReviewTestBase):
    def setUp(self):
        super().setUp()
        self.review = self.create_review(self.buyer, rating=3, komentar="Lumayan")
        self.url = reverse("ulasan:edit_review", args=[self.review.id])
        self.new_data = {"rating": 5, "komentar": "Ternyata bagus banget"}

    def test_guest_forbidden(self):
        response = self.client.post(self.url, self.new_data)
        self.assertEqual(response.status_code, 403)

    def test_other_user_forbidden(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url, self.new_data)
        self.assertEqual(response.status_code, 403)
        self.review.refresh_from_db()
        self.assertEqual(self.review.komentar, "Lumayan")

    def test_edit_success(self):
        self.client.force_login(self.buyer)
        response = self.client.post(self.url, self.new_data)
        self.assertEqual(response.status_code, 200)

        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 5)
        self.assertEqual(self.review.komentar, "Ternyata bagus banget")
        self.assertEqual(Review.objects.count(), 1)

    def test_invalid_data(self):
        self.client.force_login(self.buyer)
        response = self.client.post(self.url, {"rating": 9, "komentar": ""})
        self.assertEqual(response.status_code, 400)
        self.assertIn("rating", response.json()["errors"])
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 3)

    def test_get_not_allowed(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_review_not_found(self):
        self.client.force_login(self.buyer)
        response = self.client.post(reverse("ulasan:edit_review", args=[uuid.uuid4()]), self.new_data)
        self.assertEqual(response.status_code, 404)


class DeleteReviewTest(ReviewTestBase):
    def setUp(self):
        super().setUp()
        self.review = self.create_review(self.buyer)
        self.url = reverse("ulasan:delete_review", args=[self.review.id])

    def test_guest_forbidden(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Review.objects.count(), 1)

    def test_other_user_forbidden(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Review.objects.count(), 1)

    def test_delete_success(self):
        self.client.force_login(self.buyer)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Review.objects.count(), 0)

    def test_get_not_allowed(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(Review.objects.count(), 1)

    def test_review_not_found(self):
        self.client.force_login(self.buyer)
        response = self.client.post(reverse("ulasan:delete_review", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)
