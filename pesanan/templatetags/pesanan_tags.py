from django import template

from pesanan.presentation import availability, cart_state

register = template.Library()


@register.inclusion_tag("pesanan/partials/cart_button.html", takes_context=True)
def cart_button(context, product):
    request = context["request"]
    return {"request": request, "product": product, "user": request.user,
            "state": availability(product), "in_cart": product.pk in cart_state(request)["ids"],
            "is_owner": request.user.is_authenticated and request.user.pk == product.seller_id}
