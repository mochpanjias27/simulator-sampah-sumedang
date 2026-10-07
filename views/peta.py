import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from src import data, model, ui

ui.header("Peta Dampak Kebijakan per Kecamatan",
          "Kabupaten Sumedang · 26 kecamatan · pilih wilayah penerapan dan lihat dampaknya")

ss = st.session_state
p = ui.params()
sk = ss["skenario"]
dasar = data.kecamatan_dasar()
NAMA = dict(zip(dasar["id"], dasar["nama"]))
PRESET = {
    "Seluruh Sumedang": list(dasar["id"]),
    "Jatinangor & sekitar": ["jatinangor", "cimanggung", "tanjungsari", "rancakalong"],
    "Jatinangor saja": ["jatinangor"],
    "Kosongkan": [],
}
ss.setdefault("terapan", PRESET["Jatinangor & sekitar"])
ss.setdefault("fokus", "jatinangor")
ss.setdefault("klik_terakhir", None)
# widget dibuat ulang tiap halaman dibuka; ambil nilainya dari state persisten
ss.setdefault("w_terapan", list(ss["terapan"]))


def _sinkron():
    ss["terapan"] = list(ss["w_terapan"])


def _preset(ids):
    ss["terapan"] = list(ids)
    ss["w_terapan"] = list(ids)


def _toggle(kid):
    t = list(ss["terapan"])
    t.remove(kid) if kid in t else t.append(kid)
    _preset(t)


if sk == "saat_ini":
    st.info("Skenario **Kondisi saat ini** tidak mengubah apa pun. Pilih skenario kebijakan di panel kiri.")

# ---------- pilihan wilayah ----------
with st.container(border=True):
    a, b = st.columns([1.3, 2])
    with a:
        st.markdown("**Cakupan wilayah cepat**")
        cols = st.columns(2)
        for i, (lbl, ids) in enumerate(PRESET.items()):
            cols[i % 2].button(lbl, on_click=_preset, args=(ids,), width="stretch")
    with b:
        st.multiselect("Kecamatan yang menerapkan kebijakan", list(dasar["id"]), format_func=NAMA.get,
                       key="w_terapan", on_change=_sinkron)

terapan = set(ss["terapan"])
override = ss.get("override_gerai")
kec = data.kecamatan(p["total_gerai"], override)
hasil = model.spasial(kec, terapan, p, sk)
H = hasil.set_index("id")

# ---------- angka ringkas ----------
c1, c2, c3, c4 = st.columns(4)
with c1:
    ui.kpi("Kecamatan diterapkan", f"{len(terapan)}", "/ 26")
with c2:
    ui.kpi("Gerai tercakup", ui.angka(hasil.loc[hasil.diterapkan, "gerai"].sum(), 0),
           f"/ {ui.angka(hasil['gerai'].sum(), 0)}")
with c3:
    ui.kpi("Pengurangan bersih", ui.angka(hasil["bersih"].sum()), "t/th", gaya_kartu="utama")
with c4:
    ui.kpi("Limpahan ke wilayah lain", ui.angka(hasil["limpahan_keluar"].sum()), "t/th",
           "belanja pindah ke kecamatan tetangga", "oker")
st.write("")

# ---------- peta ----------
maks = max(hasil["bersih"].max(), 1e-9)


def warna(kid):
    q = H.loc[kid]
    if q["diterapkan"]:
        t = q["bersih"] / maks
        return ui.TEAL if t > 0.6 else ui.TEAL_MUDA if t > 0.25 else ui.TEAL_PUCAT
    return ui.LIMPAHAN if q["limpahan_masuk"] > 0 else ui.ABU


gj = data.geojson()
for f in gj["features"]:
    kid = f["properties"]["id"]
    q = H.loc[kid]
    f["properties"].update({
        "status": q["status"], "gerai": ui.angka(q["gerai"], 0),
        "bersih": ui.angka(q["bersih"]), "limpahan": ui.angka(q["limpahan_masuk"]),
    })

kiri, kanan = st.columns([2.2, 1])
with kiri:
    with st.container(border=True):
        st.markdown("### Peta sebaran gerai dan dampak kebijakan")
        m = folium.Map(location=[-6.81, 107.98], zoom_start=10, tiles="OpenStreetMap",
                       control_scale=True)
        m.fit_bounds([[-7.05, 107.74], [-6.57, 108.23]])
        folium.GeoJson(
            gj, name="Kecamatan",
            style_function=lambda f: {"fillColor": warna(f["properties"]["id"]), "fillOpacity": 0.72,
                                      "color": ui.TEAL_TUA if f["properties"]["id"] == ss["fokus"] else "#FFFFFF",
                                      "weight": 3 if f["properties"]["id"] == ss["fokus"] else 1.2},
            highlight_function=lambda f: {"weight": 3, "color": ui.TEAL_TUA},
            tooltip=folium.GeoJsonTooltip(
                fields=["nama", "status", "gerai", "bersih", "limpahan"],
                aliases=["Kecamatan", "Status", "Gerai", "Pengurangan bersih (t/th)", "Limpahan diterima (t/th)"]),
        ).add_to(m)

        tampil_titik = st.toggle("Tampilkan titik gerai", value=True)
        if tampil_titik:
            titik = ss.get("titik_gerai")
            if titik is None:
                jumlah = tuple((r.id, r.gerai) for r in kec.itertuples())
                titik = data.titik_ilustrasi(jumlah)
            for t in titik.itertuples():
                on = t.kecamatan in terapan
                folium.CircleMarker([t.lat, t.lon], radius=3, weight=1,
                                    color="#FFFFFF" if on else "#FFF6E6",
                                    fill=True, fill_opacity=1,
                                    fill_color=ui.TEAL_TUA if on else ui.OKER).add_to(m)
        keluar = st_folium(m, height=560, use_container_width=True, center=(-6.81, 107.985), zoom=10,
                           returned_objects=["last_active_drawing"], key="peta")
        st.markdown(
            '<div class="leg">'
            f'<div><span class="sw" style="background:{ui.TEAL}"></span><span class="sw" style="background:{ui.TEAL_MUDA}"></span>'
            f'<span class="sw" style="background:{ui.TEAL_PUCAT}"></span>Diterapkan (pengurangan tinggi–rendah)</div>'
            f'<div><span class="sw" style="background:{ui.LIMPAHAN}"></span>Menerima limpahan</div>'
            f'<div><span class="sw" style="background:{ui.ABU}"></span>Belum diterapkan</div>'
            f'<div><span class="sw" style="background:{ui.TEAL_TUA};border-radius:50%"></span>Gerai patuh</div>'
            f'<div><span class="sw" style="background:{ui.OKER};border-radius:50%"></span>Gerai belum diatur</div>'
            '</div>', unsafe_allow_html=True)

    # klik pada peta -> fokus kecamatan
    klik = (keluar or {}).get("last_active_drawing")
    if klik:
        kid = klik.get("properties", {}).get("id")
        if kid and kid != ss["klik_terakhir"]:
            ss["klik_terakhir"] = kid
            ss["fokus"] = kid
            st.rerun()

with kanan:
    with st.container(border=True):
        st.markdown("**Detail kecamatan**")
        st.caption("Klik wilayah di peta atau pilih di sini")
        ids = list(dasar["id"])
        fokus = st.selectbox("Kecamatan", ids, index=ids.index(ss["fokus"]), format_func=NAMA.get,
                             label_visibility="collapsed")
        ss["fokus"] = fokus
        q = H.loc[fokus]
        warna_status = ui.TEAL if q["diterapkan"] else "#8A520D" if q["limpahan_masuk"] > 0 else ui.REDUP
        st.markdown(f'<div class="serif" style="font-size:26px">{NAMA[fokus]}</div>'
                    f'<div style="font-weight:700;color:{warna_status}">{q["status"]}</div>',
                    unsafe_allow_html=True)
        sel = lambda l, v: (f'<div><div style="font-size:13px;color:{ui.REDUP}">{l}</div>'
                            f'<div style="font-size:19px;font-weight:700">{v}</div></div>')
        st.markdown('<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:10px 0 14px">'
                    + sel("Gerai", ui.angka(q["gerai"], 0))
                    + sel("Timbulan kantong", f"{ui.angka(q['timbulan'])} t/th")
                    + sel("Pengurangan bersih", f"{ui.angka(q['bersih'])} t/th")
                    + sel("Limpahan diterima", f"{ui.angka(q['limpahan_masuk'])} t/th")
                    + '</div>', unsafe_allow_html=True)
        st.button("Cabut kebijakan di kecamatan ini" if q["diterapkan"] else "Terapkan kebijakan di kecamatan ini",
                  on_click=_toggle, args=(fokus,), width="stretch",
                  type="secondary" if q["diterapkan"] else "primary")

    with st.container(border=True):
        st.markdown("**Dampak terbesar**")
        top = hasil[hasil["bersih"] > 0].sort_values("bersih").tail(8)
        if top.empty:
            st.caption("Belum ada kecamatan yang menerapkan kebijakan.")
        else:
            fig = go.Figure(go.Bar(x=top["bersih"], y=top["nama"], orientation="h", marker_color=ui.TEAL,
                                   text=[ui.angka(v) for v in top["bersih"]], textposition="outside",
                                   hovertemplate="%{y}: %{x:,.1f} t/th<extra></extra>"))
            fig.update_layout(height=40 + 30 * len(top), margin=dict(l=0, r=30, t=0, b=0),
                              xaxis=dict(visible=False, range=[0, top["bersih"].max() * 1.3]),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(family="Public Sans, system-ui, sans-serif", size=12))
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

# ---------- tabel & data gerai ----------
with st.expander("Tabel hasil per kecamatan"):
    tab = hasil[["nama", "status", "gerai", "timbulan", "bersih", "substitusi", "perpindahan", "limpahan_masuk"]]
    tab = tab.rename(columns={"nama": "Kecamatan", "status": "Status", "gerai": "Gerai",
                              "timbulan": "Timbulan (t/th)", "bersih": "Pengurangan bersih (t/th)",
                              "substitusi": "Kantong pengganti (t/th)", "perpindahan": "Perpindahan (t/th)",
                              "limpahan_masuk": "Limpahan diterima (t/th)"})
    st.dataframe(tab.round(2), hide_index=True, width="stretch")
    st.download_button("Unduh CSV", tab.to_csv(index=False).encode("utf-8"), "hasil_per_kecamatan.csv", "text/csv")

with st.expander("Gunakan data lokasi gerai sendiri (CSV)"):
    st.markdown("Unggah CSV dengan kolom **lat** dan **lon** (opsional: **nama**). Kecamatan tiap gerai "
                "ditentukan otomatis dari koordinat, lalu jumlah gerai per kecamatan dan total gerai ikut diperbarui.")
    berkas = st.file_uploader("Berkas CSV", type="csv", label_visibility="collapsed")
    if berkas is not None and st.button("Terapkan data gerai", type="primary"):
        df = pd.read_csv(berkas)
        df.columns = [c.strip().lower() for c in df.columns]
        if not {"lat", "lon"} <= set(df.columns):
            st.error("Kolom lat dan lon tidak ditemukan.")
        else:
            df = data.tetapkan_kecamatan(df[["lat", "lon"]].dropna())
            luar = df["kecamatan"].isna().sum()
            df = df.dropna(subset=["kecamatan"])
            ss["titik_gerai"] = df
            ss["override_gerai"] = df["kecamatan"].value_counts().to_dict()
            ss["pending_total"] = len(df)
            st.success(f"{len(df)} gerai dipakai; {luar} titik di luar Kabupaten Sumedang diabaikan.")
            st.rerun()
    if ss.get("override_gerai") and st.button("Kembali ke data asumsi"):
        for k in ("titik_gerai", "override_gerai"):
            ss.pop(k, None)
        ss["pending_total"] = model.DEFAULT["total_gerai"]
        st.rerun()

st.markdown('<div class="catatan">Batas kecamatan: data terbuka turunan GADM/cahyadsn, belum batas resmi. '
            + ("Titik gerai berasal dari data yang diunggah." if ss.get("override_gerai") else
               "Posisi titik gerai acak di dalam kecamatan dan jumlahnya asumsi (ilustrasi).")
            + ' Perpindahan belanja dari kecamatan yang menerapkan kebijakan dibagi rata ke kecamatan '
              'tetangga yang belum menerapkan.</div>', unsafe_allow_html=True)
