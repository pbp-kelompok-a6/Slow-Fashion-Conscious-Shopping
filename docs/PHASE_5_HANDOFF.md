# Phase 5 ? UI dan integrasi pesanan

## Hasil dan baseline

Branch aktif tetap `checkout`. Sebelum implementasi, Phase 4 sudah berupa perubahan lokal yang belum di-commit; perubahan tersebut dipertahankan. Baseline `check` bersih dan 37 test lolos. Tidak checkout, commit, push, merge, seed database lokal, atau deployment.

Referensi `C:/Users/Razan/Slow-Fashion-Claude-Test` tidak ditemukan. UI memakai warna krem/ink, garis tegas, tombol persegi, font dan pola visual repository aktif. Tidak mengklaim kesamaan visual dengan referensi yang tidak tersedia.

Enam halaman tersedia: keranjang, konfirmasi checkout, checkout success, pesanan saya, pesanan masuk, detail order. Buyer dapat memilih barang dari beberapa toko, mengisi alamat, memilih pembayaran simulasi, konfirmasi, membatalkan sebelum dikirim, lalu menyelesaikan pesanan setelah diterima. Seller dapat memfilter penjualan dan menandai dikirim. Semua transisi tetap melalui service atomik Phase 4.

## Halaman dan API

| Halaman | URL |
| --- | --- |
| Keranjang | `/pesanan/keranjang/` |
| Checkout | `/pesanan/checkout/konfirmasi/?product_ids=1&product_ids=2` |
| Success | `/pesanan/checkout/berhasil/<order_id>/` |
| Pesanan saya | `/pesanan/pembelian/` |
| Pesanan masuk | `/pesanan/penjualan/` |
| Detail order | `/pesanan/detail/<order_id>/` |

URL HTML ini ditambahkan di `pesanan/urls.py`. Seluruh URL API Phase 4 tetap mengembalikan JSON dengan kontrak semula. `Accept: application/json` pada URL halaman HTML mengembalikan `{success, html}` berisi partial halaman tanpa script; dipakai filter, pagination, dan refresh setelah mutation. Route dan nama route diuji tidak duplikat.

Success dimulai dari salah satu order yang dikembalikan backend, kemudian menampilkan seluruh order dalam attempt yang sama. Hanya buyer pemilik yang dapat mengakses success. Detail order hanya buyer/seller bersangkutan; daftar pembelian dan penjualan dipisahkan melalui query kepemilikan, bukan filter client. Filter status dan pagination bekerja dengan GET biasa maupun AJAX.

## Keranjang, komponen, dan arti badge

`{% cart_button product %}` di `pesanan/templatetags/pesanan_tags.py` merender komponen `pesanan/partials/cart_button.html`. Komponen dipakai detail produk dan wishlist, termasuk HTML hasil AJAX wishlist.

State yang dirender:
- Anonymous: link masuk dengan next menuju halaman asal.
- Owner: label listing milikmu, tanpa tombol beli.
- Available: form tambah keranjang.
- Sudah dalam cart: link Di keranjang.
- Sold: label Terjual; barang dalam cart masih dapat dibuka/dihapus.
- Seller inactive: label Seller nonaktif.

Badge **menghitung listing dalam cart user yang saat ini bisa dibeli**: active, seller aktif, harga positif, bukan produk sendiri, dan tidak memiliki klaim order aktif. Barang unavailable tetap disimpan dalam cart agar dapat dihapus, tetapi tidak masuk badge atau pilihan checkout. `cart.count` API Phase 4 tetap berarti jumlah seluruh row cart; UI AJAX menghitung jumlah `items[].available` dan menggunakan definisi yang sama dengan context processor server. Tidak menambah field atau mengubah arti count backend lama.

Navbar menyediakan keranjang, pesanan saya, dan pesanan masuk. Menu pesanan masuk tetap tersedia bagi pemilik riwayat penjualan meskipun mode seller sudah dinonaktifkan, sehingga kewajiban order tidak tersembunyi.

## Konfirmasi dan retry

Server membentuk ringkasan dari service quote Phase 4. Harga satuan pada UI berasal dari payload quote yang ditandatangani, bukan pembacaan harga kedua yang mungkin sudah berubah. Ongkir tetap Rp15.000 per seller; total dan alamat snapshot tetap ditentukan backend. Pecahan harga ditampilkan akurat (`Rp100,25`) di UI bersama.

`checkout_state.js` menyimpan payload lengkap **sebelum** mengirim request, dalam sessionStorage yang dipisahkan per user. Data pending hanya bertahan di tab tersebut sampai hasil dikonfirmasi atau penolakan definitif diterima. Payload mencakup ID, token quote, alamat, metode, dan kunci attempt yang sama. ID besar tetap berupa string desimal agar tidak dibulatkan JavaScript.

- Double submit memakai satu request yang sedang berjalan; tombol dinonaktifkan dan loading ditampilkan.
- Jaringan terputus, respons tidak lengkap, HTTP 5xx, login expired, atau CSRF 403 mempertahankan payload asli. Panel recovery menampilkan tombol retry dengan data yang sama. Reload tetap dapat retry meskipun cart sudah kosong karena checkout sebelumnya sebenarnya berhasil.
- Respons sukses harus berasal dari API checkout attempt itu sendiri; UI tidak menyimpulkan sukses hanya dari cart kosong.
- Quote berubah/expired dan konflik availability menampilkan alasan, menonaktifkan konfirmasi ringkasan lama, dan menyediakan link memperbarui ringkasan. Konfirmasi berikutnya dilakukan terhadap ringkasan terbaru.
- Error field ditampilkan di dekat input dan fokus diarahkan ke field bermasalah. Error 403 menawarkan reload; 401 menuju login-next. Konflik transisi memuat ulang status server sebelum aksi berikutnya.
- Jika sessionStorage tidak dapat ditulis, submit memakai form POST biasa dengan hidden idempotency key. Cart add/remove, checkout, filter order, dan transisi memiliki form/link native sebagai fallback.
- Logout melalui navbar menggunakan POST+CSRF. Login menjaga next dari GET/POST dengan validasi host dan skema.

Transfer, e-wallet, dan COD selalu diberi label simulasi. COD ditampilkan belum dibayar saat checkout/dikirim dan dibayar dalam simulasi setelah complete, mengikuti backend.

## AJAX, refresh, dan state server

Handler `pesanan.js` dipasang sekali pada document dan memakai event delegation. Partial tidak memuat script, dan tidak bergantung pada eksekusi script dalam DOMParser. MutationObserver mendeteksi penggantian `.pc-page` oleh script katalog/wishlist lalu merekonsiliasi badge dan state cart.

Filter/pagination pesanan memakai sequence + AbortController agar respons lama tidak menimpa pilihan baru. Refresh cart mempertahankan pilihan yang masih tersedia. State badge diambil kembali setelah mutation. Add/remove di detail/wishlist merekonsiliasi slot dari server. Kembali lewat back/forward cache memperbarui cart/page/slot; badge status detail juga diperbarui dari HTML server. Setelah checkout atau cancel, load ulang katalog, wishlist, cart, dan detail memakai status produk/claim terbaru dari server.

Asset katalog yang di branch ini masih menunjuk `phase2.css`/`phase3.js` (file tidak tersedia) diarahkan ke file aktual `product_catalog.css`/`product_catalog.js`. Assertion asset existing diperbarui mengikuti referensi nyata; coverage existing tidak dihapus. Partial shared kartu produk yang hilang ditambahkan untuk mencegah crash detail yang memiliki beberapa produk terkait. Tidak memasang dependency ulasan atau tombol review.

## File Phase 5

App pesanan:
- `pesanan/page_views.py` ? adapter HTML, fallback POST, ownership, filter/pagination.
- `pesanan/presentation.py` ? availability, cart state/grouping, quote presentation.
- `pesanan/context_processors.py` ? badge dan menu riwayat seller.
- `pesanan/templatetags/__init__.py`, `pesanan/templatetags/pesanan_tags.py` ? komponen reusable.
- `pesanan/urls.py` ? hanya tambahan URL UI, API lama tetap.
- `pesanan/templates/pesanan/{cart,checkout,success,orders,order_detail}.html` ? wrappers base.
- `pesanan/templates/pesanan/partials/{cart,cart_button,checkout,success,orders,order_card,order_detail}.html` ? konten dan komponen.
- `pesanan/static/pesanan/{pesanan.css,pesanan.js,checkout_state.js}` ? gaya responsif, delegated handlers, retry state.
- `pesanan/tests/test_pages.py`, `pesanan/tests/checkout_state.test.cjs`, `pesanan/tests/browser_check.py`, `pesanan/tests/browser_flow.cjs` ? verifikasi.

File bersama / modul lain:
- `lapakaian/settings.py` ? satu context processor.
- `templates/base.html` ? title block, navbar/badge, messages, config, pemuatan aset sekali.
- `templates/partials/product_card.html` ? partial dependency detail yang belum tersedia.
- `akun/views.py`, `akun/templates/akun/login.html` ? safe login-next dan POST logout; guard hapus akun Phase 4 dipertahankan.
- `listing/templates/listing/product_detail.html` ? slot cart, link kembali/toko nyata, hindari memuat script listing yang tidak ada.
- `listing/templatetags/format_tags.py` ? format pecahan harga akurat.
- `product_catalog/templates/{katalog,wishlist}.html` ? referensi aset aktual; wishlist menambah slot cart dan link detail.
- `product_catalog/tests.py` ? dua assertion nama asset yang dikoreksi.
- `docs/PHASE_5_HANDOFF.md` ? laporan ini.

Core Phase 4 `models.py`, `services.py`, `guards.py`, `views.py`, `validation.py`, dan migration identik dengan snapshot awal Phase 5. Tidak ada migration baru di Phase 5 atau file ulasan yang diubah. Perubahan Phase 4 yang sudah ada pada `listing/views.py`, `akun/templates/akun/profil.html`, dan include project URL tidak ditimpa. Laporan Phase 4 yang hilang dari working tree selama sesi tidak dibuat ulang otomatis.

## Verifikasi

Perintah lokal:

```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\venv\Scripts\python.exe manage.py test --settings=pesanan.test_settings --noinput
node --test pesanan/tests/checkout_state.test.cjs
node --check pesanan/static/pesanan/pesanan.js
node --check pesanan/static/pesanan/checkout_state.js
.\venv\Scripts\python.exe manage.py test pesanan.tests.browser_check --settings=pesanan.test_settings --noinput
git diff --check
```

Suite Django: **48 tests** (37 baseline termasuk 8 konkurensi SQLite nyata + 11 halaman/integrasi). Node: **7 tests** double submit, lost response/reload, 401/403/5xx, konflik definitif, isolasi user, storage failure, dan presisi ID besar. Browser opt-in: **1 flow test Edge headless** memakai Node WebSocket/CDP bawaan, tanpa Playwright atau dependency download.

Browser flow benar-benar menjalankan:
1. Anonymous detail ? login ? kembali ke detail ? tambah cart.
2. Filter wishlist lewat AJAX ? tombol cart dari fragment ? badge dua barang.
3. Keranjang empat barang, hanya dua dapat dipilih (sold + seller inactive tidak dapat dipilih).
4. Desktop 1280?900 dan mobile 375?812; cart/checkout mobile tanpa overflow horizontal.
5. Checkout dua seller dengan double submit; hanya satu POST awal.
6. CDP memutus **respons setelah transaksi server selesai**, lalu reload halaman, retry payload identik, dan success berisi dua order. Total dua POST checkout, bukan dua transaksi baru. DB akhir diverifikasi hanya dua order.
7. Buyer membatalkan satu order ? katalog menampilkan kembali barangnya; wishlist barang order lain tetap unavailable.
8. Login seller ? filter processing lewat AJAX ? ship; login buyer ? complete COD ? paid_simulated.
9. Runtime JavaScript error: **0**. Kegagalan HTTP lokal tak terduga: **0**. Favicon dan respons yang sengaja diputus tidak dihitung sebagai kegagalan tak terduga. Font eksternal diblokir agar test tidak bergantung koneksi luar.

Semua test memakai database/media sementara. Edge memakai profil sementara dan screenshots test sementara yang dibersihkan setelah run. Tidak menguji gateway/uang nyata. Warning WhiteNoise `staticfiles` belum ada merupakan kondisi baseline; collectstatic/deploy tidak dilakukan.

## Usulan commit terpisah

Jangan memasukkan ulang seluruh app Phase 4 ke commit UI secara tidak sengaja karena Phase 4 masih berupa perubahan lokal. Gunakan daftar file/hunk berikut dan tinjau staged diff.

1. **`feat(pesanan): add cart checkout and order pages with safe retry UI`**
   - Seluruh file Phase 5 di app pesanan pada daftar di atas, termasuk route UI baru pada `pesanan/urls.py`; jangan staging ulang hunk route/API Phase 4 sebagai perubahan Phase 5.
   - Test UI: `test_pages.py` (halaman, ownership, native checkout/validation, transisi, pagination), `checkout_state.test.cjs` (seluruh file).
2. **`feat(checkout): integrate cart controls navigation and login return flow`**
   - `templates/base.html`, `templates/partials/product_card.html`, hunk context processor `lapakaian/settings.py`.
   - Hunk login-next/logout `akun/views.py` dan hidden next `akun/templates/akun/login.html`; guard akun Phase 4 tetap kelompok commit backend.
   - `listing/templates/listing/product_detail.html`, `listing/templatetags/format_tags.py`.
   - `product_catalog/templates/katalog.html`, `product_catalog/templates/wishlist.html`, dua assertion asset `product_catalog/tests.py`.
   - Integration test methods pada `test_pages.py`: login-next, badge, slot state/AJAX, checkout/cancel refresh, CSRF/redirect, aset/route uniqueness. Stage hunk test bersama entry point bila membuat dua commit bertahap.
   - `browser_check.py`, `browser_flow.cjs`, dan laporan ini.

## Catatan integrator / menjalankan lokal

Daftarkan context processor bersamaan dengan base baru. Muat `checkout_state.js` sebelum `pesanan.js`, masing-masing sekali dengan defer. Template anak tidak perlu mengulang aset. Komponen cart membutuhkan app pesanan terpasang dan migration Phase 4 tersedia.

Migration Phase 4 belum diterapkan ke database lokal oleh tugas ini. Sebelum mengakses UI lokal, jalankan `.\venv\Scripts\python.exe manage.py migrate pesanan`, kemudian runserver. Namespace template katalog di branch ini masih struktur baseline `product_catalog/templates/katalog.html` dan `wishlist.html`; penyelarasan perubahan Phase 0?3 antarbranch tetap pekerjaan integrasi tersendiri.

Verifikasi manual tambahan yang disarankan: perangkat sentuh fisik, screen reader, sesi login yang benar-benar habis pada deployment, dan styling setelah font eksternal termuat. Alur inti sudah diverifikasi lewat browser headless; laporan tidak mengklaim pengujian perangkat fisik atau deployment.
