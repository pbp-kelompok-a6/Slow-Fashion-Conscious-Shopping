"""Opt-in real Edge test: manage.py test pesanan.tests.browser_check

Run with --settings=pesanan.test_settings. Uses only temporary DB/media/profile.
Not named test_* so ordinary test discovery does not launch a browser.
"""
import json
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from akun.models import Profile
from listing.models import Product
from pesanan.models import CartItem, Order
from product_catalog.models import WishlistItem
from profil_toko.models import Store
from .common import Fixtures

EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


@skipUnless(EDGE.is_file() and shutil.which("node"), "Local Edge and Node required")
class BrowserFlow(Fixtures, StaticLiveServerTestCase):
    def test_buyer_seller_mobile_and_lost_checkout_response(self):
        self.make_data()
        for user in [self.buyer, self.seller2]:
            user.set_password("Phase5-browser-password!")
            user.save()
        for seller in [self.seller, self.seller2]:
            Store.objects.create(owner=seller, name=f"Toko {seller.username}", city="Jakarta", whatsapp_number="081234567890")
        inactive = get_user_model().objects.create_user("inactive-browser")
        Profile.objects.create(user=inactive, is_seller=False)
        unavailable = self.product(inactive, "Seller nonaktif", "300.00")
        sold = self.product(self.seller, "Sudah terjual", "400.00")
        Product.objects.filter(pk=sold.pk).update(status="sold")
        CartItem.objects.create(user=self.buyer, product=unavailable)
        CartItem.objects.create(user=self.buyer, product=sold)
        WishlistItem.objects.create(user=self.buyer, product=self.p2)
        with TemporaryDirectory(prefix="lapakaian-browser-artifacts-") as artifacts:
            config = {"base": self.live_server_url, "edge": str(EDGE), "artifacts": artifacts,
                      "buyer": self.buyer.username, "seller": self.seller2.username,
                      "product": self.p.pk, "product2": self.p2.pk}
            result = subprocess.run(["node", str(Path(__file__).with_name("browser_flow.cjs")), json.dumps(config)],
                                    capture_output=True, text=True, encoding="utf-8", timeout=110)
            print(result.stdout)
            self.assertEqual(result.returncode, 0, result.stderr + "\n" + result.stdout)
        self.assertEqual(Order.objects.filter(buyer=self.buyer).count(), 2)
        self.assertEqual(set(Order.objects.filter(buyer=self.buyer).values_list("status", flat=True)), {"cancelled", "completed"})
