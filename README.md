## LaPAKAIAN — Gaya Berkelanjutan, Peduli Lingkungan

Proyek Tengah Semester — Mata Kuliah Pemrograman Berbasis Platform (PBP)
Fakultas Ilmu Komputer, Universitas Indonesia — Kelompok A-6

## Deskripsi Aplikasi

LaPAKAIAN adalah marketplace sederhana tempat orang menjual dan membeli baju thrift/preloved secara online, dibangun di bawah payung tema besar Sustainable Living.

Baju bekas yang sebenarnya masih layak pakai sering kali berakhir menjadi sampah karena pemiliknya tidak tahu harus dijual ke mana. Di sisi lain, banyak calon pembeli yang ingin belanja lebih hemat sekaligus ramah lingkungan, tetapi kesulitan menemukan tempat jual-beli baju bekas yang rapi dan terpercaya.

Aplikasi ini menjembatani kedua kebutuhan tersebut lewat satu akun untuk semua pengguna. Setiap pengguna bisa langsung menjelajah katalog dan menyimpan baju favorit ke wishlist, sekaligus punya opsi untuk mulai berjualan kapan saja tanpa perlu akun terpisah. Dengan begitu, siklus hidup pakaian menjadi lebih panjang dan sampah fashion berkurang.

## Anggota Kelompok A-6

| Nama | NPM |
|---|---|
| Naurah Claradinda Aulia Pane | 2506657163 |
| Emil Ananta Kautsar | 2506622121 |
| Joanna Prittavidya Putri Arianto | 2506539265 |
| Razan Muhammad Fathin Lesmana | 2506603646 |
| Goeij Angelatika Goeyanto | 2506656772 |

## Jenis/Peran Pengguna

Aplikasi memakai **satu jenis akun** untuk semua pengguna (tidak ada pilihan role saat registrasi). Setiap pengguna bisa berperan sebagai:

- **Pengunjung (belum login)** — dapat menjelajah katalog, mencari/filter produk, dan membuka detail produk.
- **Buyer (Pembeli)** — peran default setelah login: menyimpan baju ke wishlist, menulis ulasan.
- **Seller (Penjual)** — peran tambahan yang diaktifkan lewat tombol "Jadi Seller". Setelah aktif, pengguna bisa mengelola listing baju dan profil tokonya.

Status seller disimpan sebagai field pada model Profile (terhubung ke model User bawaan Django), sehingga satu akun bisa menjadi buyer sekaligus seller.

## Sumber Public API / Mock API

Aplikasi memakai **mock API** buatan sendiri yang di-deploy terpisah dari proyek ini, berisi data size chart per brand (misalnya brand X ukuran M = lingkar dada sekian, panjang sekian). Data ini ditampilkan di halaman detail produk agar pembeli tahu ukuran pasti sebelum membeli, dan bisa difilter berdasarkan brand.

- Tautan mock API: *(isi setelah di-deploy)*

## Daftar Modul & Pembagian Kerja

Setiap anggota mengerjakan satu modul berbeda dengan CRUD lengkap.

### 1. Akun, Profil & Landing Page — Naurah

- **Model:** Profile (terhubung ke User bawaan Django)
- **Views:** registrasi, lihat profil, edit profil, hapus akun, toggle status seller, plus endpoint JSON profil
- **Form:** form registrasi dan form edit profil
- **Interaktivitas:** toggle "Jadi Seller"/nonaktifkan tanpa reload halaman (AJAX)
- **Filter autentikasi:** halaman profil, edit, dan hapus akun hanya bisa diakses pemilik akun yang sudah login
- **Filter data:** menu "My Listings"/"Toko Saya" di navbar hanya muncul kalau status seller aktif

### 2. Listing Baju — Angel

- **Model:** Product (+ ProductImage kalau foto lebih dari satu)
- **Views:** tambah, lihat (My Listings + Detail Produk), edit, hapus listing, plus endpoint JSON daftar produk
- **Form:** form Tambah/Edit listing
- **Interaktivitas:** hapus listing dan tandai "Sold" tanpa reload halaman (AJAX)
- **Filter autentikasi:** hanya seller pemilik yang bisa membuka My Listings dan tombol edit/hapus
- **Filter data:** My Listings bisa difilter per status (Aktif/Terjual) dan kategori

### 3. Profil Toko & Size Chart — Emil

- **Model:** Store, SizeChart (per brand)
- **Views:** buka toko, lihat Profil Toko, edit profil, tutup toko, plus CRUD size chart dan endpoint JSON-nya
- **Form:** form Buka/Edit toko dan form size chart
- **Interaktivitas:** tab Semua/Tersedia/Terjual di Profil Toko berganti isi tanpa reload (AJAX)
- **Filter autentikasi:** tombol "Chat via WhatsApp" (nomor seller) hanya muncul untuk pengguna yang sudah login
- **Filter data:** produk di Profil Toko difilter Tersedia/Terjual

### 4. Katalog & Wishlist — Razan

- **Model:** WishlistItem (menggunakan Product milik modul Listing Baju)
- **Views:** Katalog (browse publik), tambah ke wishlist, lihat wishlist, edit catatan, hapus dari wishlist, plus endpoint JSON wishlist
- **Form:** form catatan per item wishlist
- **Interaktivitas:** ikon hati pada kartu produk toggle tanpa reload (AJAX)
- **Filter autentikasi:** ikon hati dan halaman Wishlist hanya untuk pengguna login; tiap pengguna hanya melihat wishlist miliknya sendiri
- **Filter data:** Katalog difilter berdasarkan brand, ukuran, kondisi, harga, plus sorting

### 5. Ulasan — Joanna

- **Model:** Review (terhubung ke Product atau Store)
- **Views:** tambah ulasan, lihat daftar ulasan di Detail Produk, edit ulasan sendiri, hapus ulasan sendiri, plus endpoint JSON ulasan
- **Form:** form tambah/edit ulasan (rating + komentar)
- **Interaktivitas:** submit ulasan langsung muncul di daftar tanpa reload (AJAX)
- **Filter autentikasi:** hanya pengguna login yang bisa menulis ulasan; hanya pemilik ulasan yang bisa mengedit/menghapus miliknya
- **Filter data:** ulasan bisa di-sort berdasarkan terbaru atau rating tertinggi

**Dikerjakan bersama:** base.html, header.html, footer.html, halaman Masuk/Daftar, dan halaman 404. Token warna, font, dan radius di-set sekali di konfigurasi framework CSS (Tailwind/Bootstrap), lalu dipakai bersama oleh seluruh modul agar tampilan konsisten dan responsif.

## Tautan

- **Repository:** https://github.com/pbp-kelompok-a6/Slow-Fashion-Conscious-Shopping
- **Deployment PWS:** https://naurah-claradinda-lapakaian.pws.cs.ui.ac.id/
- **Desain Figma:** *https://www.figma.com/design/usJgJikXCZoeA01cEsmww9/LaPAKAIAN?node-id=0-1&t=5A4BHUBT5zdI4J0A-1*