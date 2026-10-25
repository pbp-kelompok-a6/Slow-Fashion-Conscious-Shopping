import uuid
from django.db import models
from django.contrib.auth.models import User

class Review(models.Model):
    RATING_CHOICES = [
        (1, "1 - Sangat Buruk"),
        (2, "2 - Buruk"),
        (3, "3 - Cukup"),
        (4, "4 - Baik"),
        (5, "5 - Sangat Baik"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(choices=RATING_CHOICES)
    komentar = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.rating}"
