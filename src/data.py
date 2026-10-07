"""Pemuatan data wilayah dan gerai."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from shapely.geometry import Point, shape

DATA = Path(__file__).resolve().parent.parent / "data"


@st.cache_data
def geojson() -> dict:
    return json.loads((DATA / "kecamatan_sumedang.geojson").read_text(encoding="utf-8"))


@st.cache_resource
def bentuk() -> dict:
    """Geometri shapely per id kecamatan."""
    return {f["properties"]["id"]: shape(f["geometry"]) for f in geojson()["features"]}


@st.cache_data
def tetangga() -> dict[str, list[str]]:
    """Kecamatan yang bersinggungan (toleransi ±400 m untuk celah batas)."""
    g = bentuk()
    return {a: [b for b, gb in g.items() if b != a and ga.buffer(0.004).intersects(gb)]
            for a, ga in g.items()}


@st.cache_data
def kecamatan_dasar() -> pd.DataFrame:
    return pd.read_csv(DATA / "kecamatan.csv")


def kecamatan(total_gerai: float, jumlah_override: dict | None = None) -> pd.DataFrame:
    """Tabel kecamatan dengan jumlah gerai yang diskalakan ke total."""
    df = kecamatan_dasar().copy()
    if jumlah_override:
        df["gerai_asumsi"] = df["id"].map(jumlah_override).fillna(0)
    dasar = df["gerai_asumsi"].sum() or 1
    df["gerai"] = df["gerai_asumsi"] * total_gerai / dasar
    nb = tetangga()
    df["tetangga"] = df["id"].map(lambda i: nb.get(i, []))
    return df


@st.cache_data
def titik_ilustrasi(jumlah: tuple, seed: int = 7) -> pd.DataFrame:
    """Titik gerai ilustratif yang disebar acak di dalam batas kecamatan.

    jumlah: tuple (id, n). Posisi BUKAN lokasi gerai sebenarnya.
    """
    rng = np.random.default_rng(seed)
    g = bentuk()
    rows = []
    for kid, n in jumlah:
        poly = g[kid]
        inner = poly.buffer(-0.002)
        inner = poly if inner.is_empty else inner
        x0, y0, x1, y1 = inner.bounds
        got, tries = 0, 0
        while got < int(round(n)) and tries < 20000:
            tries += 1
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
            if inner.contains(Point(x, y)):
                rows.append({"kecamatan": kid, "lat": y, "lon": x})
                got += 1
    return pd.DataFrame(rows, columns=["kecamatan", "lat", "lon"])


def tetapkan_kecamatan(titik: pd.DataFrame) -> pd.DataFrame:
    """Tentukan kecamatan tiap titik gerai (lat, lon) dengan uji titik-dalam-poligon."""
    g = bentuk()
    out = titik.copy()
    out["kecamatan"] = [next((k for k, poly in g.items() if poly.contains(Point(lon, lat))), None)
                        for lat, lon in zip(out["lat"], out["lon"])]
    return out
