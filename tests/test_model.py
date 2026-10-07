import pandas as pd
import pytest

from src import model

P = dict(model.DEFAULT)


def test_timbulan_per_gerai():
    # 300 transaksi x 1,2 kantong x 5 g x 365 hari = 0,657 ton
    assert model.ton_per_gerai(P) == pytest.approx(0.657)


def test_saat_ini_tanpa_dampak():
    r = model.ringkasan(P, "saat_ini")
    assert r["bersih"] == 0 and r["kotor"] == 0


def test_urutan_skenario():
    b = {k: model.ringkasan(P, k)["bersih"] for k in model.SKENARIO}
    assert b["larangan"] > b["berbayar"] > 0 and b["larangan"] > b["bertahap"] > 0


def test_neraca_dampak():
    r = model.ringkasan(P, "larangan")
    assert r["bersih"] + r["substitusi"] + r["perpindahan"] == pytest.approx(r["kotor"])
    assert r["kotor"] + r["tetap"] == pytest.approx(r["timbulan"])


def test_limpahan_kekal():
    kec = pd.DataFrame({"id": ["a", "b", "c"], "nama": list("ABC"), "gerai": [10, 10, 10],
                        "tetangga": [["b"], ["a", "c"], ["b"]]})
    h = model.spasial(kec, {"a", "c"}, P, "larangan")
    assert h["limpahan_masuk"].sum() == pytest.approx(h["limpahan_keluar"].sum())
    assert h.set_index("id").loc["b", "status"] == "Menerima limpahan"


def test_bertahap_naik():
    pr = model.proyeksi(P, "bertahap", tahun_mulai=2026)
    laju = (pr["kotor"] / pr["timbulan"]).tolist()
    assert laju[0] < laju[1] < laju[2] == pytest.approx(laju[3])


def test_monte_carlo_terurut():
    mc = model.monte_carlo(P, "larangan", n=500)
    assert (mc["p10"] <= mc["p50"]).all() and (mc["p50"] <= mc["p90"]).all()
