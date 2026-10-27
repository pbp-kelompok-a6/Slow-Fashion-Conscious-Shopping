from django.urls import path
from . import views

app_name = "ulasan"

urlpatterns = [
    path("json/<int:product_id>/", views.show_json, name="show_json"),
]
