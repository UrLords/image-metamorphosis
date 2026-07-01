# Logbook Pengembangan Image Metamorphosis

## Identitas Project

**Nama project:** Image Metamorphosis  
**Domain produksi:** https://imagemeta.site  
**Repository:** https://github.com/UrLords/image-metamorphosis  
**Periode pengembangan:** 29 April 2026 - 25 Juni 2026  
**Stack utama:** React, TypeScript, Vite, Tailwind CSS, Flask, OpenCV, Firebase Authentication, Supabase PostgreSQL, Cloudinary, Vercel, Hostinger VPS, Nginx

## Ringkasan Project

Image Metamorphosis adalah aplikasi web edukatif untuk mempelajari dan mencoba berbagai teknik pengolahan citra digital secara interaktif. Aplikasi ini menyediakan fitur upload gambar, pemrosesan citra menggunakan OpenCV, visualisasi perbandingan sebelum dan sesudah, histogram RGB/luminance, serta penjelasan konsep dari setiap operasi.

Project ini berkembang dari aplikasi pengolahan citra dasar menjadi aplikasi web yang lebih lengkap dengan autentikasi Google, integrasi backend produksi, scan dokumen, dashboard fitur edukatif, deployment frontend-backend terpisah, serta pengamanan API dasar.

## Tujuan Pengembangan

Tujuan utama pengembangan project ini adalah:

1. Membuat media pembelajaran pengolahan citra yang interaktif dan mudah dipahami.
2. Mengimplementasikan operasi citra digital menggunakan OpenCV pada backend Flask.
3. Menyediakan antarmuka modern agar pengguna dapat mencoba operasi citra tanpa menulis kode.
4. Menambahkan visualisasi histogram agar perubahan nilai piksel dapat dianalisis.
5. Menyediakan fitur lanjutan seperti scan dokumen dan advanced editor.
6. Menyiapkan project agar dapat dipublikasikan secara online dengan domain produksi.
7. Menambahkan sistem login dan pengamanan API sebelum website digunakan publik.

---

## Log Pengembangan

### Kronologi Kolaborasi dan Proses Kerja

Bagian ini mencatat proses kerja yang terjadi selama pengembangan project, termasuk diskusi masalah, keputusan teknis, percobaan yang gagal, revisi fitur, dan hasil akhirnya. Logbook ini tidak hanya dibuat berdasarkan commit, tetapi juga berdasarkan proses diskusi dan debugging selama project dikembangkan.

#### 1. Masalah Awal Histogram, Multiplication, dan Division

Pada awal pengembangan, salah satu masalah utama adalah histogram tidak muncul pada beberapa operasi. Selain itu, operasi multiplication dan division belum berjalan normal pada semua kondisi gambar.

Masalah yang dibahas:

1. Histogram tidak tampil setelah gambar diproses.
2. Beberapa operasi tidak mengembalikan data histogram dengan format yang konsisten.
3. Operasi perkalian dan pembagian perlu menjaga nilai piksel tetap berada pada rentang 0-255.
4. Division perlu menghindari pembagian dengan nol.

Solusi yang dilakukan:

1. Backend diperiksa agar setiap operasi mengembalikan response yang konsisten.
2. Histogram dibuat agar tetap dihitung setelah operasi selesai.
3. Operasi multiplication dan division diperbaiki dengan clipping nilai piksel.
4. Frontend diperbaiki agar dapat membaca response histogram dari backend.

Hasil akhirnya, histogram dapat digunakan untuk mendukung analisis sebelum dan sesudah proses citra, sedangkan multiplication dan division dapat berjalan lebih normal.

#### 2. Diskusi Publikasi Website Gratis

Setelah fitur dasar berjalan, tahap berikutnya adalah mencari cara publikasi website secara gratis tanpa kartu bank. Beberapa opsi dipertimbangkan:

1. Vercel untuk frontend.
2. PythonAnywhere untuk backend Flask.
3. Render.
4. Hugging Face Spaces.

Pada tahap ini, dipahami bahwa frontend React/Vite sangat cocok untuk Vercel, tetapi backend Flask/OpenCV lebih sulit jika memakai platform gratis karena dependency OpenCV cukup besar dan membutuhkan runtime Python yang stabil.

Kesimpulan dari tahap ini:

1. Frontend sebaiknya tetap di Vercel.
2. Backend perlu platform yang mampu menjalankan Flask dan OpenCV.
3. Platform gratis memiliki batasan yang cukup besar untuk project image processing.

#### 3. Tutorial PythonAnywhere dan Masalah WSGI

Backend sempat dicoba dijalankan di PythonAnywhere. Pada proses ini, file WSGI menjadi salah satu hal yang membingungkan karena PythonAnywhere membutuhkan entry point khusus untuk menjalankan aplikasi Flask.

Masalah pertama:

```text
ModuleNotFoundError: No module named 'app'
```

Masalah ini terjadi karena file WSGI belum diarahkan ke folder backend yang benar. Path backend harus ditambahkan ke `sys.path`, lalu aplikasi Flask di-import dari `app.py`.

Setelah path diperbaiki, muncul masalah kedua:

```text
ModuleNotFoundError: No module named 'flask_cors'
```

Artinya dependency belum tersedia pada virtual environment PythonAnywhere. Dependency kemudian dicoba di-install melalui `requirements.txt`, tetapi gagal karena:

```text
Disk quota exceeded
```

Hasil pembelajaran dari tahap ini:

1. PythonAnywhere bisa menjalankan Flask, tetapi tidak ideal untuk backend OpenCV yang berat.
2. WSGI perlu konfigurasi path yang benar.
3. Dependency besar seperti OpenCV dapat membuat hosting gratis cepat terkena batas storage.
4. Backend image processing lebih cocok dijalankan di VPS.

#### 4. Percobaan Hugging Face dan Kebingungan Space

Hugging Face Spaces sempat dipertimbangkan sebagai alternatif backend gratis. Namun ketika URL space dibuka, muncul halaman 404 atau Not Found.

Masalah yang terjadi:

1. Space belum benar-benar dibuat atau belum aktif.
2. URL yang dibuka tidak menemukan aplikasi.
3. Alur deployment Hugging Face kurang cocok dengan struktur frontend Vercel + backend Flask yang sedang dibangun.

Kesimpulan:

1. Hugging Face lebih cocok untuk demo ML/AI atau Gradio/Streamlit.
2. Project ini lebih cocok menggunakan backend API Flask yang berjalan stabil di VPS.

#### 5. Pembahasan Hostinger VPS

Setelah beberapa opsi gratis kurang cocok, dipertimbangkan untuk memakai Hostinger VPS. Spesifikasi yang dipilih cukup kuat untuk backend image processing:

```text
2 vCPU Core
8 GB RAM
100 GB NVMe
8 TB Bandwidth
Dedicated IP
Full Root Access
Backup Mingguan
```

Pertimbangan:

1. Backend OpenCV membutuhkan CPU dan RAM yang lebih stabil.
2. VPS memberi full root access.
3. Nginx, Gunicorn, Certbot, dan systemd bisa dikontrol sendiri.
4. Cocok untuk production awal.

Kesimpulan:

VPS adalah pilihan yang lebih realistis untuk backend karena project ini bukan sekadar static website, melainkan aplikasi yang memproses gambar.

#### 6. Perubahan Arsitektur Project

Arsitektur final yang disepakati:

```text
Frontend: Vercel
Backend: Hostinger VPS
Auth: Firebase Google Sign-In
DB: Supabase PostgreSQL
Storage: Cloudinary
Domain: imagemeta.site
API: api.imagemeta.site
```

Alasan pemisahan:

1. Vercel optimal untuk frontend React/Vite.
2. VPS optimal untuk backend Flask/OpenCV.
3. Firebase mempermudah login Google.
4. Supabase cocok untuk data user, history, dan saved project.
5. Cloudinary cocok untuk menyimpan hasil upload dan processed image.

Pada tahap ini juga disepakati bahwa:

1. Frontend tidak ditempatkan di VPS untuk versi pertama.
2. Backend tidak ditempatkan di Vercel.
3. Secret backend tidak boleh masuk frontend.
4. Supabase service role hanya boleh ada di backend.

#### 7. Integrasi Firebase Authentication

User ingin website mewajibkan login sebelum fitur bisa digunakan. Karena itu ditambahkan Firebase Google Sign-In pada frontend.

Bagian yang dikerjakan:

1. Membuat konfigurasi Firebase di frontend.
2. Membuat `AuthContext` untuk menyimpan state login.
3. Membuat halaman login Google.
4. Menambahkan provider auth di `main.tsx`.
5. Membuat Axios client yang otomatis menyertakan Firebase ID token.
6. Backend memverifikasi token Firebase sebelum memproses gambar.

Kendala:

Backend sempat menampilkan pesan:

```text
Firebase auth belum dikonfigurasi di backend.
```

Penyebabnya adalah service account Firebase belum dimasukkan dengan benar ke environment backend.

Solusi:

Service account Firebase dibuat, diubah menjadi base64, lalu dimasukkan sebagai:

```text
FIREBASE_SERVICE_ACCOUNT_BASE64
```

Hasil:

Frontend dapat login menggunakan Google dan backend dapat memverifikasi token user.

#### 8. Integrasi Supabase dan Cloudinary

Supabase dipilih sebagai database PostgreSQL untuk menyimpan data seperti user, image, processing history, dan saved project. Cloudinary digunakan sebagai penyimpanan image agar file original dan hasil processing tidak perlu disimpan langsung di server VPS.

Pembahasan penting:

1. Supabase service role tidak boleh diekspos ke frontend.
2. Cloudinary API secret hanya boleh berada di backend.
3. Frontend hanya menerima URL hasil upload/proses.
4. Database cukup menyimpan metadata seperti URL, public ID, user ID, operation type, dan timestamp.

Kendala:

Pada tahap awal, penggunaan Supabase dan Cloudinary membuat proses terasa lebih lambat dibanding mode lokal. Hal ini terjadi karena sebelumnya proses hanya terjadi di memori lokal, sedangkan setelah integrasi cloud terdapat proses tambahan seperti upload, request jaringan, dan penyimpanan history.

Evaluasi:

Tidak semua proses harus langsung disimpan ke Cloudinary/Supabase. Untuk meningkatkan performa, proses utama harus tetap cepat dan penyimpanan history/upload dapat dibuat opsional atau dilakukan setelah hasil utama siap.

#### 9. Pembahasan Optimasi Performa

User merasa proses gambar menjadi lebih lambat setelah integrasi cloud. Awalnya sempat dianggap karena ukuran file atau request save, tetapi kemudian disadari bahwa masalah harus dilihat lebih luas.

Analisis:

1. Local processing cepat karena tidak ada upload eksternal.
2. Cloudinary menambah waktu upload/download.
3. Supabase menambah waktu insert metadata.
4. Auth token verification juga menambah sedikit overhead.
5. Gambar besar membutuhkan waktu komputasi lebih lama.

Solusi optimasi yang dibahas:

1. Proses gambar dilakukan di backend terlebih dahulu.
2. Upload Cloudinary tidak perlu selalu menjadi blocking utama.
3. Simpan history hanya jika diperlukan.
4. Batasi ukuran gambar dan jumlah piksel.
5. Resize gambar internal untuk operasi berat.
6. Tambahkan feedback loading agar user tahu proses berjalan.

Hasil:

Backend diperkuat dengan limit ukuran request dan pixel. Scan Document juga dibuat dengan pipeline yang memperhatikan ukuran kerja agar proses tidak terlalu berat.

#### 10. Perubahan Histogram agar Lebih Edukatif

Histogram awal dianggap membingungkan dan sulit dijelaskan. User ingin histogram RGB dan luminance divisualisasikan dalam satu area agar lebih mudah dibandingkan, seperti style tools image online.

Masalah:

1. Histogram terpisah membuat perbandingan kurang jelas.
2. Histogram luminance saja tidak cukup untuk gambar berwarna.
3. Nilai peak dianggap tidak terlalu berguna untuk user awam.
4. Tampilan histogram sempat terlalu kecil dan sempit.

Solusi:

1. Histogram RGB dan luminance dibuat berada dalam visualisasi yang lebih mudah dibandingkan.
2. Peak yang tidak terlalu membantu dihapus.
3. Ukuran histogram diperbesar agar lebih nyaman dibaca.
4. Penekanan diarahkan pada distribusi intensitas, bukan angka teknis yang membingungkan.

Hasil:

Histogram menjadi lebih edukatif karena pengguna dapat melihat perubahan distribusi channel warna dan luminance dalam satu konteks.

#### 11. Penambahan Materi Pengolahan Citra Lanjutan

User memberikan materi tentang thinning, Zhang-Suen, edge detection, dan segmentasi. Materi ini kemudian dijadikan dasar untuk menambahkan fitur edukatif baru.

Materi yang ditambahkan:

1. Thinning.
2. Zhang-Suen Algorithm.
3. Edge Detection.
4. Segmentasi Citra.
5. Thresholding.
6. Adaptive Thresholding.
7. Otsu Binarization.
8. K-Means Segmentation.
9. Morfologi Citra.

Pertimbangan kategori:

Sempat dibahas apakah operasi seperti thinning dan segmentasi masuk ke operasi spasial atau harus dibuat halaman sendiri. Karena website bertujuan edukatif, fitur tersebut lebih baik dibuat sebagai topik terpisah agar konsepnya lebih jelas dan tidak bercampur dengan operasi spasial dasar.

Hasil:

Website menjadi lebih sesuai dengan materi pengolahan citra dan pola, bukan hanya editor gambar.

#### 12. Evaluasi Teknik Segmentasi

Segmentasi awal memiliki terlalu banyak pilihan dengan nama yang mirip dan penjelasan yang kurang membedakan fungsi masing-masing. User merasa halaman segmentasi terlalu ramai.

Masalah:

1. Terlalu banyak teknik membuat pengguna bingung.
2. Penjelasan perbedaan antar metode belum cukup jelas.
3. Beberapa metode tidak perlu ditampilkan jika tidak penting untuk tujuan edukasi.

Solusi yang diarahkan:

1. Menampilkan teknik yang paling penting saja.
2. Menjelaskan kapan menggunakan global thresholding, adaptive thresholding, Otsu, dan K-Means.
3. Mengurangi fitur yang tidak memberi nilai edukasi jelas.

Hasil:

Arah pengembangan segmentasi menjadi lebih fokus pada kualitas pembelajaran, bukan jumlah fitur.

#### 13. Pengembangan Scan Document

Fitur Scan Document dikembangkan karena user ingin fitur seperti CamScanner, yaitu gambar dokumen yang miring dapat diluruskan, teks diperjelas, bayangan dikurangi, dan hasil terlihat seperti scan.

Fitur yang dibuat:

1. Upload gambar dokumen.
2. Auto crop dan deskew.
3. Perspective correction.
4. Output mode B/W Sharp.
5. Output mode Clean Text.
6. Output mode Grayscale.
7. Output mode Color.
8. Histogram sebelum dan sesudah.
9. Download hasil.

Kendala:

1. Auto crop dan deskew kadang menghasilkan perspektif aneh.
2. Deteksi kontur dokumen tidak selalu akurat jika background ramai.
3. Hasil B/W bisa terlalu keras pada dokumen bernoda.
4. Frontend sempat blank jika backend response tidak sesuai field yang diharapkan.

Solusi:

1. Menambahkan fallback jika dokumen tidak terdeteksi sempurna.
2. Membuat beberapa mode output agar user bisa memilih hasil terbaik.
3. Menambahkan guard response di frontend.
4. Membuat pipeline scan yang lebih fokus pada dokumen, bukan segmentasi objek umum.

Hasil:

Walaupun auto crop belum selalu sempurna, fitur Scan Document sudah memuaskan untuk fungsi dasar scan dokumen dan cocok untuk penggunaan edukatif.

#### 14. Evaluasi Remove Background dan Cutout

Remove background dan cutout sempat dibuat menggunakan OpenCV klasik seperti GrabCut dan pipeline segmentasi. Namun hasilnya tidak sesuai ekspektasi.

Masalah yang terlihat:

1. Objek tidak selalu terpotong rapi.
2. Background masih tersisa di sekitar objek.
3. Tepi objek terlihat kasar atau gelap.
4. Pada gambar objek kompleks, GrabCut tidak memahami objek seperti AI segmentation.

Kesimpulan:

Fitur remove.bg yang bagus membutuhkan AI segmentation. OpenCV klasik bisa membantu, tetapi tidak cukup untuk hasil yang terlihat profesional pada semua gambar.

Keputusan:

1. Remove background dihapus.
2. Cutout dihapus dari Advanced Editor.
3. Route backend `/api/editor/cutout` dihapus.
4. Pipeline segmentasi lama dihapus dari backend.

Hasil:

Project menjadi lebih bersih dan tidak menjanjikan fitur yang kualitasnya belum siap.

#### 15. Pembersihan Karakter Anomali di Kode

Pada beberapa file ditemukan karakter aneh seperti:

```text
â”€â”€ RIGHT: Result area
```

Karakter ini berasal dari masalah encoding atau mojibake. User menegaskan bahwa yang harus dibersihkan adalah kode, bukan hanya tampilan frontend.

Masalah:

1. Kode menjadi sulit dibaca.
2. Komentar terlihat tidak profesional.
3. Editor seperti VS Code menampilkan karakter aneh.

Solusi:

Komentar yang mengandung karakter aneh dibersihkan menjadi teks sederhana, misalnya:

```text
RIGHT: Result area
```

Hasil:

Kode menjadi lebih rapi dan mudah dibaca.

#### 16. README dan Dokumentasi Public-Facing

README sempat dibuat terlalu teknis dengan detail deployment, environment, struktur produksi, VPS, dan internal setup. User menilai hal tersebut tidak cocok untuk project yang ingin terlihat seperti produk atau bisnis.

Masalah:

1. README terlalu menampilkan detail internal.
2. Struktur deployment dan env terlalu terbuka untuk public-facing documentation.
3. Terlihat kurang profesional jika semua infrastruktur dijelaskan secara mentah.

Solusi:

README diubah menjadi lebih public-facing:

1. Fokus pada nilai produk.
2. Menjelaskan fitur utama.
3. Tidak menampilkan detail secret atau infrastruktur internal berlebihan.
4. Menggunakan gaya yang lebih hidup dan profesional.

Hasil:

README menjadi lebih cocok untuk repository publik dan branding website.

#### 17. Pengamanan Website

Setelah website mulai online, user bertanya apakah website aman dari SQL injection, exposure, dan risiko lain. Pengamanan yang dibahas dan sebagian diterapkan:

1. Firebase authentication.
2. Backend token verification.
3. CORS origin restriction.
4. Rate limiting basic.
5. Max request size.
6. Max image pixels.
7. Security headers.
8. Nginx dotfile blocking.
9. Pengecekan `.git/config` dan `.env` exposure.

Pengecekan exposure dilakukan dengan:

```bash
curl -i https://imagemeta.site/.git/config
curl -i https://api.imagemeta.site/.git/config
curl -i https://api.imagemeta.site/.env
```

Hasilnya semua mengembalikan 404, sehingga `.git` dan `.env` tidak terekspos publik.

Hasil:

Website sudah memiliki pengamanan dasar yang cukup untuk tahap awal production, walaupun masih perlu peningkatan seperti role authorization, logging, monitoring, dan backup.

#### 18. Diskusi Production Readiness

User bertanya apakah website sudah memiliki:

1. Authentication.
2. Authorization.
3. Cloud compute.
4. CI/CD.
5. Version control.
6. Role level security.
7. Rate limiting.
8. Cache dan CDN.
9. Load balancer dan scaling.
10. Error tracking dan log.
11. Availability dan recovery.

Evaluasi:

1. Authentication sudah ada melalui Firebase.
2. Authorization masih basic.
3. Cloud compute sudah ada melalui Vercel dan VPS.
4. CI/CD frontend sudah ada via Vercel, backend masih manual.
5. Version control sudah menggunakan GitHub.
6. Role level security belum matang.
7. Rate limiting sudah basic.
8. CDN sudah ada melalui Vercel dan Cloudinary.
9. Load balancer belum dibutuhkan untuk tahap awal.
10. Logging masih basic melalui server logs.
11. Recovery masih perlu backup dan monitoring lebih baik.

Kesimpulan:

Untuk public beta, project sudah cukup kuat. Untuk production bisnis, perlu admin dashboard, role/plan, backend CI/CD, error tracking, backup, dan monitoring.

#### 19. Diskusi Monetisasi: Ads dan Premium

User ingin menjadikan website sebagai peluang production dan monetisasi. Beberapa ide dibahas:

1. Menambahkan iklan setelah proses image.
2. Membuat fitur premium.
3. Membuat admin yang dapat mengatur fitur maintenance.
4. Membuat fitur tertentu hanya bisa digunakan user premium.
5. Membuat limit penggunaan untuk free user.

Rencana model:

Free user:

```text
limit proses harian
ads aktif
akses fitur dasar
```

Premium user:

```text
no ads
limit lebih besar
fitur advanced
export kualitas tinggi
history/project saving
```

Admin:

```text
mengatur fitur active/maintenance
mengatur free/premium access
melihat user dan usage
melihat error log
```

Kesimpulan:

Monetisasi bisa dilakukan, tetapi pondasi yang lebih penting adalah admin control, role/plan, usage limit, dan backend CI/CD.

#### 20. Rencana Admin Dashboard

Admin Dashboard direncanakan sebagai fitur penting agar website bisa dikelola seperti produk production.

Fitur admin yang direncanakan:

1. Melihat daftar user.
2. Melihat usage per user.
3. Mengatur operation active atau maintenance.
4. Mengatur fitur free atau premium.
5. Melihat error log.
6. Melihat processing history.
7. Mengatur limit penggunaan.

Contoh status fitur:

```text
grayscale       active       free
scan-document   active       free
advanced-editor active       premium
segmentation    maintenance  admin_only
```

Jika fitur maintenance, frontend menampilkan pesan:

```text
Fitur sedang maintenance. Kami sedang memperbaiki hasil proses.
```

#### 21. Backend CI/CD

Saat ini frontend sudah memiliki CI/CD otomatis melalui Vercel. Setiap commit yang di-push ke GitHub akan otomatis memicu build dan deploy frontend.

Namun backend masih manual:

```bash
ssh root@76.13.196.40
cd /var/www/image-metamorphosis
git pull
sudo systemctl restart imagemeta-api
```

Rencana berikutnya adalah membuat GitHub Actions agar backend otomatis deploy ke VPS setelah push ke branch main.

Alur yang diinginkan:

```text
push GitHub main
GitHub Actions SSH ke VPS
git pull
install/update dependency jika perlu
restart systemd service
health check API
```

Manfaat:

1. Tidak perlu update manual lewat terminal.
2. Deploy lebih konsisten.
3. Mengurangi risiko lupa restart backend.
4. Lebih profesional untuk production.

#### 22. Keputusan Akhir Tahap Ini

Setelah banyak iterasi, project berada pada kondisi:

1. Fitur utama pengolahan citra berjalan.
2. Scan Document berjalan sebagai fitur mandiri.
3. Advanced Editor difokuskan pada editing umum.
4. Remove background/cutout dihapus karena belum memenuhi standar kualitas.
5. Frontend sudah online di domain utama.
6. Backend sudah online di subdomain API.
7. Login Google sudah berjalan.
8. Security dasar sudah diterapkan.
9. Repository sudah lebih rapi.
10. Arah produk ke depan sudah lebih jelas: admin, premium, ads, CI/CD, monitoring.

Proses ini menunjukkan bahwa pengembangan project tidak hanya menambah fitur, tetapi juga mengevaluasi fitur yang tidak layak, memperbaiki deployment, memperkuat keamanan, dan mengarahkan website menjadi produk yang lebih siap digunakan publik.

### 29 April 2026 - Inisialisasi Project

Pada tahap awal, project Image Metamorphosis dibuat dengan struktur frontend dan backend. Backend menggunakan Flask sebagai API server dan OpenCV untuk menjalankan proses pengolahan citra. Frontend menggunakan React, TypeScript, Vite, dan Tailwind CSS untuk membangun tampilan aplikasi.

Fitur awal yang dibuat meliputi halaman utama, upload gambar, layout aplikasi, sidebar navigasi, komponen kontrol parameter, tampilan before-after, serta beberapa halaman operasi citra dasar seperti operasi titik, operasi aritmatika, operasi spasial, geometri, dasar citra, dan studi kasus.

Kendala pada tahap ini adalah struktur project masih dalam bentuk awal dan beberapa dependency lokal seperti virtual environment sempat ikut masuk ke repository. Hal ini kemudian diperbaiki pada tahap berikutnya dengan menambahkan `.gitignore` yang lebih tepat.

Hasil dari tahap ini adalah fondasi aplikasi berhasil dibuat dan aplikasi sudah dapat menjalankan proses pengolahan citra dari frontend ke backend.

### 29 April 2026 - Dokumentasi Awal dan Navigasi

Setelah project dasar dibuat, dokumentasi README mulai ditambahkan. README berisi penjelasan fitur, tech stack, dan cara menjalankan project. Dokumentasi ini penting agar project dapat dipahami oleh orang lain yang melihat repository.

Pada hari yang sama, navigasi header juga sempat diubah. Menu navigasi pernah disembunyikan karena perlu perbaikan, kemudian dikembalikan lagi agar pengguna dapat berpindah antarhalaman dengan lebih mudah.

Kendala pada tahap ini adalah menentukan struktur navigasi yang tidak terlalu ramai tetapi tetap memudahkan pengguna. Hasil akhirnya, navigasi aplikasi dikembalikan agar pengalaman pengguna menjadi lebih jelas.

### 8 Mei 2026 - Histogram dan Operasi Aritmatika

Pada tahap ini, fitur operasi perkalian dan pembagian citra ditambahkan. Backend diperbarui agar dapat menjalankan operasi multiplication dan division, sedangkan frontend diperbarui agar operasi tersebut tersedia di halaman Operasi Aritmatika.

Histogram juga mulai ditambahkan untuk mendukung analisis hasil operasi. Dengan adanya histogram, pengguna tidak hanya melihat perubahan visual pada gambar, tetapi juga dapat memahami distribusi intensitas piksel sebelum dan sesudah operasi.

Kendala yang muncul adalah memastikan histogram tetap muncul untuk semua operasi dan tidak hanya untuk operasi tertentu. Operasi perkalian dan pembagian juga perlu ditangani dengan hati-hati agar nilai piksel tidak keluar dari rentang valid 0-255. Solusinya adalah melakukan clipping dan normalisasi output pada backend.

Hasil akhirnya, operasi aritmatika menjadi lebih lengkap dan visualisasi histogram mulai menjadi bagian penting dari aplikasi.

### 8-9 Mei 2026 - Persiapan Backend untuk Deployment

Backend mulai disesuaikan agar lebih siap untuk deployment. File `requirements.txt` diperbarui dengan dependency seperti `gunicorn` dan `opencv-python-headless`. Penggunaan `opencv-python-headless` lebih cocok untuk server karena tidak membutuhkan library GUI.

API base URL di frontend juga diperbaiki agar bisa diarahkan ke backend yang berjalan di environment berbeda. Selain itu, tipe Vite environment ditambahkan agar konfigurasi environment variable lebih aman di TypeScript.

Kendala pada tahap ini muncul saat mencoba menjalankan backend di platform gratis. Beberapa platform memiliki keterbatasan disk quota, dependency OpenCV yang besar, atau konfigurasi WSGI yang cukup membingungkan. Dari proses tersebut, diputuskan bahwa backend lebih cocok dijalankan di VPS karena membutuhkan OpenCV dan proses komputasi gambar yang lebih berat.

Hasil akhirnya, backend menjadi lebih siap untuk dijalankan sebagai service produksi.

### 11 Juni 2026 - Pembersihan Repository

Pada tahap ini, `.gitignore` diterapkan dengan lebih baik. File virtual environment dan dependency lokal yang sebelumnya ikut masuk repository mulai dibersihkan. Hal ini membuat repository lebih ringan dan lebih profesional.

Kendala utama adalah ukuran repository sempat membesar karena folder `backend/venv` berisi banyak package Python ikut ter-commit. Solusinya adalah menghapus file dependency lokal dari tracking Git dan memastikan `.gitignore` mencegah hal serupa terjadi lagi.

Hasil akhirnya, repository menjadi lebih rapi dan lebih aman untuk dipublikasikan.

### 11 Juni 2026 - Penambahan Operasi Citra Baru

Beberapa operasi baru ditambahkan ke aplikasi, yaitu Gaussian Blur, Saturation, Hue Shift, Opacity, dan Sharpness. Operasi ini ditambahkan ke backend dan frontend agar pengguna dapat mempelajari efek perubahan warna, ketajaman, transparansi, dan blur pada gambar.

Gaussian Blur dibuat dengan parameter kernel size dan sigma. Saturation dan Hue Shift menggunakan ruang warna HSV agar perubahan warna lebih sesuai secara konsep pengolahan citra. Sharpness dibuat dengan teknik Unsharp Masking, yaitu menambahkan kembali detail dari selisih gambar asli dan gambar blur.

Kendala pada tahap ini adalah membuat penjelasan parameter yang mudah dipahami. Beberapa istilah seperti sigma pada Gaussian Blur perlu dijelaskan dengan bahasa edukatif agar pengguna tidak hanya memakai slider, tetapi juga memahami efek matematisnya.

Hasil akhirnya, fitur operasi titik dan spasial menjadi lebih kaya dan sesuai dengan kebutuhan pembelajaran.

### 11 Juni 2026 - Advanced Editor dan Penghapusan Studi Kasus

Advanced Editor mulai dibuat sebagai fitur editor gambar yang lebih fleksibel. Halaman Studi Kasus dihapus karena fungsinya mulai digantikan oleh Advanced Editor yang lebih luas.

Advanced Editor menyediakan fitur adjustment seperti brightness, contrast, saturation, hue, blur, sharpness, opacity, rotate, flip, crop, dan export gambar. Tujuannya adalah menyediakan ruang kerja yang lebih bebas untuk mengedit gambar secara langsung.

Kendala pada tahap ini adalah menentukan batas fitur editor. Beberapa fitur seperti remove background dan cutout sempat dicoba, tetapi hasilnya belum memenuhi ekspektasi karena menggunakan pendekatan OpenCV klasik, bukan AI segmentation seperti remove.bg. Oleh karena itu, fitur tersebut kemudian dievaluasi ulang dan akhirnya dihapus.

Hasil akhirnya, Advanced Editor menjadi fitur pendukung untuk editing umum, bukan fitur segmentasi otomatis.

### 24 Juni 2026 - Big Update: Authentication, Scan Document, dan Materi Lanjutan

Pada tahap ini dilakukan pembaruan besar pada project. Firebase Authentication ditambahkan agar pengguna harus login menggunakan Google sebelum mengakses fitur utama. Frontend menambahkan `AuthContext`, halaman login, Firebase initialization, dan Axios client yang otomatis mengirim Firebase ID token ke backend.

Backend diperbarui agar dapat menerima dan memverifikasi token Firebase. Dengan ini, API tidak lagi hanya terbuka bebas, tetapi dapat dilindungi oleh autentikasi.

Selain itu, halaman baru untuk materi pengolahan citra juga ditambahkan, seperti Morfologi Citra, Segmentasi Citra, dan Deteksi Tepi. Hal ini membuat website lebih sesuai sebagai media edukasi, bukan hanya alat editing gambar.

Fitur Scan Document juga mulai dibuat. Fitur ini bertujuan untuk melakukan koreksi perspektif, pembersihan noise, peningkatan kontras, dan menghasilkan beberapa mode output seperti hitam-putih, clean text, grayscale, dan color.

Kendala pada tahap ini cukup banyak. Pertama, integrasi authentication perlu sinkron antara frontend dan backend. Kedua, scan document perlu menghasilkan output yang terlihat seperti hasil scanner, tetapi tetap menggunakan OpenCV. Ketiga, fitur cutout/remove background sempat dibuat tetapi hasilnya belum stabil karena OpenCV klasik tidak sekuat AI segmentation.

Hasil akhirnya, website mulai berubah menjadi aplikasi yang lebih production-ready dengan login, halaman edukasi tambahan, API token, dan fitur scan dokumen.

### 24 Juni 2026 - Pipeline Modal dan Penjelasan Proses

Pipeline Modal dibuat untuk menampilkan tahapan proses pengolahan citra. Tujuannya adalah agar pengguna bisa melihat proses yang terjadi di balik sebuah output, bukan hanya hasil akhirnya.

Komponen ini digunakan untuk menjelaskan tahapan seperti preprocessing, enhancement, filtering, thresholding, dan output generation. Dari sisi edukasi, fitur ini berguna karena pengguna dapat memahami alur kerja OpenCV secara bertahap.

Kendala yang muncul adalah beberapa teks dan karakter dalam kode sempat mengalami masalah encoding atau mojibake, misalnya karakter aneh hasil salah encoding. Bagian tersebut kemudian dibersihkan agar kode lebih rapi dan mudah dibaca.

Hasil akhirnya, Pipeline Modal menjadi komponen pendukung edukasi untuk fitur yang membutuhkan penjelasan proses.

### 24 Juni 2026 - Pembaruan README

README diperbarui agar lebih profesional dan lebih sesuai untuk project yang akan dipublikasikan. Dokumentasi dibuat lebih fokus pada nilai produk, fitur utama, dan gambaran umum aplikasi.

Kendala pada tahap ini adalah menentukan informasi mana yang perlu ditampilkan secara publik. Beberapa detail deployment seperti VPS, environment variable rahasia, dan struktur produksi tidak perlu ditampilkan secara terlalu terbuka karena README publik sebaiknya tidak memperlihatkan sisi internal bisnis atau infrastruktur secara berlebihan.

Hasil akhirnya, README menjadi lebih rapi, lebih representatif, dan lebih aman untuk repository publik.

### 25 Juni 2026 - Security Hardening

Backend diperkuat dengan beberapa pengamanan dasar. CORS dibuat berbasis environment variable, route penting dilindungi dengan Firebase authentication, ukuran request dibatasi, jumlah pixel gambar dibatasi, dan rate limiting dasar ditambahkan.

Security headers juga ditambahkan, seperti `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, dan `Strict-Transport-Security`. Tujuannya adalah mengurangi risiko umum seperti clickjacking, sniffing content type, dan akses browser API yang tidak dibutuhkan.

Kendala pada tahap ini adalah menjaga agar security tidak merusak fitur yang sudah berjalan. Backend harus tetap bisa menerima request dari frontend domain produksi, tetapi tetap menolak request yang tidak valid atau tanpa token.

Hasil akhirnya, backend menjadi lebih aman untuk digunakan secara publik.

### 25 Juni 2026 - Perbaikan Scan Document

Fitur Scan Document diperbaiki agar lebih stabil ketika menerima response dari backend. Frontend diberi guard agar tidak blank jika response backend tidak memiliki field tertentu seperti `detection_score` atau mode output tertentu.

Kendala yang terjadi adalah halaman dapat menjadi kosong atau error jika response scan document tidak sesuai ekspektasi frontend. Solusinya adalah menambahkan fallback output, misalnya memilih `bw`, `grayscale`, atau `color` jika mode aktif tidak tersedia.

Hasil akhirnya, Scan Document menjadi lebih tahan terhadap variasi response backend dan pengalaman pengguna menjadi lebih stabil.

### 25 Juni 2026 - Evaluasi dan Penghapusan Fitur Scan Docs di Advanced Editor

Scan Document sempat muncul juga di Advanced Editor, tetapi kemudian dinilai tidak tepat karena fitur scan document sudah memiliki halaman khusus. Jika fitur yang sama muncul di dua tempat, pengguna dapat bingung dan error handling menjadi tidak konsisten.

Kendala yang muncul adalah fitur scan document di Advanced Editor dapat gagal karena alur UI dan API-nya tidak sebaik halaman Scan Document khusus. Solusinya adalah menghapus Scan Docs dari Advanced Editor agar setiap fitur berada di tempat yang sesuai.

Hasil akhirnya, Advanced Editor menjadi lebih fokus pada editing gambar umum, sedangkan Scan Document menjadi fitur mandiri.

### 25 Juni 2026 - Penghapusan Legacy Cutout Feature

Fitur cutout/remove background dihapus dari Advanced Editor dan backend. Fitur ini sebelumnya dibuat menggunakan pipeline segmentasi OpenCV klasik, tetapi hasilnya belum memenuhi ekspektasi karena remove background berkualitas tinggi biasanya membutuhkan AI segmentation.

Kendala utama adalah hasil cutout kurang presisi, terutama pada objek kompleks, latar belakang ramai, atau objek dengan tepi halus. GrabCut dan morphology dapat membantu, tetapi tidak selalu mampu menghasilkan hasil seperti remove.bg.

Solusinya adalah menghapus tombol Cutout dari Advanced Editor, menghapus pemanggilan API `/api/editor/cutout`, dan menghapus route backend serta pipeline lama yang berkaitan dengan cutout. Dengan begitu, website tidak menampilkan fitur yang kualitasnya belum sesuai standar.

Hasil akhirnya, project menjadi lebih jujur secara fitur. Fitur yang tersedia adalah fitur yang benar-benar dapat digunakan dengan kualitas yang stabil.

---

## Kendala Umum Selama Pengembangan

### 1. Deployment Backend OpenCV

Backend OpenCV membutuhkan dependency yang cukup besar. Saat mencoba beberapa platform gratis, muncul kendala seperti disk quota, konfigurasi WSGI, dan dependency yang tidak cocok. Solusi akhirnya adalah menggunakan Hostinger VPS agar backend memiliki kontrol penuh terhadap Python environment, Nginx, Gunicorn, dan dependency OpenCV.

### 2. Integrasi Frontend dan Backend

Frontend berjalan di Vercel, sedangkan backend berjalan di VPS dengan domain API berbeda. Hal ini membutuhkan pengaturan CORS, environment variable `VITE_API_URL`, HTTPS, dan token authentication. Solusinya adalah memisahkan frontend dan backend secara jelas serta menggunakan Axios client untuk mengirim token Firebase.

### 3. Authentication dan API Protection

Pada awalnya API dapat dipakai tanpa login. Setelah Firebase Authentication ditambahkan, backend perlu memverifikasi ID token agar fitur hanya bisa digunakan oleh user yang valid. Tantangannya adalah memastikan token dikirim di setiap request dan backend memiliki service account Firebase yang benar.

### 4. Kualitas Fitur Cutout

Fitur cutout/remove background menjadi salah satu evaluasi penting. Pendekatan OpenCV klasik tidak cukup untuk menghasilkan output sekelas AI segmentation. Daripada mempertahankan fitur yang hasilnya tidak memuaskan, fitur tersebut dihapus agar kualitas website tetap konsisten.

### 5. Scan Document

Scan Document membutuhkan beberapa proses sekaligus: deteksi dokumen, koreksi perspektif, penghilangan bayangan, peningkatan teks, dan output dalam beberapa mode. Tantangan utamanya adalah membuat hasil tetap bagus untuk gambar miring, dokumen bernoda, dan pencahayaan tidak merata. Solusinya adalah membuat pipeline khusus scan document dengan beberapa mode output.

### 6. Histogram

Histogram sempat beberapa kali disesuaikan karena tujuan utamanya adalah edukasi. Histogram harus mudah dibandingkan antara sebelum dan sesudah, serta antara RGB dan luminance. Perbaikan dilakukan agar histogram lebih informatif dan tidak membingungkan pengguna.

### 7. Encoding dan Karakter Aneh

Beberapa file sempat memiliki karakter aneh akibat masalah encoding. Hal ini membuat kode kurang rapi saat dilihat di editor. Solusinya adalah membersihkan komentar dan teks yang mengandung mojibake agar kode lebih mudah dibaca.

---

## Proses Deployment dan Publikasi Website

Bagian ini menjelaskan proses nyata yang dilakukan saat project mulai dipersiapkan untuk online. Proses deployment tidak langsung berhasil dalam satu kali percobaan, karena project ini memiliki frontend React dan backend Flask/OpenCV yang membutuhkan environment berbeda.

### 1. Menentukan Tempat Hosting Gratis

Pada awalnya, tujuan deployment adalah mencari tempat hosting gratis tanpa syarat kartu bank. Beberapa opsi dipertimbangkan, seperti Vercel untuk frontend, PythonAnywhere untuk backend, Render, dan Hugging Face Spaces.

Vercel dipilih untuk frontend karena cocok untuk aplikasi React/Vite dan dapat terhubung langsung dengan GitHub. Namun, backend Flask dengan OpenCV tidak cocok ditempatkan di Vercel karena backend membutuhkan proses Python yang berjalan sebagai API server, bukan serverless frontend.

PythonAnywhere sempat dicoba untuk backend karena menyediakan hosting Python gratis. Namun, muncul beberapa kendala, terutama pada konfigurasi WSGI dan dependency backend.

### 2. Percobaan Backend di PythonAnywhere

Saat mencoba menjalankan backend di PythonAnywhere, muncul error:

```text
ModuleNotFoundError: No module named 'app'
```

Error ini terjadi karena file WSGI belum menunjuk ke folder backend yang benar. Solusinya adalah mengatur path Python agar mengarah ke folder:

```text
/home/UrLord/image-metamorphosis/backend
```

Setelah path diperbaiki, error berikutnya muncul:

```text
ModuleNotFoundError: No module named 'flask_cors'
```

Error ini menunjukkan bahwa dependency backend belum ter-install di virtual environment PythonAnywhere. Dependency kemudian dicoba di-install melalui:

```bash
pip install -r /home/UrLord/image-metamorphosis/backend/requirements.txt
```

Namun proses instalasi gagal karena:

```text
ERROR: Could not install packages due to an OSError: [Errno 122] Disk quota exceeded
```

Kendala ini terjadi karena dependency seperti OpenCV cukup besar, sedangkan akun gratis PythonAnywhere memiliki batas storage. Dari sini disimpulkan bahwa PythonAnywhere gratis kurang cocok untuk backend project ini.

### 3. Evaluasi Platform Backend

Setelah PythonAnywhere mengalami kendala disk quota, opsi lain seperti Render dan Hugging Face Spaces ikut dipertimbangkan. Render membutuhkan verifikasi kartu untuk beberapa kebutuhan deployment, sedangkan Hugging Face Spaces sempat membingungkan karena URL space belum aktif atau belum terbuat dengan benar.

Dari evaluasi tersebut, backend akhirnya diputuskan lebih baik dijalankan di VPS. Alasannya:

1. Backend membutuhkan OpenCV dan dependency yang cukup berat.
2. Proses image processing lebih stabil jika berjalan di server sendiri.
3. VPS memberi akses penuh untuk mengatur Python, virtual environment, Gunicorn, Nginx, dan SSL.
4. Project ini ditargetkan untuk production sehingga kontrol server lebih penting.

### 4. Keputusan Arsitektur Production

Arsitektur production yang dipilih adalah:

```text
Frontend: Vercel
Backend: Hostinger VPS
Domain utama: https://imagemeta.site
API domain: https://api.imagemeta.site
Authentication: Firebase Google Sign-In
Database: Supabase PostgreSQL
Storage: Cloudinary
```

Frontend tidak ditempatkan di VPS karena Vercel lebih mudah untuk build React/Vite dan sudah memiliki CDN. Backend tidak ditempatkan di Vercel karena Flask/OpenCV lebih cocok berjalan sebagai service di VPS.

Keputusan ini membuat project lebih terstruktur:

1. Vercel menangani frontend dan delivery static asset.
2. VPS menangani API dan image processing.
3. Firebase menangani login Google.
4. Supabase menyimpan data user/history.
5. Cloudinary menyimpan gambar original/processed.

### 5. Setup Frontend di Vercel

Frontend di-deploy ke Vercel dengan cara import repository GitHub:

```text
Repository: UrLords/image-metamorphosis
Root Directory: frontend
Build Command: npm run build
Output Directory: dist
```

Environment variable frontend yang diperlukan di Vercel adalah:

```text
VITE_API_URL=https://api.imagemeta.site/api
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_APP_ID=...
```

Hanya environment variable dengan prefix `VITE_` yang boleh masuk frontend. Secret backend seperti Supabase service role, Cloudinary API secret, dan Firebase service account tidak boleh dimasukkan ke Vercel frontend.

Setelah project berhasil di-import, Vercel menghasilkan domain sementara:

```text
image-metamorphosis.vercel.app
```

Kemudian domain custom ditambahkan:

```text
imagemeta.site
www.imagemeta.site
```

Vercel memberikan DNS record yang perlu dipasang di DNS provider:

```text
A record untuk @
CNAME record untuk www
```

Setelah DNS propagasi selesai, domain frontend dapat diakses melalui:

```text
https://imagemeta.site
```

### 6. Setup Domain dan DNS

Domain dibeli melalui Hostinger. Setelah domain aktif, DNS diarahkan untuk dua kebutuhan:

1. Domain utama `imagemeta.site` mengarah ke Vercel.
2. Subdomain `api.imagemeta.site` mengarah ke VPS.

Subdomain API diarahkan ke IP VPS:

```text
api.imagemeta.site -> 76.13.196.40
```

Dengan pemisahan ini, frontend dan backend dapat berjalan di tempat berbeda tetapi tetap terlihat sebagai satu produk.

### 7. Setup Backend di Hostinger VPS

VPS menggunakan Ubuntu 24.04. Akses dilakukan melalui SSH:

```bash
ssh root@76.13.196.40
```

Saat pertama kali SSH, muncul pertanyaan fingerprint:

```text
Are you sure you want to continue connecting?
```

Jawabannya adalah `yes` jika IP benar-benar milik VPS sendiri. Setelah berhasil masuk, repository project ditempatkan di folder:

```text
/var/www/image-metamorphosis
```

Backend dijalankan dari folder:

```text
/var/www/image-metamorphosis/backend
```

Di VPS perlu disiapkan:

1. Python dan pip.
2. Virtual environment.
3. Dependency dari `requirements.txt`.
4. Gunicorn sebagai production WSGI server.
5. Systemd service agar backend tetap berjalan.
6. Nginx sebagai reverse proxy.
7. Certbot untuk HTTPS.

### 8. Environment Backend

Backend membutuhkan file `.env` di server. Environment backend berisi konfigurasi production seperti:

```text
FRONTEND_URL=https://imagemeta.site
CORS_ORIGINS=https://imagemeta.site
REQUIRE_AUTH=true
MAX_CONTENT_LENGTH=16777216
MAX_IMAGE_PIXELS=12000000
RATE_LIMIT_WINDOW=60
RATE_LIMIT_MAX=40

FIREBASE_PROJECT_ID=...
FIREBASE_SERVICE_ACCOUNT_BASE64=...

SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...

CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

Sempat terjadi error:

```text
Firebase auth belum dikonfigurasi di backend.
```

Error ini terjadi karena backend belum memiliki konfigurasi Firebase Admin service account yang benar. Solusinya adalah membuat service account Firebase, mengubahnya ke base64, lalu memasukkannya ke:

```text
FIREBASE_SERVICE_ACCOUNT_BASE64
```

Setelah environment backend diperbaiki dan service backend direstart, autentikasi Firebase berhasil berjalan.

### 9. Setup Nginx Reverse Proxy

Nginx digunakan agar request dari:

```text
https://api.imagemeta.site
```

diteruskan ke backend Flask/Gunicorn di:

```text
http://127.0.0.1:8000
```

Konfigurasi Nginx berada di:

```text
/etc/nginx/sites-available/api.imagemeta.site
```

Bagian utama konfigurasi:

```nginx
server {
    server_name api.imagemeta.site;

    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Setelah konfigurasi dibuat, Nginx dites dengan:

```bash
sudo nginx -t
```

Jika konfigurasi valid, Nginx direload:

```bash
sudo systemctl reload nginx
```

### 10. Setup HTTPS dengan Certbot

HTTPS untuk API dibuat menggunakan Certbot:

```bash
sudo certbot --nginx -d api.imagemeta.site
```

Saat proses Certbot, diminta email untuk notifikasi renewal. Email diisi agar jika certificate hampir expired, pemilik server mendapat pemberitahuan.

Setelah Certbot selesai, Nginx otomatis ditambahkan konfigurasi SSL:

```nginx
listen 443 ssl;
ssl_certificate /etc/letsencrypt/live/api.imagemeta.site/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/api.imagemeta.site/privkey.pem;
```

Hasil akhirnya, backend dapat diakses melalui HTTPS:

```text
https://api.imagemeta.site
```

### 11. Testing Integrasi Frontend dan Backend

Setelah frontend dan backend online, beberapa endpoint dites:

```bash
curl https://api.imagemeta.site/api/health
```

Tujuannya adalah memastikan backend aktif dan Nginx mengarah ke service yang benar.

Di frontend, beberapa fitur juga diuji:

1. Login Google.
2. Upload gambar.
3. Operasi pengolahan citra.
4. Scan Document.
5. Advanced Editor.
6. Histogram before-after.

Sempat muncul error:

```text
Request failed with status code 405
```

Error ini mengarah pada kemungkinan frontend memanggil URL API yang tidak tepat atau backend route belum sesuai. Perbaikan dilakukan dengan memastikan `VITE_API_URL` mengarah ke:

```text
https://api.imagemeta.site/api
```

dan backend memiliki route yang sesuai.

### 12. GitHub, Commit, dan Sync

Project menggunakan Git dan GitHub sebagai version control. Setiap perubahan penting di-commit dengan message yang menjelaskan perubahan, misalnya:

```text
Remove legacy cutout editor feature
Remove Scan Docs in Advanced Editor
add some security
fix guard scan document response fields
```

Setelah commit dibuat di VS Code, perubahan dikirim ke GitHub menggunakan tombol:

```text
Sync Changes
```

Sync Changes berarti commit lokal di-push ke GitHub. Setelah push berhasil:

1. Vercel otomatis mendeteksi commit baru.
2. Vercel menjalankan build frontend.
3. Jika build berhasil, website frontend otomatis ter-deploy.

Untuk backend, proses update masih manual:

```bash
ssh root@76.13.196.40
cd /var/www/image-metamorphosis
git pull
sudo systemctl restart imagemeta-api
sudo systemctl status imagemeta-api
```

Ini menjadi alasan kenapa backend CI/CD direncanakan sebagai pengembangan berikutnya, agar backend dapat auto-update setelah push ke GitHub.

### 13. Pengamanan dari Git dan Environment Exposure

Setelah website online, dilakukan pengecekan apakah folder `.git` dan file `.env` bisa diakses publik.

Command yang digunakan:

```bash
curl -i https://imagemeta.site/.git/config
curl -i https://api.imagemeta.site/.git/config
curl -i https://api.imagemeta.site/.env
```

Hasilnya:

```text
https://imagemeta.site/.git/config     -> 404
https://api.imagemeta.site/.git/config -> 404
https://api.imagemeta.site/.env        -> 404
```

Artinya file Git dan environment tidak terekspos publik. Untuk hardening tambahan, Nginx juga disarankan memblokir dotfiles dan file sensitif:

```nginx
location ^~ /.git {
    return 404;
}

location ~ /\.(?!well-known).* {
    return 404;
}

location ~* \.(env|ini|log|bak|sql|sqlite|db)$ {
    return 404;
}
```

Block ini diletakkan sebelum `location /` pada konfigurasi Nginx API.

### 14. Evaluasi Production Readiness

Setelah deployment berhasil, dilakukan evaluasi aspek production:

1. Authentication sudah ada melalui Firebase Google Sign-In.
2. Authorization masih basic karena belum ada role admin/user/premium.
3. Cloud compute sudah ada melalui Vercel dan VPS.
4. CI/CD frontend sudah ada melalui Vercel auto deploy.
5. CI/CD backend belum otomatis.
6. Version control sudah menggunakan GitHub.
7. Rate limiting dasar sudah ada di backend.
8. CDN sudah ada melalui Vercel dan Cloudinary.
9. Error tracking masih basic melalui logs server.
10. Availability dan recovery masih perlu ditingkatkan dengan backup dan monitoring.

Dari evaluasi ini, rencana berikutnya adalah membuat fitur yang lebih production-oriented:

1. Admin Dashboard.
2. Maintenance mode per operation.
3. Role dan plan user.
4. Premium feature dan ads.
5. Backend CI/CD.
6. Error tracking.
7. Uptime monitoring.

### 15. Keputusan Produk: Menghapus Fitur yang Tidak Stabil

Selama proses pengembangan, fitur cutout/remove background sempat dibuat tetapi hasilnya tidak konsisten. Hasilnya belum mampu menyamai layanan seperti remove.bg karena layanan tersebut menggunakan AI segmentation, sedangkan project ini hanya menggunakan OpenCV klasik.

Daripada mempertahankan fitur yang terlihat canggih tetapi hasilnya buruk, fitur tersebut dihapus dari frontend dan backend. Keputusan ini penting karena production product harus menjaga kualitas fitur yang ditampilkan.

Setelah penghapusan, Advanced Editor menjadi lebih fokus:

```text
crop, rotate, flip, adjust, export
```

Sedangkan Scan Document tetap menjadi fitur khusus yang memang relevan dengan OpenCV dan tujuan edukasi pengolahan citra.

---

## Hasil Akhir Saat Ini

Saat ini Image Metamorphosis sudah memiliki:

1. Frontend React/Vite dengan tampilan modern.
2. Backend Flask/OpenCV untuk proses pengolahan citra.
3. Operasi dasar citra, operasi titik, operasi aritmatika, operasi spasial, geometri, morfologi, segmentasi, dan deteksi tepi.
4. Advanced Editor untuk adjustment gambar umum.
5. Scan Document dengan beberapa mode output.
6. Histogram untuk analisis distribusi intensitas.
7. Login Google menggunakan Firebase Authentication.
8. API protection menggunakan Firebase ID token.
9. Integrasi domain produksi `imagemeta.site` dan API `api.imagemeta.site`.
10. Security hardening dasar pada backend.
11. Deployment frontend di Vercel dan backend di Hostinger VPS.
12. Repository yang lebih rapi dengan `.gitignore` dan README yang lebih profesional.

## Rencana Pengembangan Selanjutnya

Beberapa pengembangan yang masih dapat dilakukan:

1. Membuat Admin Dashboard untuk mengatur fitur aktif, maintenance, free, dan premium.
2. Menambahkan role dan plan user seperti `admin`, `user`, `free`, dan `premium`.
3. Membuat backend CI/CD agar update backend tidak perlu restart manual lewat SSH.
4. Menambahkan error tracking seperti Sentry atau logging ke database.
5. Menambahkan usage limit per user untuk mencegah abuse.
6. Menambahkan sistem premium dan iklan untuk monetisasi.
7. Menambahkan uptime monitoring dan backup recovery plan.
8. Mengoptimalkan performa image processing agar lebih cepat untuk gambar besar.

## Kesimpulan

Pengembangan Image Metamorphosis menunjukkan proses bertahap dari aplikasi eksperimen pengolahan citra menjadi aplikasi web yang lebih siap dipublikasikan. Project ini tidak hanya berfokus pada hasil visual, tetapi juga pada aspek edukasi, penjelasan konsep, keamanan dasar, deployment produksi, dan pengalaman pengguna.

Beberapa fitur yang kurang sesuai, seperti cutout/remove background berbasis OpenCV klasik, dievaluasi dan dihapus agar kualitas project tetap terjaga. Keputusan tersebut menunjukkan bahwa pengembangan tidak hanya menambah fitur, tetapi juga memilih fitur yang benar-benar stabil dan bermanfaat.

Secara keseluruhan, project ini sudah menjadi dasar yang kuat untuk dikembangkan lebih lanjut menjadi platform edukasi pengolahan citra digital yang lebih profesional dan siap digunakan publik.
