import plotly.graph_objects as go
import streamlit as st

from src import model, ui

ui.header("Proyeksi Dampak 2026–2029",
          "Model stok-alir tahunan dengan pertumbuhan gerai dan rentang ketidakpastian Monte Carlo")

p = ui.params()
sk = st.session_state["skenario"]
TARGET = {2025: 10, 2026: 20, 2027: 30, 2028: 40, 2029: 50}

with st.container(border=True):
    a, b, c = st.columns([1, 1, 1.4])
    mulai = a.selectbox("Kebijakan mulai berlaku", [2026, 2027, 2028], index=1)
    n = b.select_slider("Jumlah simulasi Monte Carlo", [500, 1000, 2000, 5000], value=2000)
    residu = c.number_input("Timbulan sampah residu Kab. Sumedang (ton/tahun)", min_value=0.0, value=0.0,
                            step=1000.0, help="Isi dari data DLHK/SIPSN untuk membandingkan dengan target Masterplan. "
                                              "Biarkan 0 bila belum ada data.")

proj = model.proyeksi(p, sk, tahun_mulai=mulai)
mc = model.monte_carlo(p, sk, n=n, tahun_mulai=mulai)
tahun = proj["tahun"].tolist()
akhir = proj.iloc[-1]

c1, c2, c3 = st.columns(3)
with c1:
    ui.kpi("Timbulan kantong 2029 tanpa kebijakan", ui.angka(akhir["timbulan"]), "ton/tahun",
           f"{ui.angka(akhir['gerai'], 0)} gerai")
with c2:
    ui.kpi("Pengurangan bersih 2029", ui.angka(akhir["bersih"]), "ton/tahun",
           f"rentang P10–P90: {ui.angka(mc.iloc[-1]['p10'])}–{ui.angka(mc.iloc[-1]['p90'])}", "utama")
with c3:
    kumulatif = proj["bersih"].sum()
    ui.kpi(f"Kumulatif {tahun[0]}–{tahun[-1]}", ui.angka(kumulatif), "ton",
           f"≈ {ui.angka(kumulatif * 1e6 / p['berat'] / 1e6)} juta lembar kantong dicegah")
st.write("")

with st.container(border=True):
    st.markdown(f"### Timbulan kantong plastik: tanpa dan dengan kebijakan")
    st.caption(f"Skenario **{model.SKENARIO[sk]}**, mulai {mulai}. Pita menunjukkan rentang P10–P90 hasil "
               f"{n:,} simulasi dengan parameter acak di dalam rentang ketidakpastiannya.".replace(",", "."))
    atas = proj["timbulan"] - mc["p10"]
    bawah = proj["timbulan"] - mc["p90"]
    fig = go.Figure()
    fig.add_scatter(x=tahun, y=atas, line=dict(width=0), showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=tahun, y=bawah, fill="tonexty", fillcolor="rgba(15,92,99,0.18)", line=dict(width=0),
                    name="Rentang P10–P90", hoverinfo="skip")
    fig.add_scatter(x=tahun, y=proj["timbulan"], name="Tanpa kebijakan", mode="lines+markers",
                    line=dict(color=ui.OKER, width=3, dash="dot"),
                    hovertemplate="%{x}: %{y:,.1f} ton<extra>Tanpa kebijakan</extra>")
    fig.add_scatter(x=tahun, y=proj["timbulan"] - proj["bersih"], name="Dengan kebijakan", mode="lines+markers",
                    line=dict(color=ui.TEAL, width=3),
                    hovertemplate="%{x}: %{y:,.1f} ton<extra>Dengan kebijakan</extra>")
    fig.add_vline(x=mulai - 0.5, line=dict(color=ui.REDUP, dash="dash", width=1),
                  annotation_text="kebijakan berlaku", annotation_position="top right")
    fig.update_layout(height=380, margin=dict(l=0, r=0, t=20, b=0), yaxis_title="ton per tahun",
                      xaxis=dict(dtick=1, gridcolor="#E6E1D6"), yaxis=dict(gridcolor="#E6E1D6", rangemode="tozero"),
                      legend=dict(orientation="h", y=-0.15), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Public Sans, system-ui, sans-serif"))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

kiri, kanan = st.columns([1.4, 1])
with kiri:
    with st.container(border=True):
        st.markdown("### Kontribusi terhadap target Masterplan")
        if residu > 0:
            kontrib = proj["bersih"] / residu * 100
            fig = go.Figure()
            fig.add_bar(x=tahun, y=kontrib, name="Kontribusi kebijakan ini", marker_color=ui.TEAL,
                        text=[ui.angka(v, 2) + "%" for v in kontrib], textposition="outside",
                        hovertemplate="%{x}: %{y:.2f}%<extra></extra>")
            fig.add_scatter(x=tahun, y=[TARGET[t] for t in tahun], name="Target pengurangan residu",
                            mode="lines+markers", line=dict(color=ui.OKER, width=2, dash="dash"))
            fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="% dari residu",
                              xaxis=dict(dtick=1), yaxis=dict(gridcolor="#E6E1D6"),
                              legend=dict(orientation="h", y=-0.2), paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Public Sans, system-ui, sans-serif"))
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            st.caption("Kebijakan kantong plastik hanyalah satu dari beberapa program menuju target. Grafik ini "
                       "menunjukkan seberapa besar porsi yang bisa disumbangkannya.")
        else:
            st.info("Isi **timbulan sampah residu Kabupaten Sumedang** di atas untuk melihat porsi kebijakan "
                    "ini terhadap target Masterplan (10% pada 2025 hingga 50% pada 2029).")
with kanan:
    with st.container(border=True):
        st.markdown("### Tabel proyeksi")
        tab = proj[["tahun", "gerai", "timbulan", "bersih", "substitusi", "perpindahan"]].copy()
        tab["p10"], tab["p90"] = mc["p10"], mc["p90"]
        tab = tab.rename(columns={"tahun": "Tahun", "gerai": "Gerai", "timbulan": "Timbulan (t)",
                                  "bersih": "Bersih (t)", "substitusi": "Pengganti (t)",
                                  "perpindahan": "Pindah (t)", "p10": "P10 (t)", "p90": "P90 (t)"})
        st.dataframe(tab.round(1), hide_index=True, width="stretch")
        st.download_button("Unduh CSV", tab.to_csv(index=False).encode("utf-8"), "proyeksi.csv", "text/csv",
                           width="stretch")
