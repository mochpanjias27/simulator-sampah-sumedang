import pandas as pd
import streamlit as st

from src import model, ui

ui.header("Asumsi & Parameter Model",
          "Semua angka yang dipakai simulator, rentang ketidakpastiannya, dan rumus perhitungannya")

p = ui.params()
st.markdown("Halaman ini dipakai untuk menelaah model bersama **SatuBumi** dan **Pemkab Sumedang**. "
            "Setiap parameter yang masih berupa asumsi perlu diganti dengan data lapangan atau literatur, "
            "lalu sumbernya dicatat di kolom *Sumber*.")

tab = pd.DataFrame([{
    "Parameter": q.label, "Nilai dipakai": p[q.kunci], "Nilai awal": q.nilai, "Satuan": q.satuan,
    "Rentang Monte Carlo": f"{ui.angka(q.mc_min, 1)} – {ui.angka(q.mc_maks, 1)}" if q.kunci != "total_gerai" else "tetap",
    "Keterangan": q.keterangan, "Sumber": q.sumber,
} for q in model.PARAMETER])
st.dataframe(tab, hide_index=True, width="stretch")
st.download_button("Unduh tabel parameter (CSV)", tab.to_csv(index=False).encode("utf-8"),
                   "parameter_model.csv", "text/csv")

kiri, kanan = st.columns(2)
with kiri:
    with st.container(border=True):
        st.markdown("### Rumus inti")
        st.markdown("Timbulan kantong per gerai per tahun:")
        st.latex(r"T = \text{transaksi} \times \text{kantong} \times \text{berat} \times 365 \;/\; 10^{6}\ \ \text{(ton)}")
        st.markdown("Pengurangan kotor, dengan *k* = kepatuhan dan *f* = faktor skenario:")
        st.latex(r"K = T \times k \times f")
        st.markdown("- Larangan penuh: *f* = 1\n"
                    "- Kantong berbayar: *f* = efek kantong berbayar\n"
                    "- Bertahap: *f* = efek tahun pertama, lalu rata-ratanya dengan 1 pada tahun kedua, "
                    "dan 1 mulai tahun ketiga")
        st.markdown("Pengurangan bersih setelah efek samping:")
        st.latex(r"B = K - \underbrace{K \times s}_{\text{kantong sampah pengganti}} - \underbrace{K \times m}_{\text{pindah ke warung/pasar}}")
        st.markdown("Proyeksi tahunan: jumlah gerai tumbuh dengan laju *g*, yaitu "
                    "gerai(*t*) = gerai(2026) × (1 + *g*)^(*t* − 2026).")
with kanan:
    with st.container(border=True):
        st.markdown("### Metode")
        st.markdown(
            "- **Skenario**: membandingkan empat opsi kebijakan pada parameter yang sama.\n"
            "- **Spasial**: dihitung per kecamatan. Perpindahan belanja dari kecamatan yang menerapkan "
            "kebijakan dibagi rata ke tetangga yang belum menerapkan (*limpahan*).\n"
            "- **Proyeksi (stok-alir)**: dampak tahunan 2026–2029 dengan pertumbuhan gerai dan "
            "penerapan bertahap.\n"
            "- **Monte Carlo**: parameter diambil acak dari distribusi segitiga (minimum, nilai dipakai, "
            "maksimum) untuk memperoleh rentang P10–P90.")
    with st.container(border=True):
        st.markdown("### Masukan yang dibutuhkan")
        st.markdown(
            "- **Pemkab Sumedang**: jumlah dan lokasi minimarket/swalayan, timbulan dan komposisi sampah, "
            "data TPS3R, kebijakan yang direncanakan.\n"
            "- **SatuBumi**: berat kantong, pola pakai ulang kantong, nasib akhir kantong di lapangan, "
            "kewajaran angka kepatuhan dan perubahan perilaku.\n"
            "- **Pengelola ritel**: rata-rata transaksi dan kantong per transaksi.")

st.markdown('<div class="catatan">Prototipe untuk Talkshow Jatinangor Smart City, Dies Natalis ke-68 FMIPA Unpad. '
            'Angka bukan hasil kajian final.</div>', unsafe_allow_html=True)
