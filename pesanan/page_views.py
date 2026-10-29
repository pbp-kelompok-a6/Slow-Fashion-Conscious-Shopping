from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from . import services
from .models import Order
from .presentation import cart_groups, quote_groups
from .validation import CheckoutForm, DomainError, product_ids


def page(request, template, context, status=200):
    if "application/json" in request.headers.get("Accept", ""):
        return JsonResponse({"success": status < 400, "html": render_to_string(
            f"pesanan/partials/{template}.html", context, request=request)}, status=status)
    return render(request, f"pesanan/{template}.html", context, status=status)


@login_required
@require_GET
def cart(request):
    return page(request, "cart", {"groups": cart_groups(request)})


def checkout_context(request, params, form=None):
    context = {"checkout_form": form if form is not None else CheckoutForm(initial={"payment_method": "cod"}),
               "checkout_key": params.get("idempotency_key") or str(uuid4()), "quote_error": "", "groups": [], "selected_ids": []}
    try:
        ids = product_ids(params.getlist("product_ids"))
        quote = services.quote(request.user.pk, ids)
        context.update(quote=quote, groups=quote_groups(request, quote), selected_ids=ids)
    except DomainError as exc:
        context["quote_error"] = exc.message
    return context


@login_required
@require_GET
def checkout(request):
    # Even when the cart is empty after a lost checkout response, the recovery
    # panel can replay the saved request against the unchanged Phase 4 endpoint.
    return page(request, "checkout", checkout_context(request, request.GET))


@login_required
@require_POST
def checkout_submit(request):
    form = CheckoutForm(request.POST)
    try:
        ids = product_ids(request.POST.getlist("product_ids"))
        if not form.is_valid():
            return page(request, "checkout", checkout_context(request, request.POST, form), 400)
        result = services.checkout(request.user.pk, ids, form.cleaned_data)
    except DomainError as exc:
        context = checkout_context(request, request.POST, form)
        context["submit_error"] = exc.message
        return page(request, "checkout", context, exc.status)
    return redirect("pesanan:success_page", pk=result["orders"][0]["id"])


@login_required
@require_GET
def success(request, pk):
    try:
        pk = product_ids([pk])[0]
    except DomainError as exc:
        raise Http404 from exc
    first = get_object_or_404(Order, pk=pk, buyer=request.user)
    orders = first.attempt.orders.filter(buyer=request.user).select_related("seller").prefetch_related("items")
    return page(request, "success", {"orders": orders, "total": sum(o.total for o in orders)})


@login_required
@require_GET
def order_list(request, incoming=False):
    orders = Order.objects.filter(**{"seller" if incoming else "buyer": request.user}).select_related("buyer", "seller").prefetch_related("items").order_by("-created_at", "-pk")
    status = request.GET.get("status", "")
    if status not in Order.Status.values:
        status = ""
    if status:
        orders = orders.filter(status=status)
    return page(request, "orders", {"page_obj": Paginator(orders, 12).get_page(request.GET.get("page")),
        "statuses": Order.Status.choices, "selected_status": status, "incoming": incoming})


@login_required
@require_GET
def order_detail(request, pk):
    try:
        pk = product_ids([pk])[0]
    except DomainError as exc:
        raise Http404 from exc
    order = get_object_or_404(Order.objects.select_related("buyer", "seller").prefetch_related("items"), pk=pk)
    if request.user.pk not in (order.buyer_id, order.seller_id):
        raise Http404
    return page(request, "order_detail", {"order": order, "is_buyer": order.buyer_id == request.user.pk})


def safe_next(request, fallback):
    target = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        target = reverse(fallback)
    return target


@login_required
@require_POST
def cart_mutate(request, action):
    try:
        pk = product_ids([request.POST.get("product_id")])[0]
        operation = services.add_to_cart if action == "add" else services.remove_from_cart
        operation(request.user.pk, pk)
        messages.success(request, "Produk ditambahkan ke keranjang." if action == "add" else "Produk dihapus dari keranjang.")
    except DomainError as exc:
        messages.error(request, exc.message)
    return redirect(safe_next(request, "pesanan:cart_page"))


@login_required
@require_POST
def order_action(request, pk, action):
    try:
        pk = product_ids([pk])[0]
    except DomainError as exc:
        raise Http404 from exc
    try:
        services.transition(request.user.pk, pk, action)
        messages.success(request, "Status pesanan diperbarui.")
    except DomainError as exc:
        messages.error(request, exc.message)
    return redirect("pesanan:order_page", pk=pk)
