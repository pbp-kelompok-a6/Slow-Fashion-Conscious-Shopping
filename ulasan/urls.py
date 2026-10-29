from django.urls import path
from . import views

app_name = "ulasan"

urlpatterns = [
    path("produk/<int:product_id>/", views.product_reviews, name="product_reviews"),
    path("json/<int:product_id>/", views.show_json, name="show_json"),
    path("produk/<int:product_id>/tambah/", views.create_review, name="create_review"),
    path("json/toko/<str:username>/", views.show_store_json, name="show_store_json"),
    path("toko/<str:username>/tambah/", views.create_store_review, name="create_store_review"),
    path("<uuid:review_id>/edit/", views.edit_review, name="edit_review"),
    path("<uuid:review_id>/hapus/", views.delete_review, name="delete_review"),
]
