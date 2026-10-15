/* Model simulasi dampak kebijakan kantong plastik belanja di minimarket.
 *
 * Terjemahan langsung dari src/model.py (versi Python tetap menjadi acuan dan
 * diuji di tests/). Kesetaraan keduanya diuji di tests/test_model_web.py.
 * Satuan: ton per tahun, kecuali disebut lain.
 *
 * Dipakai di peramban (window.SimModel) dan di Node (module.exports).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory;
  else root.SimModel = factory(root.SIM_DATA);
}(typeof self !== 'undefined' ? self : this, function (D) {
  'use strict';

  const HARI = D.hari_per_tahun;
  const TAHUN_DASAR = D.tahun_dasar;
  const PERSEN = new Set(D.persen);
  const PARAMETER = D.parameter;
  const PARAM = Object.fromEntries(PARAMETER.map(p => [p.kunci, p]));
  const DEFAULT = Object.fromEntries(PARAMETER.map(p => [p.kunci, p.nilai]));
  const SKENARIO = D.skenario;

  const frac = (p, k) => (PERSEN.has(k) ? p[k] / 100 : p[k]);

  /** Timbulan kantong plastik dari satu gerai, ton per tahun. */
  function tonPerGerai(p) {
    return p.transaksi * p.kantong * p.berat * HARI / 1e6;
  }

  /** Bagian timbulan yang tidak lagi diberikan (dampak kotor). tahunKe: 0 = tahun pertama. */
  function lajuPengurangan(skenario, p, tahunKe = 0) {
    const k = frac(p, 'kepatuhan');
    if (skenario === 'larangan') return k;
    if (skenario === 'berbayar') return frac(p, 'faktor_berbayar') * k;
    if (skenario === 'bertahap') {
      const f1 = frac(p, 'faktor_bertahap');
      const ramp = [f1, (f1 + 1) / 2];
      return k * (tahunKe < ramp.length ? ramp[tahunKe] : 1.0);
    }
    return 0;
  }

  /** Pecah dampak kotor menjadi bersih, substitusi, dan perpindahan. */
  function pecahDampak(timbulan, laju, p) {
    const kotor = timbulan * laju;
    const substitusi = kotor * frac(p, 'substitusi');
    const perpindahan = kotor * frac(p, 'perpindahan');
    const bersih = Math.max(kotor - substitusi - perpindahan, 0);
    return { timbulan, kotor, substitusi, perpindahan, bersih, tetap: timbulan - kotor };
  }

  /** Dampak tahunan bila kebijakan berlaku di seluruh Kabupaten Sumedang. */
  function ringkasan(p, skenario) {
    const timbulan = p.total_gerai * tonPerGerai(p);
    const h = pecahDampak(timbulan, lajuPengurangan(skenario, p), p);
    h.lembar_juta = p.total_gerai * p.transaksi * p.kantong * HARI / 1e6;
    h.lembar_dicegah_juta = p.berat ? h.bersih / p.berat : 0;
    h.efektivitas = timbulan ? h.bersih / timbulan : 0;
    return h;
  }

  /** Tabel kecamatan dengan jumlah gerai diskalakan ke total. override: {id: jumlah} dari data unggahan. */
  function kecamatan(totalGerai, override) {
    const rows = D.kecamatan.map(k => ({
      id: k.id, nama: k.nama, tetangga: k.tetangga,
      gerai_asumsi: override ? (override[k.id] || 0) : k.gerai_asumsi,
    }));
    const dasar = rows.reduce((s, r) => s + r.gerai_asumsi, 0) || 1;
    rows.forEach(r => { r.gerai = r.gerai_asumsi * totalGerai / dasar; });
    return rows;
  }

  /** Dampak per kecamatan, termasuk limpahan ke tetangga yang belum menerapkan. */
  function spasial(kec, diterapkan, p, skenario) {
    const tpg = tonPerGerai(p);
    const laju = lajuPengurangan(skenario, p);
    const df = kec.map(r => ({
      id: r.id, nama: r.nama, gerai: r.gerai, tetangga: r.tetangga,
      timbulan: r.gerai * tpg, diterapkan: diterapkan.has(r.id),
      kotor: 0, substitusi: 0, perpindahan: 0, bersih: 0, limpahan_masuk: 0, limpahan_keluar: 0,
    }));
    const idx = Object.fromEntries(df.map((r, i) => [r.id, i]));
    df.forEach(r => {
      if (!r.diterapkan) return;
      const h = pecahDampak(r.timbulan, laju, p);
      r.kotor = h.kotor; r.substitusi = h.substitusi; r.perpindahan = h.perpindahan; r.bersih = h.bersih;
      const target = r.tetangga.filter(t => t in idx && !diterapkan.has(t));
      if (target.length && h.perpindahan > 0) {
        r.limpahan_keluar = h.perpindahan;
        target.forEach(t => { df[idx[t]].limpahan_masuk += h.perpindahan / target.length; });
      }
    });
    df.forEach(r => {
      r.status = r.diterapkan ? 'Diterapkan' : (r.limpahan_masuk > 0 ? 'Menerima limpahan' : 'Belum diterapkan');
    });
    return df;
  }

  /** Proyeksi tahunan (stok-alir sederhana) dengan pertumbuhan gerai. */
  function proyeksi(p, skenario, tahunMulai = TAHUN_DASAR, tahunAkhir = 2029) {
    const rows = [];
    for (let th = TAHUN_DASAR; th <= tahunAkhir; th++) {
      const q = Object.assign({}, p);
      q.total_gerai = p.total_gerai * Math.pow(1 + frac(p, 'pertumbuhan'), th - TAHUN_DASAR);
      const timbulan = q.total_gerai * tonPerGerai(q);
      const laju = th >= tahunMulai ? lajuPengurangan(skenario, q, th - tahunMulai) : 0;
      rows.push(Object.assign({ tahun: th, gerai: q.total_gerai }, pecahDampak(timbulan, laju, q)));
    }
    return rows;
  }

  // ---------- Monte Carlo ----------

  /** Pembangkit acak mulberry32: hasil sama untuk seed yang sama. */
  function rng(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function segitiga(u, a, c, b) {
    const fc = (c - a) / (b - a);
    return u < fc ? a + Math.sqrt(u * (b - a) * (c - a)) : b - Math.sqrt((1 - u) * (b - a) * (b - c));
  }

  /** Sampel parameter dari distribusi segitiga (min, nilai saat ini, maks). */
  function sampelParameter(p, n, seed = 42) {
    const r = rng(seed);
    const out = [];
    for (let i = 0; i < n; i++) {
      const s = {};
      for (const k in p) {
        const par = PARAM[k];
        const v = p[k];
        if (!par || k === 'total_gerai') { s[k] = v; continue; }
        const lo = Math.min(par.mc_min, v), hi = Math.max(par.mc_maks, v);
        s[k] = hi <= lo ? v : segitiga(r(), lo, v, hi);
      }
      out.push(s);
    }
    return out;
  }

  /** Persentil dengan interpolasi linear (sama dengan numpy.percentile bawaan). */
  function persentil(arr, q) {
    const a = Float64Array.from(arr).sort();
    const pos = (a.length - 1) * q / 100;
    const lo = Math.floor(pos), hi = Math.ceil(pos);
    return a[lo] + (a[hi] - a[lo]) * (pos - lo);
  }

  /** Rentang ketidakpastian pengurangan bersih per tahun (P10, P50, P90). */
  function monteCarlo(p, skenario, n = 2000, tahunMulai = TAHUN_DASAR, tahunAkhir = 2029, seed = 42) {
    const sampel = sampelParameter(p, n, seed);
    const rows = [];
    for (let th = TAHUN_DASAR; th <= tahunAkhir; th++) {
      const bersih = sampel.map(s => {
        const gerai = s.total_gerai * Math.pow(1 + s.pertumbuhan / 100, th - TAHUN_DASAR);
        const timbulan = gerai * tonPerGerai(s);
        const laju = th >= tahunMulai ? lajuPengurangan(skenario, s, th - tahunMulai) : 0;
        return pecahDampak(timbulan, laju, s).bersih;
      });
      rows.push({ tahun: th, p10: persentil(bersih, 10), p50: persentil(bersih, 50), p90: persentil(bersih, 90) });
    }
    return rows;
  }

  // ---------- geometri (pengganti shapely di versi web) ----------

  const POLY = Object.fromEntries(D.geojson.features.map(f => [f.properties.id, f.geometry.coordinates]));

  function dalamCincin(x, y, ring) {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i], [xj, yj] = ring[j];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }

  function dalamPoligon(x, y, rings) {
    if (!dalamCincin(x, y, rings[0])) return false;
    for (let h = 1; h < rings.length; h++) if (dalamCincin(x, y, rings[h])) return false;
    return true;
  }

  function jarakKeTepi(x, y, rings) {
    let best = Infinity;
    rings.forEach(ring => {
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const [x1, y1] = ring[j], [x2, y2] = ring[i];
        const dx = x2 - x1, dy = y2 - y1;
        const L = dx * dx + dy * dy;
        const t = L ? Math.max(0, Math.min(1, ((x - x1) * dx + (y - y1) * dy) / L)) : 0;
        const ex = x1 + t * dx - x, ey = y1 + t * dy - y;
        best = Math.min(best, ex * ex + ey * ey);
      }
    });
    return Math.sqrt(best);
  }

  /** Titik gerai ilustratif, disebar acak di dalam kecamatan (BUKAN lokasi sebenarnya). */
  function titikIlustrasi(kec, seed = 7) {
    const r = rng(seed);
    const out = [];
    kec.forEach(k => {
      const rings = POLY[k.id];
      if (!rings) return;
      const xs = rings[0].map(c => c[0]), ys = rings[0].map(c => c[1]);
      const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
      const target = Math.round(k.gerai);
      let got = 0, tries = 0;
      while (got < target && tries < 20000) {
        tries++;
        const x = x0 + r() * (x1 - x0), y = y0 + r() * (y1 - y0);
        if (dalamPoligon(x, y, rings) && (tries > 5000 || jarakKeTepi(x, y, rings) > 0.002)) {
          out.push({ kecamatan: k.id, lat: y, lon: x });
          got++;
        }
      }
    });
    return out;
  }

  /** Tentukan kecamatan tiap titik {lat, lon}; null bila di luar Kabupaten Sumedang. */
  function tetapkanKecamatan(titik) {
    const ids = Object.keys(POLY);
    return titik.map(t => Object.assign({}, t, {
      kecamatan: ids.find(id => dalamPoligon(t.lon, t.lat, POLY[id])) || null,
    }));
  }

  return {
    TAHUN_DASAR, PARAMETER, PARAM, DEFAULT, SKENARIO, PERSEN,
    tonPerGerai, lajuPengurangan, pecahDampak, ringkasan, kecamatan, spasial, proyeksi,
    sampelParameter, monteCarlo, persentil, titikIlustrasi, tetapkanKecamatan, dalamPoligon,
  };
}));
