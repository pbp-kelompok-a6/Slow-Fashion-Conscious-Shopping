from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import template

from listing.models import Product

register = template.Library()


def format_rupiah(value):
    """Rupiah with significant cents preserved, e.g. Rp85.000,25."""
    if value is None or value == "":
        return ""
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return value
    sign = "-" if amount < 0 else ""
    whole, fraction = f"{abs(amount):,.2f}".split(".")
    return f"{sign}Rp{whole.replace(',', '.')}" + (f",{fraction}" if fraction != "00" else "")


@register.filter
def rupiah(value):
    return format_rupiah(value)


@register.simple_tag
def product_categories():
    """Daftar (value, label) kategori produk, dipakai di navbar dan footer."""
    return Product.CATEGORY_CHOICES
