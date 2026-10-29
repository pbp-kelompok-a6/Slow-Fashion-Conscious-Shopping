from collections import defaultdict
from decimal import Decimal

from .models import CartItem, OrderItem
from .validation import DomainError


def purchasable_cart(user):
    return CartItem.objects.filter(user=user, product__status="active",
        product__seller__profile__is_seller=True, product__price__gt=0).exclude(
        product__seller=user).exclude(product__order_items__is_claimed=True)


def cart_state(request):
    if not hasattr(request, "_pesanan_cart_state"):
        if request.user.is_authenticated:
            all_ids = set(CartItem.objects.filter(user=request.user).values_list("product_id", flat=True))
            available_ids = set(purchasable_cart(request.user).values_list("product_id", flat=True))
        else:
            all_ids, available_ids = set(), set()
        request._pesanan_cart_state = {"ids": all_ids, "available_ids": available_ids}
    return request._pesanan_cart_state


def availability(product):
    if product.status == "sold":
        return "Terjual"
    if not getattr(getattr(product.seller, "profile", None), "is_seller", False):
        return "Seller nonaktif"
    if product.price <= 0 or OrderItem.objects.filter(product=product, is_claimed=True).exists():
        return "Tidak tersedia"
    return "Tersedia"


def cart_groups(request):
    state = cart_state(request)
    groups = defaultdict(list)
    for item in CartItem.objects.filter(user=request.user).select_related("product__seller__profile", "product__seller__store").prefetch_related("product__images"):
        groups[item.product.seller].append({"item": item, "product": item.product,
            "available": item.product_id in state["available_ids"], "availability": availability(item.product)})
    return [{"seller": seller, "rows": rows} for seller, rows in groups.items()]


def quote_groups(request, quote):
    products = {i.product_id: i.product for i in CartItem.objects.filter(user=request.user,
        product_id__in=[row["id"] for row in quote["items"]]).select_related("product__seller__store").prefetch_related("product__images")}
    prices = {row["id"]: Decimal(row["price"]) for row in quote["items"]}
    if set(products) != set(prices):
        raise DomainError("not_in_cart", "Keranjang berubah. Periksa pilihan barang kembali.", 409)
    return [{**group, "seller": products[group["product_ids"][0]].seller,
             "products": [{"product": products[pk], "price": prices[pk]} for pk in group["product_ids"]],
             "subtotal": Decimal(group["subtotal"]), "total": Decimal(group["total"]),
             "shipping_cost": Decimal(group["shipping_cost"])} for group in quote["groups"]]
