import uuid
from django.db import models
from django.contrib.auth.models import User
from listing.models import Product

class Review(models.Model):
    """
    Ulasan untuk SATU produk ATAU SATU toko (salah satu saja yang diisi).
    Toko diwakili oleh User pemiliknya (field `seller`), bukan model Store,
    karena Store dihapus saat toko ditutup dan ulasannya tidak boleh ikut hilang.
    """
    RATING_CHOICES = [
        (1, "1 - Sangat Buruk"),
        (2, "2 - Buruk"),
        (3, "3 - Cukup"),
        (4, "4 - Baik"),
        (5, "5 - Sangat Baik"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews", null=True, blank=True)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="store_reviews", null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(choices=RATING_CHOICES)
    komentar = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Satu user hanya boleh punya satu ulasan untuk satu produk, dan satu ulasan untuk satu toko.
        # Nilai NULL tidak dianggap sama oleh database, jadi ulasan toko (product kosong)
        # tidak bentrok dengan constraint produk, begitu juga sebaliknya.
        constraints = [
            models.UniqueConstraint(fields=["product", "user"], name="unique_review_per_user_product"),
            models.UniqueConstraint(fields=["seller", "user"], name="unique_review_per_user_store"),
        ]

    def __str__(self):
        if self.product_id:
            target = self.product.name
        else:
            target = f"toko {self.seller.username}"
        return f"{self.user.username} - {target} ({self.rating})"
