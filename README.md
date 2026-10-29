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
* **Deskripsi:** Mesin pencari resep cerdas yang mencocokkan sisa bahan makanan di inventaris dengan resep masakan praktis untuk meminimalkan sisa pangan.
* **Model:** Menyimpan resep darurat kustom buatan pengguna, resep yang disimpan/diberi markah (*bookmarks*), dan catatan modifikasi memasak.
* **Fitur CRUD:**
  * **Create:** Menulis resep penyelamat kustom baru atau menyimpan resep hasil pencarian API publik.
  * **Read:** Menelusuri dan membaca resep masakan dari API eksternal maupun resep komunitas.
  * **Update:** Memperbarui langkah-langkah memasak, takaran bahan, atau catatan pribadi pada resep.
  * **Delete:** Menghapus resep yang telah disimpan atau resep kustom pribadi.
* **Integrasi API & Filter:** Terintegrasi dengan **Spoonacular Food API** (*endpoint* `/recipes/findByIngredients`). Mendukung pemfilteran dinamis berdasarkan ketersediaan bahan, durasi memasak maksimum, dan preferensi diet.

### 3. The Dead Drop (Berbagi Makanan Lokal / Anak Kost) — *Joshua Carnsyn Suyanto Sidik*
* **Deskripsi:** Papan berbagi berbasis komunitas mikro bagi penghuni kost atau tetangga untuk membagikan sisa bahan makanan mentah sebelum kedaluwarsa.
* **Model:** Menyimpan data unggahan surplus makanan, catatan titik temu/penjemputan, koordinat geografis, serta status klaim (`Available`, `Reserved`, `Claimed`).
* **Fitur CRUD:**
  * **Create:** Memublikasikan daftar sisa bahan makanan yang siap dijemput oleh pengguna lain.
  * **Read:** Melihat papan pengumuman bahan makanan komunitas terdekat.
  * **Update:** Mengubah jadwal penjemputan, deskripsi kondisi makanan, atau status klaim.
  * **Delete:** Membatalkan unggahan sebelum ada pengguna lain yang mengklaim.
* **Integrasi API & Interaktivitas:** Integrasi dengan **OpenStreetMap (Nominatim API)** untuk pemetaan lokasi titik temu. Dilengkapi mekanisme penguncian asinkronus (*AJAX claim button*) agar bahan makanan yang diklaim tidak dapat diambil ganda.

### 4. The Graveyard & Waste Analytics (Pencatatan Limbah & Pelacak Dampak) — *Adam Wahyu Syaputra*
* **Deskripsi:** Modul akuntabilitas untuk mencatat bahan makanan yang gagal diselamatkan dan mengonversinya ke dalam metrik kerugian finansial serta dampak lingkungan.
* **Model:** Menyimpan relasi pengguna dengan bahan yang dibuang, estimasi harga beli bahan, tanggal pembuangan, dan alasan kegagalan konsumsi (contoh: "terlupa di sudut kulkas").
* **Fitur CRUD:**
  * **Create:** Mencatat bahan makanan kedaluwarsa langsung dari inventaris ke dalam modul Graveyard.
  * **Read:** Menampilkan riwayat pembuangan serta visualisasi metrik akumulasi kerugian uang dan estimasi emisi $CO_2$.
  * **Update:** Memperbarui data catatan pembuangan, harga beli, atau alasan pembuangan.
  * **Delete:** Menghapus riwayat pembuangan jika terjadi kesalahan pencatatan.
* **Interaktivitas & Otentikasi:** Akses privat terotentikasi per pengguna; dilengkapi penyaringan data dinamis (*HTMX/AJAX*) berdasarkan rentang tanggal dan kategori bahan makanan (Sayur, Produk Susu, Daging, Makanan Kering).

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
| **OpenStreetMap Nominatim** | The Dead Drop | Geocoding alamat titik temu menjadi koordinat peta | https://nominatim.org/release-docs/latest/api/Overview/ |

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
| Nuno Mikael Nugroho | `[isi]` | `[isi]` | `[isi]` | `[isi]` |
| Joshua Carnsyn Suyanto Sidik | `[isi]` | `[isi]` | `[isi]` | `[isi]` |
| Adam Wahyu Syaputra | `[isi]` | `[isi]` | `[isi]` | `[isi]` |
| Muhammad Syarifudin | `[isi]` | `[isi]` | `[isi]` | `[isi]` |
