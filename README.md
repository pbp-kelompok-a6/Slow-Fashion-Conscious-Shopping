## Slow Fashion & Conscious Shopping
### LaPAKAIAN — Gaya Berkelanjutan, Peduli Lingkungan

Proyek Tengah Semester — Mata Kuliah Pemrograman Berbasis Platform (PBP)
Fakultas Ilmu Komputer, Universitas Indonesia — Kelompok A-6

## Deskripsi Aplikasi

LaPAKAIAN adalah sebuah marketplace sederhana untuk jual-beli baju thrift/preloved secara online, dibangun di bawah payung tema besar Sustainable Living.

Baju bekas yang sebenarnya masih layak pakai sering kali berakhir menjadi sampah karena pemiliknya tidak tahu harus dijual ke mana. Di sisi lain, banyak calon pembeli yang ingin belanja lebih hemat sekaligus ramah lingkungan, tetapi kesulitan menemukan tempat jual-beli baju bekas yang rapi dan terpercaya.

Aplikasi ini menjembatani kedua kebutuhan tersebut: memberi wadah bagi penjual untuk melepas baju bekas mereka secara terstruktur (lengkap dengan detail ukuran, kondisi, dan kategori), sekaligus memudahkan pembeli menemukan, menyaring, dan menyimpan baju yang mereka minati — sehingga siklus hidup pakaian menjadi lebih panjang dan sampah fashion berkurang.

## Anggota Kelompok A-6

| Nama | NPM |
|---|---|
| Naurah Claradinda Aulia Pane | 2506657163 |
| Emil Ananta Kautsar | 2506622121 |
| Joanna Prittavidya Putri Arianto | 2506539265 |
| Razan Muhammad Fathin Lesmana | 2506603646 |
| Goeij Angelatika Goeyanto | 2506656772 |

## Jenis/Peran Pengguna

- **Seller (Penjual)** — pengguna yang memiliki baju bekas masih layak pakai dan ingin menjualnya daripada dibuang.
- **Buyer (Pembeli)** — pengguna yang ingin membeli baju bagus dengan harga lebih murah sekaligus mengurangi sampah fashion.

Peran dipilih saat registrasi dan disimpan dalam model profile yang terhubung ke model User bawaan Django. Setelah login, pengguna diarahkan sesuai perannya: Seller → halaman My Listings, Buyer → halaman katalog/wishlist.

## Sumber Mock API

Aplikasi memakai mock API buatan sendiri berisi data size chart per brand (misalnya brand X ukuran M = lingkar dada sekian, panjang sekian). Data ini dipakai di halaman detail produk agar pembeli tahu ukuran pasti sebelum membeli, dan bisa difilter berdasarkan brand.

## Daftar Modul & Pembagian Kerja

### 1. Landing Page & Autentikasi — Naurah

Halaman pertama yang dilihat pengguna serta alur pendaftaran akun.

- **Landing Page**: hero section (banner & tagline), produk unggulan yang diambil dari data yang sudah diinput penjual, daftar kategori produk yang bisa diklik menuju katalog, serta tombol call-to-action "Shop Now" dan "Jadi Seller".
- **Registrasi Akun**: pengguna baru mendaftar dan memilih peran Seller atau Buyer. Peran disimpan di model profile yang terhubung ke model User Django.
- **Pengarahan Berdasarkan Peran**: setelah login, sistem mengarahkan pengguna ke halaman sesuai perannya (Seller → My Listings, Buyer → katalog/wishlist).

### 2. Manajemen Produk (Sisi Seller) — Emil, Joanna

CRUD penuh atas listing baju milik penjual, dengan filter berbasis autentikasi (hanya pemilik yang bisa mengelola listing-nya).

- **Create**: mengisi form tambah baju (nama, brand, size, kondisi, harga, foto, kategori) lalu publish.
- **Read**: melihat daftar baju yang dijual sendiri (My Listings) — difilter berdasarkan autentikasi, hanya pemilik yang bisa melihat.
- **Update**: mengedit baju miliknya sendiri (misalnya mengubah harga atau status jadi "sold").
- **Delete**: menghapus listing baju miliknya sendiri.

### 3. Katalog & Wishlist (Sisi Buyer) — Razan, Angel

Eksplorasi produk secara publik ditambah pengelolaan wishlist pribadi.

- **Create**: pengguna yang sudah login dapat menyimpan baju ke wishlist dengan menekan tombol "Simpan", opsional menambahkan catatan/prioritas pribadi.
- **Read**: menjelajah seluruh baju thrift secara publik (tanpa perlu login), melakukan pencarian/filter berdasarkan kategori, brand, ukuran, kondisi, dan harga, serta membuka halaman detail tiap baju. Pengguna yang login juga bisa melihat wishlist miliknya sendiri.
- **Update**: mengubah catatan/prioritas pada produk yang tersimpan di wishlist (opsional).
- **Delete**: menghapus baju dari wishlist miliknya sendiri.

## Tautan

- **Repository**: https://github.com/pbp-kelompok-a6/Slow-Fashion-Conscious-Shopping