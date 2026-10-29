from django.urls import path
from . import page_views, views

app_name = "pesanan"
urlpatterns = [
    path("keranjang/", page_views.cart, name="cart_page"),
    path("keranjang/tambah/", page_views.cart_mutate, {"action": "add"}, name="cart_add_page"),
    path("keranjang/hapus/", page_views.cart_mutate, {"action": "remove"}, name="cart_remove_page"),
    path("checkout/konfirmasi/", page_views.checkout, name="checkout_page"),
    path("checkout/konfirmasi/kirim/", page_views.checkout_submit, name="checkout_submit_page"),
    path("checkout/berhasil/<int:pk>/", page_views.success, name="success_page"),
    path("pembelian/", page_views.order_list, name="purchases_page"),
    path("penjualan/", page_views.order_list, {"incoming": True}, name="sales_page"),
    path("detail/<int:pk>/", page_views.order_detail, name="order_page"),
    path("detail/<int:pk>/kirim/", page_views.order_action, {"action": "ship"}, name="ship_page"),
    path("detail/<int:pk>/selesai/", page_views.order_action, {"action": "complete"}, name="complete_page"),
    path("detail/<int:pk>/batal/", page_views.order_action, {"action": "cancel"}, name="cancel_page"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/", views.cart_add, name="cart_add"),
    path("cart/remove/", views.cart_remove, name="cart_remove"),
    path("checkout/quote/", views.checkout_quote, name="checkout_quote"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.orders, name="orders"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/ship/", views.order_action, {"action": "ship"}, name="ship"),
    path("orders/<int:pk>/complete/", views.order_action, {"action": "complete"}, name="complete"),
    path("orders/<int:pk>/cancel/", views.order_action, {"action": "cancel"}, name="cancel"),
]
