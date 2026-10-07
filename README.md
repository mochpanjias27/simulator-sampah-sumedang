# Simulator Dampak Kebijakan Sampah – Kabupaten Sumedang

Prototipe web untuk mensimulasikan dampak kebijakan pengurangan **kantong plastik belanja di minimarket**
terhadap timbulan sampah bernilai rendah (*low value*) di Kabupaten Sumedang.

Dikembangkan untuk **Talkshow Jatinangor Smart City – Smart Environment**, rangkaian Dies Natalis ke-68
FMIPA Universitas Padjadjaran (27 Oktober 2026), bersama SatuBumi dan Pemerintah Kabupaten Sumedang.

> **Catatan:** semua nilai awal adalah asumsi untuk ilustrasi. Angka bukan hasil kajian final dan akan
> dikalibrasi dengan data Pemkab Sumedang serta masukan SatuBumi.

## Halaman

| Halaman | Isi |
|---|---|
| Ringkasan Skenario | Timbulan, pengurangan kotor dan bersih, rentang ketidakpastian, perbandingan 4 skenario |
| Peta Wilayah | Peta 26 kecamatan, pilihan wilayah penerapan, efek limpahan ke kecamatan tetangga, titik gerai |
| Proyeksi 2026–2029 | Proyeksi tahunan dengan pertumbuhan gerai, pita Monte Carlo P10–P90, perbandingan dengan target Masterplan |
| Asumsi & Parameter | Tabel parameter beserta rentang dan sumbernya, rumus, metode, kebutuhan data |

Parameter dan skenario diatur di panel kiri dan berlaku untuk semua halaman.

## Menjalankan di komputer sendiri

Butuh Python 3.10 atau lebih baru.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Aplikasi terbuka di http://localhost:8501.

## Menerbitkan ke web

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
app.py                  navigasi dan panel parameter
src/model.py            model (terpisah dari tampilan; bisa diuji dan dikutip)
src/data.py             batas kecamatan, tetangga, titik gerai
src/ui.py               tema, kartu angka, panel parameter
views/                  empat halaman aplikasi
data/kecamatan.csv      jumlah gerai asumsi per kecamatan
data/kecamatan_sumedang.geojson   batas kecamatan
tests/test_model.py     uji model (jalankan: pytest)
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
