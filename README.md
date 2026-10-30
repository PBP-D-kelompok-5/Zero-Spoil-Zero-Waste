# 🧟‍♂️ Pantry Necromancer: Resurrecting Leftovers, Banishing Food Waste

> Platform web gaya hidup berkelanjutan berbasis Django untuk mata kuliah Pemrograman Berbasis Platform (CSGE602022), Fakultas Ilmu Komputer, Universitas Indonesia (Semester Gasal 2026/2027).

---

## 🔗 Tautan Penting
* **Deployment (PWS):** https://michael-evan51-pantry-necromancer.pws.cs.ui.ac.id/
* **Desain UI/UX (Figma):** [Tautan Prototipe Desain Figma]
* **Repositori Git:** https://github.com/PBP-D-kelompok-5/Zero-Spoil-Zero-Waste
* **Akun demo:** username `[isi]` · password `[isi]` — sudah berisi data Death Clock & Graveyard

---

## 👥 Anggota Kelompok & Pembagian Modul
**Kelas / Kelompok:** [PBP D / Kelompok 5]

| Nama | NPM | Modul yang Dikerjakan |
| :--- | :--- | :--- |
| **Michael Evan Putra Nugroho** | 2506616674 | **Modul 1:** Pantry Death Clock (Manajemen Inventaris Bahan Makanan Pribadi) |
| **Nuno Mikael Nugroho** | 2506624865 | **Modul 2:** Recipe Alchemist (Penyelamat Resep & Integrasi Spoonacular API) |
| **Joshua Carnsyn Suyanto Sidik** | 2506593821 | **Modul 3:** The Dead Drop (Platform Berbagi Makanan Lokal & OpenStreetMap API) |
| **Adam Wahyu Syaputra** | 2506534964 | **Modul 4:** The Graveyard & Waste Analytics (Pencatatan Limbah & Analitik Dampak) |
| **Muhammad Syarifudin** | 2506657112 | **Modul 5:** Preservation Grimoire & Smell Test (Wiki Pengawetan & Uji Kelayakan Pangan) |

---

## 📖 Deskripsi Aplikasi & Manfaat bagi Masyarakat
Limbah makanan rumah tangga menyumbang hampir 40% dari total sampah makanan dunia. Mahasiswa dan perantau yang tinggal di kamar sewa (*kost*) merupakan salah satu kelompok rentan akibat kebiasaan belanja yang tidak terencana, jadwal perkuliahan yang padat, serta minimnya kepercayaan diri dalam mengolah sisa bahan masakan di kulkas bersama. Bahan makanan segar sering kali membusuk tanpa disadari, menimbulkan kerugian finansial sekaligus memicu emisi gas metana di tempat pembuangan akhir.

**Pantry Necromancer** hadir sebagai solusi berbasis *food triage* yang digamifikasi. Melalui pemantauan masa kedaluwarsa secara visual ("Death Clock"), rekomendasi resep darurat dari sisa bahan makanan, hingga fitur berbagi bahan berlebih dengan sesama penghuni kost terdekat, platform ini membantu pengguna memaksimalkan nilai konsumsi setiap bahan pangan sebelum terbuang sia-sia ke tempat sampah.

---

## 🎯 Target Pengguna & Peran Pengguna (User Roles)

### Target Pengguna
* **Mahasiswa & Anak Kost:** Individu dengan keterbatasan ruang penyimpanan, anggaran belanja ketat, dan fasilitas dapur bersama.
* **Pekerja Muda & Pemula Masak:** Individu yang ingin menghemat pengeluaran bulanan dan mengurangi jejak karbon tanpa sistem perencanaan makan yang rumit.

### Peran Pengguna (User Roles)
1. **Pengunjung Umum (Guest / Unregistered):**
   * Menjelajahi katalog resep umum, melihat basis pengetahuan pengawetan makanan komunitas, dan mencari panduan keamanan pangan dasar.
   * Tidak dapat menyimpan inventaris pribadi, memublikasikan bahan makanan untuk dibagikan, atau mencatat riwayat pembuangan makanan.
2. **Pengguna Terdaftar (Registered User / "Necromancer"):**
   * Mengakses modul inventaris bahan makanan pribadi dengan pelacak urgensi kedaluwarsa ("Death Clock").
   * Membuat resep darurat kustom berdasarkan sisa bahan yang ada di inventaris.
   * Mengunggah, memesan (*reserve*), dan mengklaim (*claim*) surplus bahan makanan pada papan berbagi komunitas lokal.
   * Mencatat bahan makanan yang terbuang serta melihat analitik personal terkait estimasi kerugian uang dan jejak karbon ($CO_2$).
3. **Administrator / Moderator:**
   * Mengelola dan meninjau unggahan bahan makanan yang dilaporkan pada papan berbagi komunitas serta memoderasi artikel pengawetan yang dikirimkan pengguna.

---

## 📦 Rincian Modul (Implementasi CRUD Lengkap)

Setiap modul dikembangkan secara independen oleh satu anggota kelompok dan memenuhi seluruh standar implementasi CRUD (Create, Read, Update, Delete), pemisahan pola Model-View-Template, penanganan formulir (*forms*), otentikasi pengguna, serta interaktivitas asinkronus AJAX/HTMX:

### 1. Pantry Death Clock (Inventaris Bahan Makanan Pribadi) — *Michael Evan Putra Nugroho*
* **Deskripsi:** Dasbor utama bagi pengguna untuk mengelola inventaris bahan makanan pribadi sebelum melewati batas kelayakan konsumsi.
* **Model:** Menyimpan nama bahan, tanggal pembelian, estimasi kedaluwarsa, jumlah/kuantitas, kategori, tempat simpan, serta status peluruhan dinamis (`Stable`, `Critical`, `Flatlining`, atau `Resurrected` bila sudah diolah).
* **Fitur CRUD:**
  * **Create:** Menambahkan bahan makanan baru secara satuan atau melalui input massal terpisah koma.
  * **Read:** Menampilkan daftar bahan makanan yang diurutkan berdasarkan sisa hari kedaluwarsa.
  * **Update:** Memperbarui jumlah bahan, memperpanjang estimasi tanggal kedaluwarsa, atau mengubah kategori.
  * **Delete:** Menghapus bahan makanan yang telah dimasak/dikonsumsi atau menandainya sebagai berhasil diselamatkan.
* **Interaktivitas:** Seluruh CRUD berjalan lewat AJAX tanpa memuat ulang halaman (modal tambah/ubah, filter & pencarian langsung). Aksi cepat memakai *optimistic UI*: jumlah, "Sudah diolah", dan hapus langsung berubah di layar lalu dikembalikan bila server menolak. JavaScript dipecah per bagian sebagai ES module (`static/death_clock/modules/`).
* **Otentikasi & keamanan:** Data privat per pengguna (bahan milik orang lain → 404); tamu melihat halaman pengenalan; endpoint yang mengubah data dibatasi per pengguna per menit (`rate_limit` di `main/auth.py`, 429 + `Retry-After`), begitu pula percobaan login yang gagal.
* **Data contoh:** Tombol "Isi 50 bahan contoh" pada inventaris kosong (mis. akun demo di PWS) atau command `seed_death_clock`.

### 2. Recipe Alchemist (Penyelamat Resep & Integrasi API Publik) — *Nuno Mikael Nugroho*
* **Deskripsi:** Mesin pencari resep yang mencocokkan bahan yang diketik dan isi inventaris Death Clock dengan resep dari Spoonacular, koleksi pribadi, dan resep komunitas.
* **Model:** Satu model `Recipe` untuk semua jenis resep: kustom buatan pengguna atau disimpan dari Spoonacular (`source`), dengan bahan, langkah memasak, waktu masak, diet, catatan pribadi, dan status publik/pribadi (`is_public`). Resep yang disimpan dari API berfungsi sebagai *bookmark* yang tetap bisa diubah, dan catatan modifikasi memasak ada di field `notes`. Satu resep API hanya bisa disimpan sekali per pengguna (`UniqueConstraint`).
* **Halaman & fitur CRUD:**
  * **Create:** Tulis resep kustom (`/recipes/baru/`) atau simpan hasil pencarian Spoonacular dengan satu klik.
  * **Read:** Cari resep, Koleksi saya, Komunitas (resep yang dipublikasikan semua pengguna), dan halaman detail.
  * **Update:** Ubah judul, bahan, langkah, waktu masak, diet, catatan pribadi, dan status publik, termasuk pada resep yang disimpan dari API.
  * **Delete:** Hapus resep milik sendiri (hanya lewat `POST`).
* **Pencarian:** Bahan diambil dari input pengguna dan, bila dicentang, dari bahan aktif di Death Clock (bahan yang sudah "Resurrected" tidak ikut). Hasil lokal (koleksi sendiri + komunitas, diurutkan berdasarkan jumlah bahan yang cocok) tampil di atas hasil Spoonacular. Nama bahan berbahasa Indonesia diterjemahkan lewat kamus kecil karena Spoonacular memakai bahasa Inggris. Filter: waktu masak maksimum dan preferensi diet.
* **Integrasi API:** Spoonacular `findByIngredients` + `informationBulk` (lihat tabel API di bawah).
* **Interaktivitas:** Tombol "Simpan resep" memakai `fetch` (AJAX): kartu langsung berubah menjadi "Tersimpan" tanpa memuat ulang halaman. Pencarian dan filter memakai form `GET` sehingga URL hasil bisa dibagikan. Tanpa JavaScript, tombol simpan tetap bekerja lewat `POST` biasa.
* **Otentikasi & keamanan:** Tamu boleh mencari dan melihat resep komunitas; menulis atau menyimpan resep butuh login. Resep pribadi milik pengguna lain dan semua aksi ubah/hapus milik orang lain mengembalikan `404`. Catatan pribadi tidak tampil pada resep publik.

### 3. The Dead Drop (Berbagi Makanan Lokal / Anak Kost) — *Joshua Carnsyn Suyanto Sidik*
* **Deskripsi:** Papan berbagi berbasis komunitas mikro bagi penghuni kost atau tetangga untuk membagikan sisa bahan makanan mentah sebelum kedaluwarsa.
* **Model:** Menyimpan nama dan deskripsi makanan, owner dari post, user yang mereservasi, lokasi dan jadwal penjemputan, titik temu notes, latitude, longitude, status listing, dan informasi waktu (pembuatan, update, dan klaim)

flow status: Available > Reserved > Claimed
* **Fitur CRUD:**
  * **Create:** Memublikasikan daftar sisa bahan makanan yang siap dijemput oleh pengguna lain. Field owner diisi berdasarkan akun yang login dan bukan dari input user.
  * **Read:** User dapat melihat listing berdasarkan status (available, reserved, claimed). Untuk available dapat dilihat semua orang, sedangkan status lain hanya bisa dilihat oleh owner dan pembuat reservasi. Masing masing di halaman terpisah.
  * **Update:** Owner dapat mengubah informasi postingannya. Batasan edit adalah field owner, reserved by, dan status. Hanya bisa dilakukan owner.
  * **Reserve dan cancel** User yang sudah login dan bukan owner dapat reserve listing yang available. User dan Owner dapat membatalkan reservasi.
  * **Claim** Jika makanan berhasil diantar owner dapat menandai postinganntya sebagai claimed.
  * **Delete:** Owner dapat membatalkan posting tersedia. Listing yang di claim tidak bisa dihapus
* **Integrasi API & Interaktivitas:** 
  * **Peta dan geocoding:** Map menggunakan Leaflet dengan tile OpenStreetMap. Pencarian alama,latitude,dan longitude menggunakan Nominatim. Hasil geocoding yang berhasil disimpan di cache selama 24 jam; pencarian lokasi yang tidak ditemukan di cache selama 5 menit. Permintaan geocoding yang belum tersimpan di cache dibatasi maksimal satu permintaan per detik. Peta show marker listing `Available` dan `Reserved` yang dapat dilihat pengguna. Listing `Claimed` tidak ditampilkan pada peta. Setiap marker dapat menampilkan nama makanan dan lokasi penjemputan.

  * **Interaktivitas dan keamanan:** Reserve, cancel, claim, edit, dan delete menggunakan HTMX agar jika ada update user tidak perlu refresh page. Perubahan status dilakukan dengan pembaruan database bersyarat, sehingga hanya satu permintaan yang berhasil mereservasi atau mengklaim listing yang memenuhi status awal. Fitur selain melihat listing available yang memerlukan autentikasi, dan izin perubahan diperiksa berdasarkan pemilik atau pengguna yang mereservasi.


### 4. The Graveyard & Waste Analytics (Pencatatan Limbah & Pelacak Dampak) — *Adam Wahyu Syaputra*
* **Deskripsi:** Modul akuntabilitas untuk mencatat bahan makanan yang gagal diselamatkan dan mengonversinya ke dalam metrik kerugian finansial (Rp), estimasi jejak karbon ($CO_2e$), serta kartu refleksi limbah (*"The Haunting Wrapped: Bisikan Arwah Pangan"*).
* **Model:** Model `GraveyardItem` menyimpan relasi ke pengguna, nama bahan, kategori, alasan pembuangan (`EXPIRED`, `FORGOTTEN`, `SPOILED_EARLY`, `SMELL_TEXTURE`, `MOLD`, `OVERCOOKED`, `OTHER`), catatan tambahan, tanggal kedaluwarsa, tanggal dibuang, jumlah dan satuan, estimasi berat dalam gram (`weight_g`), serta estimasi kerugian uang (`estimated_loss`). Dilengkapi properti terhitung untuk estimasi berat efektif (memakai konversi gram default per satuan bila berat tidak diisi langsung) dan faktor emisi karbon per kategori pangan (`CARBON_FACTORS_PER_KG`), serta custom QuerySet (`GraveyardItemQuerySet`) untuk agregasi total kerugian dan berat limbah.
* **Halaman & fitur CRUD:**
  * **Create:** Mencatat bahan makanan terbuang secara manual (`/graveyard/create/`) atau memindahkan langsung bahan yang sudah kedaluwarsa dari inventaris Death Clock (`/graveyard/move/<pantry_item_id>/`) lewat `BuryForm`.
  * **Read:** Menampilkan daftar nisan bahan terbuang (tabel pada desktop dan kartu pada tampilan HP), kartu ringkasan analitik bulanan & total akumulasi (item bulan ini, kategori paling sering terbuang, total kerugian Rp, dan jejak karbon $CO_2e$), carousel refleksi *"The Haunting Wrapped"* (`graveyard/wrapped.py`), serta endpoint JSON (`/graveyard/json/`).
  * **Update:** Memperbarui data catatan nisan limbah (`/graveyard/<pk>/edit/`), termasuk nama bahan, kategori, alasan pembuangan, jumlah, berat, dan estimasi harga beli/kerugian.
  * **Delete:** Menghapus riwayat pembuangan jika terjadi kesalahan pencatatan (`/graveyard/<pk>/delete/`, hanya lewat `POST`).
* **Interaktivitas:** Pencarian langsung (*debounced* 300 ms dengan `AbortController`) dan pemfilteran instan berdasarkan kategori, alasan pembuangan, serta rentang tanggal pembuangan (`date_from` s.d. `date_to`) berjalan lewat `fetch` (AJAX) tanpa memuat ulang halaman dan tetap memperbarui URL. Penghapusan item memakai modal konfirmasi di dalam halaman (*Grim Reaper modal*) dengan animasi pelenyapan baris/kartu, serta langsung memperbarui angka jumlah item dan kartu ringkasan analitik di layar. Carousel *Haunting Wrapped* berjalan otomatis dengan indikator *progress bar* dan tombol jeda/lanjut.
* **Otentikasi & keamanan:** Riwayat pembuangan bersifat privat per pengguna; tamu melihat halaman pengenalan modul (`graveyard/guest.html`), sedangkan akses atau aksi ubah/hapus/pindah terhadap data milik pengguna lain mengembalikan `404`.

### 5. Preservation Grimoire & Smell Test (Basis Pengetahuan & Uji Sensori) — *Muhammad Syarifudin*
* **Deskripsi:** Ensiklopedia interaktif mengenai teknik pengawetan bahan makanan dan panduan uji sensori ("The Smell Test") guna mencegah pembuangan makanan prematur akibat kebingungan label kedaluwarsa.
* **Model:** Menyimpan artikel tips pengawetan, indikator kelayakan sensori (bau, tekstur, tampilan), dan data dukungan komunitas (*upvotes*).
* **Fitur CRUD:**
  * **Create:** Menulis panduan pengawetan baru, trik pembekuan (*freezing*), atau metode penyimpanan bahan.
  * **Read:** Membaca dan mencari panduan keamanan pangan berdasarkan kategori.
  * **Update:** Memperbarui konten panduan agar metode pengawetan lebih akurat.
  * **Delete:** Menghapus panduan yang dibuat oleh pengguna yang bersangkutan.
* **Interaktivitas & Otentikasi:** Fitur *upvote* interaktif berbasis AJAX tanpa memuat ulang laman; pencarian dan pemfilteran instan berdasarkan kategori bahan dan metode pengawetan.

---

## 🌐 Public API & Sumber Data

| Sumber | Dipakai oleh | Kegunaan | Dokumentasi |
| :--- | :--- | :--- | :--- |
| **Spoonacular Food API** | Recipe Alchemist | `GET /recipes/findByIngredients` untuk mencari resep dari sisa bahan, lalu `GET /recipes/informationBulk` untuk durasi memasak, diet, dan tautan sumber | https://spoonacular.com/food-api/docs |
| **OpenStreetMap Nominatim** | The Dead Drop | Geocoding nama atau alamat lokasi di Indonesia menjadi latitude dan longitude untuk marker peta | [Dokumentasi Nominatim](https://nominatim.org/release-docs/latest/api/Overview/) |

**Penanganan data eksternal (Spoonacular)**
* Dipanggil dari server (`recipe_alchemist/services.py`), sehingga API key tidak pernah sampai ke browser.
* Hasil disimpan di cache server selama 6 jam per kombinasi pencarian untuk menghemat kuota; respons galat tidak di-cache.
* Timeout 15 detik. Galat jaringan, kuota habis, atau API key kosong ditampilkan sebagai pesan yang rapi, dan hasil dari koleksi lokal/komunitas tetap ditampilkan.

**Data awal**
* Death Clock: data sintetis dari katalog 50 bahan dapur umum (kategori, satuan, tempat simpan, dan umur simpan kasar per bahan) dengan tanggal beli acak relatif terhadap hari ini, sehingga status Stable/Critical/Flatlining/Resurrected tersebar realistis. Karena inventaris bersifat privat, data dibuat per akun: `python manage.py seed_death_clock <username>` (butuh akses shell) atau tombol "Isi 50 bahan contoh" di halaman Death Clock yang masih kosong (bisa dipakai langsung di PWS).
* Recipe Alchemist: resep berasal dari Spoonacular dan dari resep yang ditulis pengguna.
* `[isi: sumber data awal modul lain bila ada]`

---

## 🛠️ Teknologi & Struktur Proyek

* **Backend:** Django 5 (pola Model–View–Template), PostgreSQL di produksi, SQLite di lokal.
* **Frontend:** template Django + Tailwind CSS (CDN) + design system bersama di `static/css/global.css` (token warna, tombol, kartu, form, badge). Interaktivitas memakai `fetch` (AJAX).
* **Deployment:** PWS Fasilkom UI, Gunicorn + WhiteNoise, CI/CD lewat GitHub Actions.

```
PantryNecromancer/      # settings & URL utama
main/                   # landing page, autentikasi, alur login bersama
death_clock/            # Modul 1
recipe_alchemist/       # Modul 2
dead_drop/              # Modul 3
graveyard/              # Modul 4
preservation_grimoire/  # Modul 5
templates/              # base.html, partials/ (header, footer, messages, form_field), 404/500, template per modul
static/                 # css/global.css, js/tailwind.config.js, aset per modul
```

---

## 💻 Menjalankan Secara Lokal

Prasyarat: Python 3.12 atau lebih baru, Git.

```bash
git clone https://github.com/PBP-D-kelompok-5/Zero-Spoil-Zero-Waste.git
cd Zero-Spoil-Zero-Waste

python -m venv env
# Windows: env\Scripts\activate    |    macOS/Linux: source env/bin/activate
pip install -r requirements.txt

# buat file .env (lihat tabel variabel di bawah), minimal:
#   PRODUCTION=False
#   SPOONACULAR_API_KEY=<key-kamu>

python manage.py migrate
python manage.py createsuperuser          # opsional, untuk /admin/
python manage.py runserver
```

Buka http://127.0.0.1:8000/, daftar akun, lalu isi data contoh:

```bash
python manage.py seed_death_clock <username> --count 50
```

### Variabel lingkungan

| Variabel | Lokal | Produksi (Environs PWS) | Keterangan |
| :--- | :--- | :--- | :--- |
| `PRODUCTION` | `False` | `True` | `True` = DEBUG mati, PostgreSQL, cookie hanya lewat HTTPS |
| `SPOONACULAR_API_KEY` | opsional | wajib | Tanpa key, pencarian Spoonacular menampilkan pesan galat yang rapi |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | — | wajib | Koneksi PostgreSQL PWS |
| `SCHEMA` | — | `tugas_kelompok` | Schema PostgreSQL |

Jangan commit file `.env` / `.env.prod`; keduanya sudah ada di `.gitignore`.

---

## ✅ Testing

```bash
python manage.py test                       # seluruh unit test
pip install coverage
coverage run --source=. --omit="*/migrations/*,*/tests.py,*/tests/*,env/*" manage.py test
coverage report
```

Setiap modul punya unit test untuk model, form, view (termasuk akses tanpa login, akses ke data milik pengguna lain, dan respons AJAX/JSON).

**Functional test (browser sungguhan, Playwright)** ada di `playwright_checks/`: alur pengguna dijalankan di Chromium terhadap server Django (CRUD lewat AJAX, optimistic UI, tampilan HP 375/320 px, isolasi data, XSS).

```bash
pip install -r playwright_checks/requirements.txt
playwright install chromium
python manage.py test playwright_checks -p "check_*.py"
```

---

## 🚀 Deployment & CI/CD

* Workflow `.github/workflows/deploy.yml` berjalan setiap ada push ke `main` dan meneruskan kode ke PWS (secret repositori `PWS_URL`).
* Alur kerja tim: setiap fitur dikerjakan di branch sendiri → Pull Request → di-review anggota lain → merge ke `main` → deploy otomatis.
* Pengaturan produksi dan lokal dipisahkan lewat variabel `PRODUCTION`.

---

## 🔐 Alur Autentikasi Bersama

Semua modul memakai aturan yang sama (`main/auth.py`):
* Halaman/aksi yang butuh login → diarahkan ke `/login/?next=<halaman asal>`; permintaan AJAX/JSON mendapat respons `401` berisi `login_url`.
* Halaman daftar yang datanya privat (Death Clock, Graveyard, Koleksi resep) menampilkan halaman pengenalan modul untuk tamu.
* Data milik pengguna lain dianggap tidak ada (`404`); aksi yang mengubah data hanya lewat `POST` dengan CSRF; parameter `next` hanya boleh mengarah ke situs ini.

---

## 🤖 Penggunaan AI

Kami menggunakan alat AI selama pengembangan. Setiap anggota bertanggung jawab memahami, menguji, dan dapat menjelaskan seluruh kode di modulnya, termasuk bagian yang dibuat dengan bantuan AI.

| Anggota | Alat | Dipakai untuk | Strategi prompt | Batasan yang ditemui & perbaikan manual |
| :--- | :--- | :--- | :--- | :--- |
| Michael Evan Putra Nugroho | Claude (aplikasi Claude, mode Cowork) | Kerangka awal Django & design system v1, landing page + autentikasi, implementasi Modul Death Clock beserta test, audit progres & keamanan tim, penyeragaman alur autentikasi lintas modul (`main/auth.py`), perbaikan tampilan Grimoire, form "kubur" Graveyard, halaman 404/500, diagnosis galat deployment | Memberi spesifikasi tugas, palet & struktur folder yang diinginkan, batasan (Bahasa Indonesia, AI tidak boleh melakukan aksi Git), lalu meminta AI menjalankan test dan menunjukkan bukti sebelum perubahan diterapkan | AI sempat mengubah line ending file menjadi CRLF sehingga diff PR membengkak; usulan memindahkan `SECRET_KEY` dibatalkan sesuai arahan dosen; AI tidak dapat mengakses log PWS dan CDN Tailwind sehingga pengecekan dilakukan manual. Seluruh commit, review, dan konfigurasi PWS dilakukan sendiri. |
| Nuno Mikael Nugroho | Claude | Kerangka awal template HTML untuk halaman Recipe Alchemist, bantu menulis tes, implementasi integrasi API Spoonacular dan mengatur pembatasannya, perbaikan bug pada implementasi form, menambahkan komen-komen pembantu | Memberi ide yang ingin diimplementasi, lalu menggunakan kode yang diberi AI sebagai contoh awal serta meminta menjelaskan dan memperbaiki bug jika ditemukan. | Claude awalnya mengintegrasi API Spoonacular pada search form dengan menampilkan 24 resep dan ini cepat menghabiskan kuota API-nya sehingga harus diganti menjadi angka yang lebih kecil (dipilih angka 12). Commit dan review di github dilakukan sendiri. |
| Joshua Carnsyn Suyanto Sidik | Chat Gpt 6 Luna medium | Membantu dalam design, test, flow tdd, logika penggunaan api openStreetMap (penamilan map, geocoding,  dan javascriptnya). Untuk design css sebagian besar dilakukan oleh AI tetapi kerangka utama seperti informasi yang harus di tampilkan dan flow dari page dead drop dibuat sendiri. | Dalam setiap sesi selalu diawali dengan pernyataan ulang peran AI tersebut, recap terakhir sampai dimana, dan menyuruh AI membaca ulang seluruh code pada folder. Saat ingin melakukan sesuatu prompt akan berisi 3 bagian utama: context, information, task. Dengan ini AI dapat mengerti tanpa ambiguitas. Selain ini dalam prompt ada juga penambahan batasan dimana AI tidak boleh mengedit langsung dan memberi code secara langsung. Dikarenakan ini dibuat dengan codex maka AI rawan mengubah code tanpa izin yang membuat user dapat kebingungan dan tidak mengerti code. | Saat mengaplikasikan openStreetMap API untuk menampilkan map pada halaman dead drop, map menunjukkan error 403. Disini saya membuat perbaikan manual dengan menelusuri terms of condition dari penggunaan API tersebut. Yang ternyata kode yang dibuat oleh AI tidak mengirim header referer yang dibutuhkan tile. Hal ini dikarenkana referrer policy django membatasi header itu sendiri saat meminta ke domain lain. Sehingga dapat diperbaiki dengan mengatur kebijakannya agar situs dikirim ke server openstreemap dan memakai url resmi |
| Adam Wahyu Syaputra | Gemini (Google Antigravity) | Kerangka awal template HTML halaman Graveyard, bantu menyusun perhitungan agregasi analitik kerugian dan jejak karbon, implementasi filter pencarian AJAX dan modal konfirmasi hapus, serta membantu menulis unit test dan komentar penjelas | Memberi ide fitur yang ingin diimplementasi beserta struktur modelnya, menggunakan kode contoh yang diberikan sebagai acuan awal, lalu meminta penjelasan alur kode serta perbaikan ketika ditemukan bug saat diuji coba. | Kode awal untuk carousel *Haunting Wrapped* sempat membuat slide bertumpuk saat pergantian dan tombol pause ikut ter-reset ketika kursor keluar dari kartu, sehingga tata letak dan penyimpanan state pause harus diperbaiki. Pencocokan kata kunci bahan pada teks refleksi juga sempat salah mendeteksi kata umum (seperti suku kata `mi` pada kata `misterius`) sehingga logika pencocokan dan unit test disesuaikan kembali. Commit dan review di GitHub dilakukan sendiri. |
| Muhammad Syarifudin | `[isi]` | `[isi]` | `[isi]` | `[isi]` |
