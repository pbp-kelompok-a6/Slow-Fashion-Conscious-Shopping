from .presentation import cart_state


def navigation(request):
    state = cart_state(request)
    return {"cart_purchasable_count": len(state["available_ids"]),
            "pesanan_has_sales": request.user.is_authenticated and request.user.sales.exists()}
