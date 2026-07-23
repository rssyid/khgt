# KHGT Kalender - Deploy ke Vercel (FIX 404 NOT_FOUND)

## Kenapa 404 terjadi sebelumnya
Konfigurasi lama menggunakan "builds" + "routes" campur dengan folder "static" terpisah.
Ini sering bikin Vercel salah mengarahkan request root "/" sehingga muncul 404: NOT_FOUND.

## Perbaikan pada versi ini
1. vercel.json sekarang HANYA memakai "rewrites" - semua request (termasuk "/") diarahkan ke
   satu serverless function: api/app.py
2. File kalender.html dipindahkan KE DALAM folder api/, dan Flask membacanya langsung
   via app.route("/") memakai path relatif ke file app.py. Ini menghindari masalah routing
   static file yang jadi sumber 404 di banyak kasus Flask + Vercel.
3. Tidak ada lagi folder static/ terpisah - semua diserve dari satu function Python.

## Struktur file
- api/app.py         -> Backend Flask (scraper + API + serve halaman kalender)
- api/kalender.html  -> Frontend, dibaca langsung oleh Flask saat request ke "/"
- requirements.txt   -> Dependency Python
- vercel.json        -> HANYA rewrites, tidak ada builds/routes manual

## Langkah Deploy

1. Upload SEMUA file dalam folder ini ke repo GitHub baru (struktur api/ harus dipertahankan).
2. Di Vercel Dashboard, kalau sebelumnya sudah ada project yang error 404:
   a. Buka project itu -> Settings -> Git -> pastikan Root Directory KOSONG (bukan menunjuk ke
      subfolder yang salah). Ini penyebab 404 paling umum kedua setelah masalah routing.
   b. Redeploy dari tab Deployments -> klik "..." pada deployment terakhir -> Redeploy.
   Kalau belum ada project, langsung:
3. Klik "Add New" -> "Project", pilih repo GitHub yang berisi file ini.
4. JANGAN ubah Root Directory (biarkan default, yaitu root repo itu sendiri).
5. Framework Preset: pilih "Other" jika Vercel tidak otomatis mendeteksi Python.
6. Klik Deploy, tunggu 1-2 menit.
7. Buka URL yang diberikan (misal https://khgt-kalender.vercel.app) - kalender harus langsung
   muncul di halaman utama, bukan 404.

## Kalau masih 404 setelah langkah di atas
Cek di Vercel Dashboard -> Deployments -> klik deployment terbaru -> tab "Functions":
- Jika api/app.py TIDAK muncul di daftar functions, artinya Vercel tidak mendeteksi file itu
  sebagai Python function. Pastikan requirements.txt ada di ROOT repo (bukan di dalam api/),
  dan file app.py benar-benar berada di folder bernama "api" persis di root repo.
- Cek juga tab "Build Logs" untuk error import (misal lxml gagal install) - errors di sini
  akan membuat function gagal deploy dan otomatis menghasilkan 404 saat diakses.

## Testing lokal sebelum push
Install Vercel CLI: npm install -g vercel
Jalankan dari root folder project: vercel dev
Buka http://localhost:3000
