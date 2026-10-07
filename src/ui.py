"""Komponen tampilan bersama: tema, kartu angka, panel parameter."""
from __future__ import annotations

import streamlit as st

from src import model

# Palet mengikuti rancangan prototipe
TEAL = "#0F5C63"
TEAL_TUA = "#13343A"
TEAL_MUDA = "#5E9E9A"
TEAL_PUCAT = "#B7D6D2"
OKER = "#B06A12"
PASIR = "#E8C27E"
LIMPAHAN = "#EFCB86"
KREM = "#F4F1EA"
ABU = "#DCD6C8"
TINTA = "#1B2A2F"
REDUP = "#55615F"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&display=swap');
html, body, [class*="css"], .stMarkdown, .stText, label, button, input {{ font-family: 'Public Sans', system-ui, sans-serif; }}
h1, h2, h3, .serif {{ font-family: 'Source Serif 4', Georgia, serif !important; font-weight: 600 !important; color: {TINTA}; }}
.block-container {{ padding-top: 1.2rem; max-width: 1400px; }}
[data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid #DDD7CA; }}
.hdr {{ background: {TEAL_TUA}; color: {KREM}; border-radius: 14px; padding: 18px 26px; margin-bottom: 18px;
        display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }}
.hdr .t {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 26px; font-weight: 600; }}
.hdr .s {{ font-size: 14px; color: #C9D6D4; margin-top: 2px; }}
.chip {{ font-size: 12px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; padding: 5px 11px;
         border: 1px solid #7FA3A0; border-radius: 999px; color: #E4ECEA; white-space: nowrap; }}
.kpi {{ background: #FFFFFF; border: 1px solid #DDD7CA; border-radius: 14px; padding: 16px 18px; height: 100%; }}
.kpi .l {{ font-size: 14px; color: {REDUP}; }}
.kpi .v {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 34px; font-weight: 600; color: {TINTA}; line-height: 1.15; margin-top: 4px; }}
.kpi .v small {{ font-size: 16px; color: {REDUP}; font-family: 'Public Sans', sans-serif; }}
.kpi .d {{ font-size: 13px; color: {REDUP}; margin-top: 4px; }}
.kpi.utama {{ background: {TEAL}; border-color: {TEAL}; }}
.kpi.utama .l, .kpi.utama .d, .kpi.utama .v small {{ color: #D6E6E4; }}
.kpi.utama .v {{ color: #FFFFFF; }}
.kpi.oker .v {{ color: #8A520D; }}
.kotak {{ background: #EAF1F0; border: 1px solid #C6D9D6; border-radius: 14px; padding: 16px 18px; font-size: 14px; line-height: 1.6; color: #2F3B39; }}
.catatan {{ font-size: 13px; color: {REDUP}; line-height: 1.55; }}
.leg {{ display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 13px; color: #3E4A48; margin-top: 6px; }}
.leg span.sw {{ display: inline-block; width: 13px; height: 13px; border-radius: 3px; margin-right: 6px; vertical-align: -2px; }}
</style>
"""


def gaya():
    st.markdown(CSS, unsafe_allow_html=True)


def header(judul: str, sub: str):
    st.markdown(
        f'<div class="hdr"><div><div class="t">{judul}</div><div class="s">{sub}</div></div>'
        f'<div style="display:flex;gap:10px;align-items:center"><span class="chip">Prototipe</span>'
        f'<span class="s" style="margin:0">FMIPA Unpad × SatuBumi × Pemkab Sumedang</span></div></div>',
        unsafe_allow_html=True)


def angka(x: float, d: int = 1) -> str:
    """Format angka gaya Indonesia: 1.234,5"""
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def kpi(label: str, nilai: str, satuan: str = "", detail: str = "", gaya_kartu: str = ""):
    st.markdown(
        f'<div class="kpi {gaya_kartu}"><div class="l">{label}</div>'
        f'<div class="v">{nilai}<small> {satuan}</small></div><div class="d">{detail}</div></div>',
        unsafe_allow_html=True)


# ---------- state parameter ----------

def _is_int(k: str) -> bool:
    p = model.PARAM[k]
    return float(p.langkah).is_integer() and float(p.nilai).is_integer()


def _nilai_awal(k: str):
    v = model.DEFAULT[k]
    return int(v) if _is_int(k) else float(v)


def init_state():
    for k in model.DEFAULT:
        st.session_state.setdefault(k, _nilai_awal(k))
    st.session_state.setdefault("skenario", "larangan")
    st.session_state.setdefault("override_gerai", None)
    if "pending_total" in st.session_state:  # dari unggah data gerai
        st.session_state["total_gerai"] = int(min(max(st.session_state.pop("pending_total"), 50), 1500))


def params() -> dict:
    return {k: st.session_state[k] for k in model.DEFAULT}


def reset_params():
    for k in model.DEFAULT:
        st.session_state[k] = _nilai_awal(k)
    st.session_state["skenario"] = "larangan"


def _slider(k: str):
    p = model.PARAM[k]
    cast = int if _is_int(k) else float
    st.slider(f"{p.label} ({p.satuan})", cast(p.minimum), cast(p.maksimum), step=cast(p.langkah),
              key=k, help=p.keterangan)


def panel_parameter():
    st.markdown('<div class="serif" style="font-size:20px;margin-bottom:4px">Skenario kebijakan</div>',
                unsafe_allow_html=True)
    st.radio("Skenario", list(model.SKENARIO), format_func=model.SKENARIO.get, key="skenario",
             label_visibility="collapsed")
    st.markdown('<div class="serif" style="font-size:20px;margin:10px 0 4px">Parameter</div>',
                unsafe_allow_html=True)
    for k in ("total_gerai", "transaksi", "kantong", "berat", "kepatuhan"):
        _slider(k)
    st.markdown(f'<div style="font-weight:700;color:#7A4B0E;margin-top:6px">Efek samping kebijakan</div>',
                unsafe_allow_html=True)
    for k in ("substitusi", "perpindahan"):
        _slider(k)
    with st.expander("Parameter skenario & proyeksi"):
        for k in ("faktor_berbayar", "faktor_bertahap", "pertumbuhan"):
            _slider(k)
    st.button("Kembalikan nilai awal", on_click=reset_params, width="stretch")
    st.markdown('<div class="catatan" style="margin-top:10px">Nilai awal adalah contoh untuk ilustrasi dan '
                'akan dikalibrasi dengan data Pemkab Sumedang serta masukan SatuBumi.</div>',
                unsafe_allow_html=True)
