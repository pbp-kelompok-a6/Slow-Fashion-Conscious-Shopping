from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from listing.models import Product
from listing.utils import product_card_data
from .filters import (
    active_filter_chips, filter_options, filter_products, parse_filters, query_without_page,
)
from .forms import WishlistNoteForm
from .models import WishlistItem

PER_PAGE = 12


def paginate(request, queryset):
    return Paginator(queryset, PER_PAGE).get_page(request.GET.get("page"))


# ---------- Katalog ----------

def katalog(request):
    filters = parse_filters(request.GET)
    page_obj = paginate(request, filter_products(filters))
    chips = active_filter_chips(request.GET, filters)
    sort = request.GET.get("sort")
    return render(request, "product_catalog/katalog.html", {
        "page_obj": page_obj,
        "products": page_obj.object_list,
        "filters": filters,
        "options": filter_options(),
        "active_chips": chips,
        # Filter di sidebar (tidak termasuk pencarian & kategori) untuk tombol "Filter (n)" di mobile.
        "sidebar_count": len(filters["brand"]) + len(filters["size"]) + len(filters["condition"])
        + (filters["min_price"] is not None) + (filters["max_price"] is not None),
        "querystring": query_without_page(request.GET),
        "clear_url": f"?sort={sort}" if sort else "?",
    })


@require_GET
def katalog_json(request):
    filters = parse_filters(request.GET)
    page_obj = paginate(request, filter_products(filters))
    return JsonResponse({
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