import json
from functools import wraps

from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from . import services
from .models import CartItem, Order, OrderItem
from .validation import CheckoutForm, DomainError, product_ids


def api(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"success": False, "code": "authentication_required", "message": "Silakan masuk terlebih dahulu."}, status=401)
        try:
            return view(request, *args, **kwargs)
        except DomainError as exc:
            return JsonResponse({"success": False, "code": exc.code, "message": exc.message}, status=exc.status)
    return wrapped


def body(request):
    if request.content_type != "application/json":
        raise DomainError("invalid_content_type", "Gunakan body JSON.", 415)
    if len(request.body) > 65536:
        raise DomainError("body_too_large", "Permintaan terlalu besar.", 413)
    try:
        value = json.loads(request.body)
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise DomainError("invalid_json", "Body JSON tidak valid.") from exc
    if not isinstance(value, dict):
        raise DomainError("invalid_json", "Body JSON harus berupa object.")
    return value


@require_GET
@ensure_csrf_cookie
@api
def cart(request):
    items = list(CartItem.objects.filter(user=request.user).select_related("product__seller__profile"))
    claimed = set(OrderItem.objects.filter(product_id__in=[i.product_id for i in items], is_claimed=True).values_list("product_id", flat=True))
    rows = []
    for item in items:
        p = item.product
        available = p.status == "active" and getattr(getattr(p.seller, "profile", None), "is_seller", False) and p.pk not in claimed and p.seller_id != request.user.pk and p.price > 0
        rows.append({"id": item.pk, "product_id": p.pk, "seller_id": p.seller_id,
                     "name": p.name, "price": str(p.price), "available": available})
    groups = [{"seller_id": seller, "items": [row for row in rows if row["seller_id"] == seller]}
              for seller in sorted({row["seller_id"] for row in rows})]
    return JsonResponse({"success": True, "items": rows, "groups": groups, "count": len(rows), "shipping_per_seller": str(services.SHIPPING)})


@require_POST
@api
def cart_add(request):
    data = body(request)
    if "quantity" in data and (type(data["quantity"]) is not int or data["quantity"] != 1):
        raise DomainError("invalid_quantity", "Setiap listing hanya memiliki satu unit.")
    product_id = product_ids([data.get("product_id")])[0]
    item_id = services.add_to_cart(request.user.pk, product_id)
    return JsonResponse({"success": True, "cart_item_id": item_id, "product_id": product_id})


@require_POST
@api
def cart_remove(request):
    product_id = product_ids([body(request).get("product_id")])[0]
    services.remove_from_cart(request.user.pk, product_id)
    return JsonResponse({"success": True})


@require_POST
@api
def checkout_quote(request):
    ids = product_ids(body(request).get("product_ids"))
    return JsonResponse({"success": True, **services.quote(request.user.pk, ids)})


@require_POST
@api
def checkout(request):
    data = body(request)
    ids = product_ids(data.get("product_ids"))
    # Reject containers instead of coercing them into plausible address strings.
    if any(not isinstance(data.get(field), str) for field in CheckoutForm.base_fields):
        raise DomainError("invalid_checkout", "Lengkapi alamat, metode pembayaran, token ringkasan, dan kunci percobaan sebagai teks.")
    form = CheckoutForm(data)
    if not form.is_valid():
        return JsonResponse({"success": False, "code": "invalid_checkout", "errors": form.errors.get_json_data()}, status=400)
    return JsonResponse({"success": True, "simulation": True, **services.checkout(request.user.pk, ids, form.cleaned_data)})


@require_GET
@api
def orders(request):
    queryset = Order.objects.filter(Q(buyer=request.user) | Q(seller=request.user)).prefetch_related("items")
    return JsonResponse({"success": True, "orders": [services.serialize_order(o) for o in queryset]})


@require_GET
@api
def order_detail(request, pk):
    pk = product_ids([pk])[0]
    order = Order.objects.filter(Q(buyer=request.user) | Q(seller=request.user), pk=pk).prefetch_related("items").first()
    if order is None:
        raise DomainError("not_found", "Pesanan tidak ditemukan.", 404)
    return JsonResponse({"success": True, "order": services.serialize_order(order)})


@require_POST
@api
def order_action(request, pk, action):
    pk = product_ids([pk])[0]
    return JsonResponse({"success": True, "order": services.transition(request.user.pk, pk, action)})
