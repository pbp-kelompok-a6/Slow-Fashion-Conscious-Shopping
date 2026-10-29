
"""Data awal (50 produk) untuk semua modul, yang otomatis dibuat setiap kali `manage.py migrate` dijalankan.
 
Aman dijalankan berulang: data yang sudah ada tidak digandakan dan tidak ditimpa.
Dilewati saat `manage.py test` supaya database test tetap kosong.
Foto diambil dari media/product_images/dummy/<nama file>.jpg; produk yang fotonya
belum ada tetap dibuat dan tampil "Belum ada foto".
"""
import sys
from decimal import Decimal
from pathlib import Path
 
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils.text import slugify
 
PASSWORD = "DummyLapakaian123"
PHOTO_DIR = "product_images/dummy"
 
# (username, nama toko, kota, nomor WhatsApp)
SELLERS = [
    ("seller1", "Lemari Kedua", "Depok", "081234567801"),
    ("seller2", "Preloved Pojok", "Jakarta", "081234567802"),
    ("seller3", "Rak Sepatu Bekas", "Bandung", "081234567803"),
    ("seller4", "Butik Kedua", "Yogyakarta", "081234567804"),
    ("seller5", "Tas & Teman", "Surabaya", "081234567805"),
]
BUYERS = ["buyer1", "buyer2"]
 
# (seller, nama, brand, kategori, ukuran, kondisi, harga, deskripsi)
PRODUCTS = [
    ("seller1", "Linen blazer krem", "Uniqlo", "outerwear", "M", "like_new", "85000", "Blazer linen ringan warna krem, cocok untuk kerja atau kuliah. Baru dipakai dua kali, tanpa noda."),
    ("seller1", "Kemeja oversized putih", "Cotton On", "atasan", "M", "like_new", "55000", "Kemeja katun potongan oversized, bahan adem dan tidak menerawang."),
    ("seller1", "Trench coat beige", "Zara", "outerwear", "M", "good", "180000", "Trench coat klasik dengan sabuk, ada sedikit tanda pemakaian di ujung lengan."),
    ("seller1", "Cardigan rajut abu", "Uniqlo", "atasan", "L", "good", "70000", "Cardigan rajut tebal, kancing lengkap, nyaman untuk ruangan ber-AC."),
    ("seller1", "Blazer hitam slim fit", "Zara", "outerwear", "M", "like_new", "90000", "Blazer hitam formal, jahitan rapi, cocok untuk presentasi atau wawancara."),
    ("seller1", "Overshirt flanel kotak", "Cotton On", "atasan", "M", "good", "65000", "Overshirt flanel motif kotak merah, bisa dipakai sebagai luaran."),
    ("seller1", "Parka olive", "H&M", "outerwear", "L", "good", "150000", "Parka hijau olive dengan hoodie, resleting dan kancing berfungsi baik."),
    ("seller1", "Wool coat charcoal", "Mango", "outerwear", "M", "new", "220000", "Mantel wol abu tua, masih ada label, belum pernah dipakai."),
    ("seller1", "Kemeja linen biru muda", "Uniqlo", "atasan", "L", "good", "60000", "Kemeja linen lengan panjang, warna biru muda yang mudah dipadukan."),
    ("seller1", "Turtleneck rajut hitam", "H&M", "atasan", "S", "like_new", "50000", "Turtleneck rajut tipis, elastis, warna hitam masih pekat."),
    ("seller2", "501 jeans light wash", "Levi's", "bawahan", "30", "good", "120000", "Jeans 501 original warna light wash, potongan straight."),
    ("seller2", "Denim jacket washed", "Levi's", "outerwear", "M", "good", "110000", "Jaket denim washed, semua kancing lengkap, cocok gaya kasual."),
    ("seller2", "Wide leg trousers krem", "H&M", "bawahan", "L", "like_new", "60000", "Celana kulot wide leg berpinggang karet, bahan jatuh dan tidak kusut."),
    ("seller2", "Kaos putih basic", "Uniqlo", "atasan", "M", "good", "30000", "Kaos katun putih polos, kerah tidak melar, sudah dicuci bersih."),
    ("seller2", "Ribbed knit top hitam", "Zara", "atasan", "S", "good", "45000", "Atasan rajut ribbed lengan pendek, pas di badan."),
    ("seller2", "Celana chino khaki", "Uniqlo", "bawahan", "32", "good", "75000", "Chino khaki slim fit, cocok untuk kuliah maupun acara semi formal."),
    ("seller2", "Rok denim A-line", "Pull&Bear", "bawahan", "M", "like_new", "65000", "Rok denim A-line selutut, resleting depan berfungsi baik."),
    ("seller2", "Hoodie abu polos", "H&M", "atasan", "L", "good", "80000", "Hoodie fleece tebal tanpa sablon, kantong depan masih rapi."),
    ("seller2", "Mom jeans dark wash", "Levi's", "bawahan", "28", "good", "130000", "Mom jeans high waist warna gelap, belum pernah dipermak."),
    ("seller2", "Bomber jacket olive", "H&M", "outerwear", "M", "good", "130000", "Bomber jacket hijau olive dengan lapisan dalam oranye."),
    ("seller3", "Chuck 70 hitam", "Converse", "sepatu", "EU 39", "good", "250000", "Converse Chuck 70 high top, sol masih tebal, ada sedikit kotor di bagian karet."),
    ("seller3", "Stan Smith putih hijau", "Adidas", "sepatu", "EU 41", "good", "300000", "Adidas Stan Smith kulit putih dengan aksen hijau, sudah dicuci."),
    ("seller3", "Air Force 1 putih", "Nike", "sepatu", "EU 42", "fair", "350000", "Nike Air Force 1 putih, ada lipatan di bagian depan, sol masih kuat."),
    ("seller3", "Old Skool hitam putih", "Vans", "sepatu", "EU 40", "good", "280000", "Vans Old Skool klasik, tali dan insole masih bagus."),
    ("seller3", "Samba OG putih", "Adidas", "sepatu", "EU 40", "like_new", "650000", "Adidas Samba OG, baru dipakai tiga kali, lengkap dengan box."),
    ("seller3", "Loafers kulit coklat", "Pedro", "sepatu", "EU 41", "good", "220000", "Loafers kulit asli warna coklat, cocok untuk acara formal."),
    ("seller3", "Sandal gunung hitam", "Eiger", "sepatu", "EU 42", "good", "120000", "Sandal gunung dengan strap perekat, nyaman untuk jalan jauh."),
    ("seller3", "Slip-on kanvas krem", "Vans", "sepatu", "EU 38", "fair", "150000", "Slip-on kanvas krem, warna sedikit pudar tapi masih layak pakai."),
    ("seller3", "Ventela Public low hitam", "Ventela", "sepatu", "EU 41", "like_new", "180000", "Sneakers lokal Ventela Public low, jarang dipakai."),
    ("seller3", "Ankle boots hitam", "Zara", "sepatu", "EU 38", "good", "260000", "Ankle boots hak rendah dengan resleting samping."),
    ("seller4", "Midi dress motif bunga", "Mango", "dress", "S", "new", "150000", "Midi dress motif bunga kecil, masih ada label."),
    ("seller4", "Slip dress satin hijau", "Zara", "dress", "M", "like_new", "140000", "Slip dress satin hijau emerald, tali bahu bisa diatur."),
    ("seller4", "Kebaya modern putih", "Lokal", "dress", "M", "like_new", "175000", "Kebaya modern brokat putih, cocok untuk wisuda atau kondangan."),
    ("seller4", "Maxi dress linen terakota", "H&M", "dress", "L", "good", "120000", "Maxi dress linen warna terakota dengan kancing depan."),
    ("seller4", "Shirt dress denim", "Uniqlo", "dress", "M", "good", "110000", "Shirt dress denim tipis, bisa dipakai dengan sabuk."),
    ("seller4", "Rok plisket mocca", "Lokal", "bawahan", "All size", "good", "55000", "Rok plisket panjang warna mocca, pinggang karet."),
    ("seller4", "Blouse batik modern", "Batik Keris", "atasan", "M", "like_new", "95000", "Blouse batik motif modern, bahan katun halus."),
    ("seller4", "Dress rajut abu", "Uniqlo", "dress", "S", "good", "100000", "Dress rajut abu selutut, hangat dan tidak gatal."),
    ("seller4", "Rok midi satin hitam", "Mango", "bawahan", "S", "like_new", "85000", "Rok midi satin hitam, jatuh dan berkilau lembut."),
    ("seller4", "Wrap dress polkadot", "Zara", "dress", "M", "good", "115000", "Wrap dress polkadot hitam putih dengan tali pinggang."),
    ("seller5", "Tote bag kanvas natural", "Lokal", "tas", "One size", "good", "40000", "Tote bag kanvas tebal, muat laptop 14 inci."),
    ("seller5", "Ransel kulit coklat", "Fossil", "tas", "One size", "good", "450000", "Ransel kulit asli, resleting lancar, ada goresan halus."),
    ("seller5", "Sling bag nilon hitam", "Uniqlo", "tas", "One size", "like_new", "120000", "Sling bag nilon ringan dengan banyak kantong."),
    ("seller5", "Shoulder bag kulit hitam", "Charles & Keith", "tas", "One size", "good", "280000", "Shoulder bag kulit sintetis hitam, tali bisa dilepas."),
    ("seller5", "Topi baseball navy", "New Era", "aksesori", "One size", "good", "90000", "Topi baseball navy dengan strap belakang yang bisa diatur."),
    ("seller5", "Syal wol abu", "H&M", "aksesori", "One size", "like_new", "45000", "Syal wol lembut warna abu, panjang 180 cm."),
    ("seller5", "Sabuk kulit coklat", "Levi's", "aksesori", "90 cm", "good", "70000", "Sabuk kulit asli dengan gesper logam."),
    ("seller5", "Kacamata hitam aviator", "Ray-Ban", "aksesori", "One size", "good", "550000", "Kacamata aviator original lengkap dengan case."),
    ("seller5", "Jam tangan analog silver", "Casio", "aksesori", "One size", "good", "300000", "Jam tangan analog strap logam, baterai baru diganti."),
    ("seller5", "Beanie rajut krem", "Cotton On", "aksesori", "One size", "new", "35000", "Beanie rajut krem, masih ada label."),
]
 
 
def photo_name(number, product_name):
    """Path foto relatif terhadap MEDIA_ROOT, mis. product_images/dummy/01-linen-blazer-krem.jpg."""
    return f"{PHOTO_DIR}/{number:02d}-{slugify(product_name)}.jpg"
 
 
def seed_dummy_data(sender, **kwargs):
    if sys.argv[1:2] == ["test"]:
        return
 
    from django.contrib.auth import get_user_model
 
    from akun.models import Profile
    from listing.models import Product, ProductImage
    from profil_toko.models import Store
 
    User = get_user_model()
    with transaction.atomic():
        users = {}
        for username in [s[0] for s in SELLERS] + BUYERS:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.password = make_password(PASSWORD)
                user.save(update_fields=["password"])
            Profile.objects.get_or_create(user=user, defaults={"is_seller": username.startswith("seller")})
            users[username] = user
 
        for username, store_name, city, whatsapp in SELLERS:
            Store.objects.get_or_create(owner=users[username], defaults={
                "name": store_name, "city": city, "whatsapp_number": whatsapp})
 
        for number, (seller, name, brand, category, size, condition, price, description) in enumerate(PRODUCTS, start=1):
            product, _ = Product.objects.get_or_create(seller=users[seller], name=name, defaults={
                "brand": brand, "description": description, "category": category, "size": size,
                "condition": condition, "price": Decimal(price), "status": "active"})
            image = photo_name(number, name)
            if (Path(settings.MEDIA_ROOT) / image).exists():
                ProductImage.objects.get_or_create(product=product, image=image, defaults={"alt_text": name})