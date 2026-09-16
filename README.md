## LaPAKAIAN — Gaya Berkelanjutan, Peduli Lingkungan

Proyek Tengah Semester — Mata Kuliah Pemrograman Berbasis Platform (PBP)
Fakultas Ilmu Komputer, Universitas Indonesia — Kelompok A-6

## Deskripsi Aplikasi

LaPAKAIAN adalah marketplace sederhana tempat orang menjual dan membeli baju thrift/preloved secara online, dibangun di bawah payung tema besar Sustainable Living.

Baju bekas yang sebenarnya masih layak pakai sering kali berakhir menjadi sampah karena pemiliknya tidak tahu harus dijual ke mana. Di sisi lain, banyak calon pembeli yang ingin belanja lebih hemat sekaligus ramah lingkungan, tetapi kesulitan menemukan tempat jual-beli baju bekas yang rapi dan terpercaya.

Aplikasi ini menjembatani kedua kebutuhan tersebut lewat satu akun untuk semua pengguna — mirip marketplace pada umumnya. Setiap pengguna bisa langsung menjelajah dan menyimpan baju favorit, sekaligus punya opsi untuk mulai berjualan kapan saja tanpa perlu akun terpisah, sehingga siklus hidup pakaian menjadi lebih panjang dan sampah fashion berkurang.

## Anggota Kelompok A-6

| Nama | NPM |
|---|---|
| Naurah Claradinda Aulia Pane | 2506657163 |
| Emil Ananta Kautsar | 2506622121 |
| Joanna Prittavidya Putri Arianto | 2506539265 |
| Razan Muhammad Fathin Lesmana | 2506603646 |
| Goeij Angelatika Goeyanto | 2506656772 |

## Jenis/Peran Pengguna
Aplikasi menggunakan **satu jenis akun** untuk seluruh pengguna (tidak ada pemilihan role terpisah saat registrasi). Setiap pengguna yang login otomatis bisa berperan sebagai:

- **Buyer (Pembeli)** — peran default setelah login: menjelajah katalog, mencari/filter produk, dan mengelola wishlist pribadi.
- **Seller (Penjual)** — peran tambahan yang bisa diaktifkan kapan saja lewat tombol "Jadi Seller" di navbar/profile. Setelah aktif, pengguna mendapat akses ke halaman My Listings untuk mengelola produk jualannya sendiri.

Status seller disimpan sebagai field pada model profile (terhubung ke model User bawaan Django), sehingga satu akun bisa berperan sebagai buyer sekaligus seller secara bersamaan.

## Sumber Mock API

Aplikasi memakai mock API buatan sendiri berisi data size chart per brand (misalnya brand X ukuran M = lingkar dada sekian, panjang sekian). Data ini dipakai di halaman detail produk agar pembeli tahu ukuran pasti sebelum membeli, dan bisa difilter berdasarkan brand.

## Daftar Modul & Pembagian Kerja

### 1. Landing Page & Autentikasi — Naurah

Halaman pertama yang dilihat pengguna serta alur pendaftaran akun.

- **Landing Page**: hero section (banner & tagline), produk unggulan yang diambil dari data yang sudah diinput penjual, daftar kategori produk yang bisa diklik menuju katalog, serta tombol call-to-action "Shop Now" dan "Jadi Seller".
- **Registrasi Akun**: pengguna baru mendaftar dengan satu jenis akun (tanpa pemilihan role di awal).
- **Aktivasi Peran Seller**: pengguna yang sudah login dapat mengaktifkan status seller lewat tombol "Jadi Seller"; status ini disimpan pada model profile dan membuka akses ke halaman My Listings.
- **Pengarahan Setelah Login**: pengguna login diarahkan ke halaman katalog/wishlist sebagai default. Menu "My Listings" hanya muncul untuk pengguna yang statusnya sudah seller.

### 2. Manajemen Produk (Sisi Seller) — Emil, Joanna

CRUD penuh atas listing baju milik penjual, dengan filter berbasis autentikasi (hanya pemilik yang bisa mengelola listing-nya).

- **Create**: mengisi form tambah baju (nama, brand, size, kondisi, harga, foto, kategori) lalu publish.
- **Read**: melihat daftar baju yang dijual sendiri (My Listings) — difilter berdasarkan autentikasi, hanya pemilik yang bisa melihat.
- **Update**: mengedit baju miliknya sendiri (misalnya mengubah harga atau status jadi "sold").
- **Delete**: menghapus listing baju miliknya sendiri.

### 3. Katalog & Keranjang (Sisi Buyer) — Razan, Angel

Eksplorasi produk secara publik ditambah pengelolaan keranjang pribadi.
- **Create**: pengguna yang sudah login dapat menyimpan baju ke keranjang dengan menekan tombol "Simpan".
- **Read**: menjelajah seluruh baju thrift secara publik (tanpa perlu login), melakukan pencarian/filter berdasarkan kategori, brand, ukuran, kondisi, dan harga, serta membuka halaman detail tiap baju. Pengguna yang login juga bisa melihat keranjang miliknya sendiri.
- **Update**: mengubah pilihan ukuran (size) pada item yang ada di keranjang, jika brand tersebut tersedia dalam beberapa ukuran.
- **Delete**: menghapus baju dari keranjang miliknya sendiri.

## Tautan

- **Repository**: https://github.com/pbp-kelompok-a6/Slow-Fashion-Conscious-Shopping