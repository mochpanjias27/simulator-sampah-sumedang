import plotly.graph_objects as go
import streamlit as st

from src import model, ui

ui.header("Simulator Dampak Kebijakan Sampah",
          "Jatinangor Smart Environment · Studi kasus: kantong plastik belanja di minimarket Kabupaten Sumedang")

p = ui.params()
sk = st.session_state["skenario"]
r = model.ringkasan(p, sk)
mc = model.monte_carlo(p, sk, n=2000, tahun_akhir=model.TAHUN_DASAR).iloc[0]

c1, c2, c3, c4 = st.columns(4)
with c1:
    ui.kpi("Timbulan kantong saat ini", ui.angka(r["timbulan"]), "ton/tahun",
           f"≈ {ui.angka(r['lembar_juta'])} juta lembar per tahun")
with c2:
    ui.kpi("Pengurangan kotor", ui.angka(r["kotor"]), "ton/tahun", "sebelum efek samping")
with c3:
    ui.kpi("Pengurangan bersih", ui.angka(r["bersih"]), "ton/tahun",
           f"rentang P10–P90: {ui.angka(mc['p10'])}–{ui.angka(mc['p90'])} ton", "utama")
with c4:
    ui.kpi("Efektivitas bersih", ui.angka(r["efektivitas"] * 100, 0), "%", "dari timbulan kantong")

st.write("")

# --- dari dampak kotor ke bersih ---
with st.container(border=True):
    st.markdown(f"### Dari dampak kotor ke dampak bersih")
    st.caption(f"Skenario: **{model.SKENARIO[sk]}** · berlaku di seluruh Kabupaten Sumedang")
    bagian = [("Pengurangan bersih", r["bersih"], ui.TEAL),
              ("Kantong sampah pengganti", r["substitusi"], ui.OKER),
              ("Pindah ke warung/pasar", r["perpindahan"], ui.PASIR),
              ("Tetap beredar", r["tetap"], ui.ABU)]
    fig = go.Figure()
    for nama, nilai, warna in bagian:
        fig.add_bar(y=[""], x=[nilai], name=f"{nama}: {ui.angka(nilai)} t", orientation="h",
                    marker_color=warna, hovertemplate=f"{nama}: %{{x:,.1f}} ton<extra></extra>")
    fig.update_layout(barmode="stack", height=150, margin=dict(l=0, r=0, t=0, b=0),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(title="ton per tahun", gridcolor="#E6E1D6"),
                      legend=dict(orientation="h", y=-0.6, x=0, traceorder="normal"), font=dict(family="Public Sans, system-ui, sans-serif"))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

kiri, kanan = st.columns([2, 1])
with kiri:
    with st.container(border=True):
        st.markdown("### Perbandingan skenario")
        st.caption("Pengurangan bersih sampah kantong plastik, ton per tahun (tahun pertama)")
        nama = list(model.SKENARIO.values())
        nilai = [model.ringkasan(p, k)["bersih"] for k in model.SKENARIO]
        warna = [ui.TEAL if k == sk else "#8FB3AF" for k in model.SKENARIO]
        fig = go.Figure(go.Bar(x=nilai, y=nama, orientation="h", marker_color=warna,
                               text=[ui.angka(v) for v in nilai], textposition="outside",
                               hovertemplate="%{y}: %{x:,.1f} ton<extra></extra>"))
        fig.update_layout(height=260, margin=dict(l=0, r=40, t=0, b=0), yaxis=dict(autorange="reversed"),
                          xaxis=dict(gridcolor="#E6E1D6", range=[0, max(nilai + [1]) * 1.15]),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font=dict(family="Public Sans, system-ui, sans-serif"))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
with kanan:
    st.markdown(
        '<div class="kotak"><div class="serif" style="font-size:20px;margin-bottom:6px">Kaitan dengan Masterplan</div>'
        'Hasil dibaca terhadap indikator <b>persentase pengurangan sampah residu</b> dan '
        '<b>Volume Sampah Terolah vs Residu</b> pada pilar <i>Smart Environment</i> Masterplan '
        'Kawasan Pendidikan Jatinangor.<br><br>Target: pengurangan residu <b>20% (2026)</b> hingga '
        '<b>50% (2029)</b>. Lihat halaman <b>Proyeksi 2026–2029</b> untuk perbandingan tahunan.</div>',
        unsafe_allow_html=True)
