from copy import copy

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from listing.models import Product
from listing.utils import product_card_data
from .filters import (
    active_filter_chips, filter_options, filter_products, parse_filters, query_without_page,
)
from .forms import WishlistNoteForm
from .models import WishlistItem

PER_PAGE = 12


def page_html(request, template, context, url_name):
    # Links and POST fallback targets must use the public page, not /json/.
    page_request = copy(request)
    page_request.path = page_request.path_info = reverse(url_name)
    return render(page_request, template, context).content.decode()


def paginate(request, queryset):
    return Paginator(queryset, PER_PAGE).get_page(request.GET.get("page"))


# ---------- Katalog ----------

def catalog_context(request):
    filters = parse_filters(request.GET)
    page_obj = paginate(request, filter_products(filters))
    chips = active_filter_chips(request.GET, filters)
    return {
        "page_obj": page_obj,
        "products": page_obj.object_list,
        "wishlist_product_ids": set(WishlistItem.objects.filter(user=request.user).values_list("product_id", flat=True)) if request.user.is_authenticated else set(),
        "filters": filters,
        "options": filter_options(),
        "active_chips": chips,
        "querystring": query_without_page(request.GET),
        "clear_url": "?sort=" + filters["sort"],
    }


def katalog(request):
    return render(request, "katalog.html", catalog_context(request))


@require_GET
def katalog_json(request):
    context = catalog_context(request)
    filters = context["filters"]
    page_obj = context["page_obj"]
    return JsonResponse({
        "html": page_html(request, "katalog.html", context, "product_catalog:katalog"),
        "success": True,
        "message": "OK",
        "count": page_obj.paginator.count,
        "page": page_obj.number,
        "num_pages": page_obj.paginator.num_pages,
        "filters": {
            **filters,
            "min_price": int(filters["min_price"]) if filters["min_price"] is not None else None,
            "max_price": int(filters["max_price"]) if filters["max_price"] is not None else None,
        },
        "products": [product_card_data(p) for p in page_obj.object_list],
    })

# ---------- Wishlist ----------

def wishlist_count(user):
    return WishlistItem.objects.filter(user=user).count()


def item_data(item):
    return {
        "id": item.pk,
        "note": item.note,
        "created_at": item.created_at.isoformat(),
        "product": product_card_data(item.product),
    }


def wishlist_context(request, invalid_item=None, invalid_form=None):
    items = (
        WishlistItem.objects.filter(user=request.user)
        .select_related("product", "product__seller")
        .prefetch_related("product__images")
    )
    total = items.count()
    category = request.GET.get("category", "")
    if category in dict(Product.CATEGORY_CHOICES):
        items = items.filter(product__category=category)
    else:
        category = ""
    rows = [(item, invalid_form if item.pk == invalid_item else WishlistNoteForm(instance=item, auto_id="note-%s-" + str(item.pk))) for item in items]
    return {
        "rows": rows,
        "items": items,
        "total": total,
        "selected_category": category,
        "categories": Product.CATEGORY_CHOICES,
    }


@login_required
def wishlist(request, invalid_item=None, invalid_form=None, status=200):
    return render(request, "wishlist.html", wishlist_context(request, invalid_item, invalid_form), status=status)


def wants_json(request):
    return "application/json" in request.headers.get("Accept", "")


def wishlist_redirect(request, fallback="product_catalog:wishlist"):
    target = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        target = reverse(fallback)
    return redirect(target)


@login_required
@require_POST
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    item = WishlistItem.objects.filter(user=request.user, product=product).first()
    desired = request.POST.get("in_wishlist")
    if desired not in (None, "true", "false"):
        return JsonResponse({"success": False, "message": "Status wishlist tidak valid."}, status=400)
    active = (not bool(item)) if desired is None else desired == "true"
    if active:
        if not item:
            get_object_or_404(Product.objects.public(), pk=product_id)
            WishlistItem.objects.get_or_create(user=request.user, product=product)
    else:
        WishlistItem.objects.filter(user=request.user, product=product).delete()
    if wants_json(request):
        return JsonResponse({"success": True, "product_id": product.pk, "in_wishlist": active,
                             "count": wishlist_count(request.user),
                             "message": "Ditambahkan ke wishlist." if active else "Dihapus dari wishlist."})
    return wishlist_redirect(request, "product_catalog:katalog")


@login_required
@require_POST
def update_note(request, item_id):
    item = get_object_or_404(WishlistItem, pk=item_id, user=request.user)
    form = WishlistNoteForm(request.POST, instance=item, auto_id="note-%s-" + str(item.pk))
    if not form.is_valid():
        if wants_json(request):
            return JsonResponse({"success": False, "message": "Catatan gagal disimpan.",
                                 "errors": form.errors.get_json_data()}, status=400)
        return wishlist(request, invalid_item=item.pk, invalid_form=form, status=400)
    form.save()
    if wants_json(request):
        return JsonResponse({"success": True, "note": item.note, "message": "Catatan disimpan."})
    return wishlist_redirect(request)


@login_required
@require_POST
def remove_item(request, item_id):
    item = get_object_or_404(WishlistItem, pk=item_id, user=request.user)
    product_id = item.product_id
    item.delete()
    if wants_json(request):
        return JsonResponse({"success": True, "product_id": product_id, "in_wishlist": False,
                             "count": wishlist_count(request.user), "message": "Dihapus dari wishlist."})
    return wishlist_redirect(request)


@login_required
@require_GET
def wishlist_json(request):
    context = wishlist_context(request)
    items = (
        WishlistItem.objects.filter(user=request.user)
        .select_related("product", "product__seller")
        .prefetch_related("product__images")
    )
    return JsonResponse({
        "success": True,
        "message": "OK",
        "count": len(items),
        "html": page_html(request, "wishlist.html", context, "product_catalog:wishlist"),
        "items": [item_data(item) for item in items],
    })