# 🧟‍♂️ Pantry Necromancer: Resurrecting Leftovers, Banishing Food Waste

> Platform web gaya hidup berkelanjutan berbasis Django untuk mata kuliah Pemrograman Berbasis Platform (CSGE602022), Fakultas Ilmu Komputer, Universitas Indonesia (Semester Gasal 2026/2027).

---

## 🔗 Tautan Penting
* **Deployment (PWS):** [Tautan Deployment PWS - Diperbarui pada Checkpoint 2]
* **Desain UI/UX (Figma):** [Tautan Prototipe Desain Figma]
* **Repositori Git:** https://github.com/PBP-D-kelompok-5/Zero-Spoil-Zero-Waste

---

## 👥 Anggota Kelompok & Pembagian Modul
**Kelas / Kelompok:** [PBP D / Kelompok 5]

| Nama | NPM | Modul yang Dikerjakan |
| :--- | :--- | :--- |
| **Michael Evan Putra Nugroho** | 2506616674 | **Modul 1:** Pantry Death Clock (Manajemen Inventaris Bahan Makanan Pribadi) |
| **Nuno Mikael Nugroho** | 2506624865 | **Modul 2:** Recipe Alchemist (Penyelamat Resep & Integrasi Spoonacular API) |
| **Joshua Carnsyn Suyanto Sidik** | 2506593821 | **Modul 3:** The Dead Drop (Platform Berbagi Makanan Lokal & OpenStreetMap) |
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
* **Model:** Menyimpan nama bahan, tanggal pembelian, estimasi kedaluwarsa, jumlah/kuantitas, kategori, serta status peluruhan dinamis (`Stable`, `Critical`, atau `Flatlining`).
* **Fitur CRUD:**
  * **Create:** Menambahkan bahan makanan baru secara satuan atau melalui input massal terpisah koma.
  * **Read:** Menampilkan daftar bahan makanan yang diurutkan berdasarkan sisa hari kedaluwarsa.
  * **Update:** Memperbarui jumlah bahan, memperpanjang estimasi tanggal kedaluwarsa, atau mengubah kategori.
  * **Delete:** Menghapus bahan makanan yang telah dimasak/dikonsumsi atau menandainya sebagai berhasil diselamatkan.
* **Interaktivitas & Otentikasi:** Pembaruan status bahan makanan tanpa memuat ulang halaman (*AJAX/HTMX*); data bersifat privat dan hanya dapat diakses oleh pengguna terotentikasi.

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
