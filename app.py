"""Simulator Dampak Kebijakan Sampah Kantong Plastik – Kabupaten Sumedang.

Jalankan:  streamlit run app.py
"""
import streamlit as st

from src import ui

st.set_page_config(page_title="Simulator Kebijakan Sampah Sumedang", page_icon="♻️",
                   layout="wide", initial_sidebar_state="expanded")
ui.gaya()
ui.init_state()

halaman = st.navigation([
    st.Page("views/ringkasan.py", title="Ringkasan Skenario", icon=":material/dashboard:", default=True),
    st.Page("views/peta.py", title="Peta Wilayah", icon=":material/map:"),
    st.Page("views/proyeksi.py", title="Proyeksi 2026–2029", icon=":material/show_chart:"),
    st.Page("views/asumsi.py", title="Asumsi & Parameter", icon=":material/tune:"),
])

with st.sidebar:
    ui.panel_parameter()

halaman.run()
