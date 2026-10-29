import re

from django import forms

from .models import Order

MAX_ID = 2**63 - 1
MAX_ITEMS = 100


class DomainError(Exception):
    def __init__(self, code, message, status=400):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


def product_ids(value):
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_ITEMS:
        raise DomainError("invalid_product_ids", "Pilih 1 sampai 100 produk dari keranjang.")
    result = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, str)):
            raise DomainError("invalid_product_ids", "ID produk harus bilangan bulat positif.")
        text = str(item)
        if len(text) > 19 or not re.fullmatch(r"[1-9][0-9]*", text) or int(text) > MAX_ID:
            raise DomainError("invalid_product_ids", "ID produk tidak valid atau terlalu besar.")
        result.append(int(text))
    if len(set(result)) != len(result):
        raise DomainError("duplicate_product_ids", "ID produk tidak boleh duplikat.")
    return sorted(result)


class CheckoutForm(forms.Form):
    recipient_name = forms.CharField(max_length=100)
    phone = forms.RegexField(r"^\+?[0-9 ()-]{7,25}$", max_length=25)
    address = forms.CharField(max_length=1000, min_length=10)
    payment_method = forms.ChoiceField(choices=Order.PaymentMethod.choices)
    idempotency_key = forms.RegexField(r"^[A-Za-z0-9_-]{8,80}$", max_length=80)
    quote_token = forms.CharField(max_length=30000)
