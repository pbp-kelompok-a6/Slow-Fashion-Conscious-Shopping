import uuid
from django.db import models
from django.contrib.auth.models import User
from listing.models import Product

class Review(models.Model):
    RATING_CHOICES = [
        (1, "1 - Sangat Buruk"),
        (2, "2 - Buruk"),
        (3, "3 - Cukup"),
        (4, "4 - Baik"),
        (5, "5 - Sangat Baik"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(choices=RATING_CHOICES)
    komentar = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Satu user hanya boleh punya satu ulasan untuk satu produk
        constraints = [
            models.UniqueConstraint(fields=["product", "user"], name="unique_review_per_user_product"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating})"
