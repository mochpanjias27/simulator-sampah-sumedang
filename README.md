# Simulator Dampak Kebijakan Sampah – Kabupaten Sumedang

Prototipe web untuk mensimulasikan dampak kebijakan pengurangan **kantong plastik belanja di minimarket**
terhadap timbulan sampah bernilai rendah (*low value*) di Kabupaten Sumedang.

Dikembangkan untuk **Talkshow Jatinangor Smart City – Smart Environment**, rangkaian Dies Natalis ke-68
FMIPA Universitas Padjadjaran (27 Oktober 2026), bersama SatuBumi dan Pemerintah Kabupaten Sumedang.

> **Catatan:** semua nilai awal adalah asumsi untuk ilustrasi. Angka bukan hasil kajian final dan akan
> dikalibrasi dengan data Pemkab Sumedang serta masukan SatuBumi.

## Dua versi tampilan

| Versi | Folder | Cocok untuk |
|---|---|---|
| **Web, gaya SITRAS / Command Center** | `web/` | Integrasi ke Command Center Sumedang. Tampilan sama dengan dashboard SITRAS (Bootstrap 4, Work Sans, ungu Poco). Berkas statis saja: tanpa server Python, bisa dipasang di server SITRAS atau di-*embed* dengan iframe. |
| Streamlit (versi awal) | `app.py`, `views/` | Tetap berjalan di Streamlit Community Cloud seperti sebelumnya. |

Kedua versi memakai model dan data yang sama. Model acuan ada di `src/model.py`; versi web memakai
terjemahannya di `web/js/model.js`, dan kesetaraan keduanya diuji otomatis (`tests/test_model_web.py`).

## Halaman

| Halaman | Isi |
|---|---|
| Ringkasan Skenario | Timbulan, pengurangan kotor dan bersih, rentang ketidakpastian, perbandingan 4 skenario |
| Peta Wilayah | Peta 26 kecamatan, pilihan wilayah penerapan, efek limpahan ke kecamatan tetangga, titik gerai |
| Proyeksi 2026–2029 | Proyeksi tahunan dengan pertumbuhan gerai, pita Monte Carlo P10–P90, perbandingan dengan target Masterplan |
| Asumsi & Parameter | Tabel parameter beserta rentang dan sumbernya, rumus, metode, kebutuhan data |

Parameter dan skenario diatur di panel kiri dan berlaku untuk semua halaman.

## Versi web (gaya SITRAS)

**Mencoba di komputer sendiri:** buka `web/index.html` langsung di peramban (klik dua kali), atau jalankan
server kecil agar peta dasar dan unduhan berjalan normal:

```bash
cd web
python -m http.server 8080      # lalu buka http://localhost:8080
```

**Alamat untuk Command Center:**

| Keperluan | Alamat (contoh di server SITRAS) |
|---|---|
| Tampilan lengkap | `https://sitras-sumedang.tech/simulator/` |
| Mode tertanam (tanpa menu samping, untuk iframe) | `https://sitras-sumedang.tech/simulator/?embed=1` |
| Langsung ke satu halaman | tambahkan `#ringkasan`, `#peta`, `#proyeksi`, atau `#asumsi` |

Contoh menu baru di Command Center:

```html
<iframe src="https://sitras-sumedang.tech/simulator/?embed=1#peta" style="width:100%;height:900px;border:0"></iframe>
```

**Memasang di server SITRAS (VPS):** lihat README SITRAS bagian *4b. Simulator Kebijakan Sampah*. Ringkasnya:
`git clone` repo ini di sebelah folder `sitras`, lalu web server SITRAS (Caddy) menyajikan folder `web/` di
alamat `/simulator/`. Pembaruan cukup dengan `git pull`, tanpa memulai ulang apa pun.

**Mengubah data atau parameter:** ubah `data/` atau daftar `PARAMETER` di `src/model.py` seperti biasa, lalu
bangkitkan ulang data versi web:

```bash
pip install -r requirements.txt
python scripts/build_web_data.py   # menulis web/js/data.js
pytest                             # memastikan versi web tetap sama dengan model Python
```

Parameter yang digeser di versi web disimpan di peramban masing-masing pengguna. Berkas CSV lokasi gerai yang
diunggah diproses di peramban saja, tidak dikirim ke server.

## Menjalankan versi Streamlit di komputer sendiri

Butuh Python 3.10 atau lebih baru.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Aplikasi terbuka di http://localhost:8501.

## Menerbitkan versi Streamlit

**Streamlit Community Cloud (gratis):**

1. Unggah folder ini ke repositori GitHub.
2. Masuk ke https://share.streamlit.io dengan akun GitHub, pilih **Create app**.
3. Pilih repositori, cabang `main`, dan berkas utama `app.py`, lalu **Deploy**.

Aplikasi di layanan gratis akan "tidur" bila lama tidak dibuka. Buka beberapa menit sebelum demo.

**Server sendiri (misalnya server Unpad):**

```bash
pip install -r requirements.txt
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

Untuk alamat domain dan HTTPS, pasang di belakang reverse proxy (Nginx/Caddy).

## Struktur

```
web/                    versi web gaya SITRAS (statis)
  index.html            kerangka halaman
  js/app.js             tampilan, grafik, peta
  js/model.js           model (terjemahan src/model.py)
  js/data.js            data hasil scripts/build_web_data.py (jangan diedit manual)
  css/style.css         gaya SITRAS / Command Center
  vendor/               Bootstrap, Leaflet, ApexCharts, DataTables, font Work Sans (tanpa CDN)
scripts/build_web_data.py  bangkitkan web/js/data.js dari data/ dan src/model.py
app.py                  navigasi dan panel parameter (Streamlit)
src/model.py            model (terpisah dari tampilan; bisa diuji dan dikutip)
src/data.py             batas kecamatan, tetangga, titik gerai
src/ui.py               tema, kartu angka, panel parameter
views/                  empat halaman aplikasi
data/kecamatan.csv      jumlah gerai asumsi per kecamatan
data/kecamatan_sumedang.geojson   batas kecamatan
tests/test_model.py     uji model (jalankan: pytest)
tests/test_model_web.py uji kesetaraan model web dan Python (butuh Node.js)
.streamlit/config.toml  tema warna
```

## Mengganti data

- **Parameter dan rentang ketidakpastian:** ubah daftar `PARAMETER` di `src/model.py`, termasuk kolom `sumber`.
- **Jumlah gerai per kecamatan:** ubah `data/kecamatan.csv`.
- **Lokasi gerai sebenarnya:** di halaman *Peta Wilayah*, buka *Gunakan data lokasi gerai sendiri* lalu unggah
  CSV berkolom `lat` dan `lon`. Kecamatan ditentukan otomatis dari koordinat.
- **Batas kecamatan resmi:** ganti `data/kecamatan_sumedang.geojson` (properti `id` dan `nama` harus sama
  dengan `data/kecamatan.csv`).

## Model singkat

- Timbulan per gerai: transaksi × kantong × berat × 365.
- Pengurangan kotor: timbulan × kepatuhan × faktor skenario.
- Pengurangan bersih: kotor − kantong sampah pengganti − perpindahan ke warung/pasar.
- Spasial: perpindahan dibagi rata ke kecamatan tetangga yang belum menerapkan kebijakan.
- Proyeksi: jumlah gerai tumbuh per tahun; skenario bertahap naik dari efek tahun pertama hingga penuh.
- Monte Carlo: parameter diambil dari distribusi segitiga (min, nilai dipakai, maks); dilaporkan P10–P90.

## Sumber data

- Batas kecamatan: data terbuka *idn-geojson* (turunan cahyadsn/GADM), disederhanakan; belum batas resmi.
- Peta dasar: © OpenStreetMap contributors.
- Target pengurangan residu: Masterplan Kawasan Pendidikan Jatinangor – City of Digital Knowledge, Pemkab Sumedang.
