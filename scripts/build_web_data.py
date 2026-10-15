"""Bangkitkan web/js/data.js dari data/ dan src/model.py.

Versi web (folder web/) memakai berkas ini sebagai satu-satunya sumber data:
parameter model, skenario, tabel kecamatan, daftar tetangga, dan batas kecamatan.
Jalankan ulang setiap kali data/ atau daftar PARAMETER di src/model.py diubah:

    python scripts/build_web_data.py
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import model  # noqa: E402  (model.py tidak bergantung pada Streamlit)

DATA = ROOT / "data"
OUT = ROOT / "web" / "js" / "data.js"


def tetangga(gj: dict) -> dict[str, list[str]]:
    """Sama dengan src/data.py: kecamatan bersinggungan, toleransi ±400 m."""
    g = {f["properties"]["id"]: shape(f["geometry"]) for f in gj["features"]}
    return {a: [b for b, gb in g.items() if b != a and ga.buffer(0.004).intersects(gb)]
            for a, ga in g.items()}


def bulatkan(obj, d=5):
    """Kurangi presisi koordinat agar berkas kecil (5 desimal ≈ 1 m)."""
    if isinstance(obj, float):
        return round(obj, d)
    if isinstance(obj, list):
        return [bulatkan(x, d) for x in obj]
    if isinstance(obj, dict):
        return {k: bulatkan(v, d) for k, v in obj.items()}
    return obj


def main():
    gj = json.loads((DATA / "kecamatan_sumedang.geojson").read_text(encoding="utf-8"))
    kec = pd.read_csv(DATA / "kecamatan.csv")
    nb = tetangga(gj)
    ids_geo = {f["properties"]["id"] for f in gj["features"]}
    hilang = set(kec["id"]) ^ ids_geo
    if hilang:
        raise SystemExit(f"id kecamatan tidak cocok antara CSV dan GeoJSON: {sorted(hilang)}")

    out = {
        "tahun_dasar": model.TAHUN_DASAR,
        "hari_per_tahun": model.HARI_PER_TAHUN,
        "persen": sorted(model.PERSEN),
        "skenario": model.SKENARIO,
        "parameter": [asdict(p) for p in model.PARAMETER],
        "kecamatan": [{"id": r.id, "nama": r.nama, "gerai_asumsi": float(r.gerai_asumsi),
                       "tetangga": nb.get(r.id, [])} for r in kec.itertuples()],
        "geojson": bulatkan(gj),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("// DIBANGKITKAN OTOMATIS oleh scripts/build_web_data.py — jangan diedit manual.\n"
                   "window.SIM_DATA = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n",
                   encoding="utf-8")
    print(f"Tertulis {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.0f} KB), "
          f"{len(out['kecamatan'])} kecamatan, {len(out['parameter'])} parameter")


if __name__ == "__main__":
    main()
