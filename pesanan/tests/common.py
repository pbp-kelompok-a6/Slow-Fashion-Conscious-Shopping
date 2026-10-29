from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from akun.models import Profile
from listing.models import Product
from pesanan.models import CartItem
from pesanan.services import quote


class Fixtures:
    def make_data(self):
        User = get_user_model()
        self.buyer = User.objects.create_user("buyer4")
        self.other = User.objects.create_user("other4")
        self.seller = User.objects.create_user("seller4")
        self.seller2 = User.objects.create_user("seller24")
        for user in [self.buyer, self.other, self.seller, self.seller2]:
            Profile.objects.get_or_create(user=user, defaults={"is_seller": user in [self.seller, self.seller2]})
        self.p = self.product(self.seller, "Linen", "100.25")
        self.p2 = self.product(self.seller2, "Denim", "200.50")

    def product(self, seller, name, price):
        return Product.objects.create(seller=seller, name=name, description="Snapshot deskripsi", price=Decimal(price), category="atasan", condition="good", size="M", brand="Local")

    def payload(self, products=None, buyer=None, key="attempt-0001", method="cod"):
        buyer = buyer or self.buyer
        products = products or [self.p]
        ids = sorted(p.pk for p in products)
        for p in products:
            CartItem.objects.get_or_create(user=buyer, product=p)
        return ids, {"recipient_name": "Pembeli", "phone": "081234567890", "address": "Jalan Panjang nomor 12, Jakarta",
                     "payment_method": method, "idempotency_key": key, "quote_token": quote(buyer.pk, ids)["quote_token"]}

    def post(self, name, data=None, args=None, client=None):
        return (client or self.client).post(reverse("pesanan:" + name, args=args), data=data or {}, content_type="application/json")
