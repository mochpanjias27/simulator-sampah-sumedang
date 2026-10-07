"""Model simulasi dampak kebijakan kantong plastik belanja di minimarket.

Modul ini sengaja dipisahkan dari tampilan (Streamlit) agar bisa diuji,
ditelaah, dan dikutip dalam ringkasan kebijakan.

Satuan: berat dalam ton per tahun, kecuali disebut lain.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

SKENARIO = {
    "saat_ini": "Kondisi saat ini",
    "larangan": "Larangan penuh",
    "berbayar": "Kantong berbayar",
    "bertahap": "Penerapan bertahap",
}

HARI_PER_TAHUN = 365
TAHUN_DASAR = 2026


@dataclass(frozen=True)
class Parameter:
    kunci: str
    label: str
    nilai: float          # nilai awal (titik tengah)
    minimum: float        # batas slider
    maksimum: float
    langkah: float
    satuan: str
    mc_min: float         # rentang ketidakpastian untuk Monte Carlo
    mc_maks: float
    keterangan: str
    sumber: str = "Asumsi awal, perlu divalidasi bersama SatuBumi dan data Pemkab"


PARAMETER: list[Parameter] = [
    Parameter("total_gerai", "Jumlah minimarket/swalayan", 350, 50, 1500, 10, "gerai",
              300, 420, "Total gerai di Kabupaten Sumedang; dibagi ke kecamatan menurut data/kecamatan.csv"),
    Parameter("transaksi", "Transaksi per gerai per hari", 300, 50, 800, 10, "transaksi",
              200, 400, "Rata-rata transaksi harian satu gerai"),
    Parameter("kantong", "Kantong per transaksi", 1.2, 0.5, 3.0, 0.1, "lembar",
              0.9, 1.6, "Rata-rata kantong plastik yang diberikan per transaksi"),
    Parameter("berat", "Berat per kantong", 5.0, 2.0, 12.0, 0.5, "gram",
              3.5, 7.0, "Berat rata-rata satu kantong belanja"),
    Parameter("kepatuhan", "Tingkat kepatuhan gerai", 80, 0, 100, 5, "%",
              60, 95, "Persentase pengurangan pemberian kantong di gerai yang diatur"),
    Parameter("substitusi", "Beralih membeli kantong sampah", 30, 0, 80, 5, "%",
              15, 50, "Bagian pengurangan yang tergantikan pembelian kantong sampah (dulu kresek dipakai ulang)"),
    Parameter("perpindahan", "Pindah ke warung/pasar", 15, 0, 60, 5, "%",
              5, 30, "Bagian pengurangan yang berpindah ke warung, pasar, atau kecamatan yang belum diatur"),
    Parameter("faktor_berbayar", "Efek kantong berbayar", 55, 10, 100, 5, "% dari larangan",
              40, 70, "Efektivitas kantong berbayar relatif terhadap larangan penuh"),
    Parameter("faktor_bertahap", "Efek tahun pertama (bertahap)", 50, 10, 100, 5, "% dari larangan",
              40, 60, "Efektivitas penerapan bertahap pada tahun pertama; naik ke 75% lalu 100%"),
    Parameter("pertumbuhan", "Pertumbuhan jumlah gerai", 3, 0, 15, 0.5, "% per tahun",
              1, 6, "Laju penambahan gerai per tahun untuk proyeksi"),
]

PARAM = {p.kunci: p for p in PARAMETER}
DEFAULT = {p.kunci: p.nilai for p in PARAMETER}
PERSEN = {"kepatuhan", "substitusi", "perpindahan", "faktor_berbayar", "faktor_bertahap", "pertumbuhan"}


def _frac(p: dict, k: str):
    return p[k] / 100 if k in PERSEN else p[k]


def ton_per_gerai(p: dict):
    """Timbulan kantong plastik dari satu gerai, ton per tahun."""
    return p["transaksi"] * p["kantong"] * p["berat"] * HARI_PER_TAHUN / 1e6


def laju_pengurangan(skenario: str, p: dict, tahun_ke: int = 0):
    """Bagian timbulan kantong yang tidak lagi diberikan (dampak kotor).

    tahun_ke: 0 = tahun pertama kebijakan berlaku. Hanya berpengaruh untuk skenario bertahap.
    """
    k = _frac(p, "kepatuhan")
    if skenario == "larangan":
        return k
    if skenario == "berbayar":
        return _frac(p, "faktor_berbayar") * k
    if skenario == "bertahap":
        f1 = _frac(p, "faktor_bertahap")
        ramp = [f1, (f1 + 1) / 2]
        return k * (ramp[tahun_ke] if tahun_ke < len(ramp) else 1.0)
    return 0 * k


def pecah_dampak(timbulan, laju, p: dict) -> dict:
    """Pecah dampak kotor menjadi bersih, substitusi, dan perpindahan."""
    kotor = timbulan * laju
    sub = kotor * _frac(p, "substitusi")
    pindah = kotor * _frac(p, "perpindahan")
    bersih = np.maximum(kotor - sub - pindah, 0)
    return {"timbulan": timbulan, "kotor": kotor, "substitusi": sub,
            "perpindahan": pindah, "bersih": bersih, "tetap": timbulan - kotor}


def ringkasan(p: dict, skenario: str) -> dict:
    """Dampak tahunan bila kebijakan berlaku di seluruh Kabupaten Sumedang."""
    timbulan = p["total_gerai"] * ton_per_gerai(p)
    hasil = pecah_dampak(timbulan, laju_pengurangan(skenario, p), p)
    hasil["lembar_juta"] = p["total_gerai"] * p["transaksi"] * p["kantong"] * HARI_PER_TAHUN / 1e6
    hasil["lembar_dicegah_juta"] = hasil["bersih"] * 1e6 / p["berat"] / 1e6 if p["berat"] else 0
    hasil["efektivitas"] = hasil["bersih"] / timbulan if timbulan else 0
    return hasil


def spasial(kec: pd.DataFrame, diterapkan: set[str], p: dict, skenario: str) -> pd.DataFrame:
    """Dampak per kecamatan, termasuk limpahan ke tetangga yang belum menerapkan.

    kec: kolom id, nama, gerai (sudah diskalakan), tetangga (list id).
    Perpindahan dari kecamatan yang menerapkan dibagi rata ke tetangga yang belum
    menerapkan. Bila semua tetangga sudah menerapkan, perpindahan tetap dihitung
    sebagai tidak berkurang (pindah ke warung/pasar di kecamatan itu sendiri).
    """
    tpg = ton_per_gerai(p)
    laju = laju_pengurangan(skenario, p)
    df = kec[["id", "nama", "gerai", "tetangga"]].copy()
    df["timbulan"] = df["gerai"] * tpg
    df["diterapkan"] = df["id"].isin(diterapkan)
    for c in ("kotor", "substitusi", "perpindahan", "bersih", "limpahan_masuk", "limpahan_keluar"):
        df[c] = 0.0
    idx = {i: n for n, i in enumerate(df["id"])}
    for n, row in df.iterrows():
        if not row["diterapkan"]:
            continue
        h = pecah_dampak(row["timbulan"], laju, p)
        for c in ("kotor", "substitusi", "perpindahan", "bersih"):
            df.at[n, c] = h[c]
        target = [t for t in row["tetangga"] if t in idx and t not in diterapkan]
        if target and h["perpindahan"] > 0:
            df.at[n, "limpahan_keluar"] = h["perpindahan"]
            for t in target:
                df.at[idx[t], "limpahan_masuk"] += h["perpindahan"] / len(target)
    df["status"] = np.where(df["diterapkan"], "Diterapkan",
                            np.where(df["limpahan_masuk"] > 0, "Menerima limpahan", "Belum diterapkan"))
    return df


def proyeksi(p: dict, skenario: str, tahun_mulai: int = TAHUN_DASAR, tahun_akhir: int = 2029) -> pd.DataFrame:
    """Proyeksi tahunan (stok-alir sederhana) dengan pertumbuhan gerai."""
    rows = []
    for th in range(TAHUN_DASAR, tahun_akhir + 1):
        q = dict(p)
        q["total_gerai"] = p["total_gerai"] * (1 + _frac(p, "pertumbuhan")) ** (th - TAHUN_DASAR)
        timbulan = q["total_gerai"] * ton_per_gerai(q)
        laju = laju_pengurangan(skenario, q, th - tahun_mulai) if th >= tahun_mulai else 0.0
        h = pecah_dampak(timbulan, laju, q)
        rows.append({"tahun": th, "gerai": q["total_gerai"], **{k: float(v) for k, v in h.items()}})
    return pd.DataFrame(rows)


def sampel_parameter(p: dict, n: int, seed: int = 42) -> dict:
    """Sampel parameter dari distribusi segitiga (min, nilai saat ini, maks)."""
    rng = np.random.default_rng(seed)
    out = {}
    for k, v in p.items():
        par = PARAM.get(k)
        if par is None or k == "total_gerai":
            out[k] = np.full(n, float(v))
            continue
        lo, hi = min(par.mc_min, v), max(par.mc_maks, v)
        out[k] = np.full(n, float(v)) if hi <= lo else rng.triangular(lo, v, hi, n)
    return out


def monte_carlo(p: dict, skenario: str, n: int = 2000, tahun_mulai: int = TAHUN_DASAR,
                tahun_akhir: int = 2029, seed: int = 42) -> pd.DataFrame:
    """Rentang ketidakpastian pengurangan bersih per tahun (P10, P50, P90)."""
    s = sampel_parameter(p, n, seed)
    rows = []
    for th in range(TAHUN_DASAR, tahun_akhir + 1):
        gerai = s["total_gerai"] * (1 + s["pertumbuhan"] / 100) ** (th - TAHUN_DASAR)
        timbulan = gerai * ton_per_gerai(s)
        laju = laju_pengurangan(skenario, s, th - tahun_mulai) if th >= tahun_mulai else 0 * timbulan
        bersih = pecah_dampak(timbulan, laju, s)["bersih"]
        rows.append({"tahun": th, "p10": np.percentile(bersih, 10),
                     "p50": np.percentile(bersih, 50), "p90": np.percentile(bersih, 90)})
    return pd.DataFrame(rows)
