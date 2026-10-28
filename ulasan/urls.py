from django.urls import path
from . import views

app_name = "ulasan"

urlpatterns = [
    path("produk/<int:product_id>/", views.product_reviews, name="product_reviews"),
    path("json/<int:product_id>/", views.show_json, name="show_json"),
    path("produk/<int:product_id>/tambah/", views.create_review, name="create_review"),
]
