"""Uji kesetaraan model versi web (web/js/model.js) dengan model Python (src/model.py).

Butuh Node.js; dilewati bila tidak tersedia. Data kecamatan dan tetangga diambil dari
web/js/data.js agar sama persis dengan yang dipakai peramban.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from src import model

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js tidak tersedia")

KASUS = [
    {"p": dict(model.DEFAULT), "sk": "larangan", "terapan": ["jatinangor", "cimanggung", "tanjungsari", "rancakalong"], "mulai": 2027},
    {"p": dict(model.DEFAULT, kepatuhan=65, substitusi=40, perpindahan=25), "sk": "berbayar", "terapan": ["jatinangor"], "mulai": 2026},
    {"p": dict(model.DEFAULT, total_gerai=900, pertumbuhan=6.5), "sk": "bertahap", "terapan": [], "mulai": 2026},
    {"p": dict(model.DEFAULT), "sk": "saat_ini", "terapan": ["jatinangor"], "mulai": 2028},
]


def _data_web():
    teks = (ROOT / "web/js/data.js").read_text(encoding="utf-8")
    return json.loads(re.search(r"window\.SIM_DATA = (\{.*\});", teks, re.S).group(1))


@pytest.fixture(scope="module")
def hasil_js():
    out = subprocess.run(["node", str(ROOT / "tests/web_model_runner.js"), json.dumps(KASUS)],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def _kec(total):
    d = _data_web()["kecamatan"]
    df = pd.DataFrame(d)
    df["gerai"] = df["gerai_asumsi"] * total / df["gerai_asumsi"].sum()
    return df


def test_data_web_sesuai_parameter():
    d = _data_web()
    assert [p["kunci"] for p in d["parameter"]] == [p.kunci for p in model.PARAMETER]
    assert {p["kunci"]: p["nilai"] for p in d["parameter"]} == model.DEFAULT


@pytest.mark.parametrize("i", range(len(KASUS)))
def test_ringkasan_sama(hasil_js, i):
    k = KASUS[i]
    py = model.ringkasan(k["p"], k["sk"])
    for kunci in ("timbulan", "kotor", "substitusi", "perpindahan", "bersih", "tetap", "efektivitas", "lembar_juta"):
        assert hasil_js[i]["ringkasan"][kunci] == pytest.approx(float(py[kunci]), rel=1e-9, abs=1e-12)


@pytest.mark.parametrize("i", range(len(KASUS)))
def test_spasial_sama(hasil_js, i):
    k = KASUS[i]
    py = model.spasial(_kec(k["p"]["total_gerai"]), set(k["terapan"]), k["p"], k["sk"]).set_index("id")
    for r in hasil_js[i]["spasial"]:
        q = py.loc[r["id"]]
        assert r["status"] == q["status"]
        for kunci in ("timbulan", "bersih", "limpahan_masuk", "limpahan_keluar"):
            assert r[kunci] == pytest.approx(float(q[kunci]), rel=1e-9, abs=1e-12)


@pytest.mark.parametrize("i", range(len(KASUS)))
def test_proyeksi_sama(hasil_js, i):
    k = KASUS[i]
    py = model.proyeksi(k["p"], k["sk"], tahun_mulai=k["mulai"])
    for r, (_, q) in zip(hasil_js[i]["proyeksi"], py.iterrows()):
        for kunci in ("gerai", "timbulan", "kotor", "bersih"):
            assert r[kunci] == pytest.approx(float(q[kunci]), rel=1e-9, abs=1e-12)


@pytest.mark.parametrize("i", range(len(KASUS)))
def test_monte_carlo_setara(hasil_js, i):
    """Pembangkit acak berbeda, jadi persentil hanya dibandingkan secara statistik (±3%)."""
    k = KASUS[i]
    py = model.monte_carlo(k["p"], k["sk"], n=4000, tahun_mulai=k["mulai"])
    for r, (_, q) in zip(hasil_js[i]["mc"], py.iterrows()):
        assert r["p10"] <= r["p50"] <= r["p90"]
        for kunci in ("p10", "p50", "p90"):
            assert r[kunci] == pytest.approx(float(q[kunci]), rel=0.03, abs=1e-6)
