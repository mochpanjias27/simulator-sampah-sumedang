/* Simulator Kebijakan Sampah — Kabupaten Sumedang (tampilan gaya SITRAS / Command Center) */
(function () {
  'use strict';

  const M = window.SimModel;
  const D = window.SIM_DATA;

  // ------------------------------------------------------------------ util
  const qs = new URLSearchParams(location.search);
  const EMBED = qs.get('embed') === '1';
  const KUNCI_SIMPAN = 'simsampah_v1';
  const store = {
    get: (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* abaikan */ } },
  };
  const nf = (v, d = 1) => (v == null || isNaN(v) ? '–' : Number(v).toLocaleString('id-ID', { minimumFractionDigits: d, maximumFractionDigits: d }));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const sum = (a, f) => a.reduce((s, x) => s + f(x), 0);
  function toast(msg) {
    const el = $('<div class="toast-x" role="status"></div>').text(msg).appendTo('body');
    setTimeout(() => el.fadeOut(300, () => el.remove()), 3600);
  }
  function unduhCSV(nama, header, rows) {
    const cel = (v) => { const s = typeof v === 'number' ? String(Math.round(v * 100) / 100) : String(v == null ? '' : v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
    const teks = [header, ...rows].map((r) => r.map(cel).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob(['﻿' + teks], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a'); a.href = url; a.download = nama; document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 500);
  }

  // warna (status selalu disertai label teks)
  const C = {
    ungu: '#7e37d8', unguTua: '#5a1eb0', unguGelap: '#3b1a78', unguSedang: '#a57ae6', unguMuda: '#d9c6f5', unguPudar: '#cdb8ef',
    pink: '#fe5a8a', amber: '#e8a33d', limpahan: '#f6c66e', abu: '#e1e3eb', tinta: '#2b2b3a', redup: '#8a94a6', grid: '#ecedf3',
  };
  const APEX = { fontFamily: 'Work Sans', toolbar: { show: false }, animations: { enabled: true, speed: 250, animateGradually: { enabled: false } } };
  const axisLbl = { style: { colors: C.redup } };

  // ------------------------------------------------------------------ state
  const KEC = D.kecamatan;
  const NAMA = Object.fromEntries(KEC.map((k) => [k.id, k.nama]));
  const SEMUA = KEC.map((k) => k.id);
  const PRESET = {
    'Seluruh Sumedang': SEMUA,
    'Jatinangor & sekitar': ['jatinangor', 'cimanggung', 'tanjungsari', 'rancakalong'],
    'Jatinangor saja': ['jatinangor'],
    Kosongkan: [],
  };
  const isInt = (k) => Number.isInteger(M.PARAM[k].langkah) && Number.isInteger(M.PARAM[k].nilai);

  const S = {
    p: Object.assign({}, M.DEFAULT),
    sk: 'larangan',
    terapan: new Set(PRESET['Jatinangor & sekitar']),
    fokus: 'jatinangor',
    override: null,      // {id: jumlah} dari CSV gerai
    titikUnggah: null,   // [{lat, lon, kecamatan}]
    page: 'ringkasan',
  };
  try {
    const s = JSON.parse(store.get(KUNCI_SIMPAN) || 'null');
    if (s) {
      Object.keys(M.DEFAULT).forEach((k) => {
        const par = M.PARAM[k];
        if (s.p && typeof s.p[k] === 'number' && s.p[k] >= par.minimum && s.p[k] <= par.maksimum) S.p[k] = s.p[k];
      });
      if (s.sk in M.SKENARIO) S.sk = s.sk;
      if (Array.isArray(s.terapan)) S.terapan = new Set(s.terapan.filter((i) => i in NAMA));
      if (s.fokus in NAMA) S.fokus = s.fokus;
    }
  } catch (e) { /* abaikan state rusak */ }
  let simpanT = null;
  function simpan() {
    clearTimeout(simpanT);
    simpanT = setTimeout(() => store.set(KUNCI_SIMPAN, JSON.stringify({ p: S.p, sk: S.sk, terapan: [...S.terapan], fokus: S.fokus })), 300);
  }

  // ------------------------------------------------------------------ navigasi
  const PAGES = {
    ringkasan: ['Ringkasan Skenario', 'Dampak bila kebijakan berlaku di seluruh Kabupaten Sumedang'],
    peta: ['Peta Wilayah', 'Pilih kecamatan penerapan dan lihat limpahan ke tetangga'],
    proyeksi: ['Proyeksi 2026–2029', 'Pertumbuhan gerai dan rentang ketidakpastian Monte Carlo'],
    asumsi: ['Asumsi & Parameter', 'Angka, rentang, sumber, dan rumus model'],
  };
  function showPage(page) {
    if (!PAGES[page]) page = 'ringkasan';
    S.page = page;
    $('.page').removeClass('active');
    $('#page-' + page).addClass('active');
    $('.sidebar nav a').removeClass('active').filter(`[data-page="${page}"]`).addClass('active');
    $('#embed-tabs .btn').removeClass('active btn-secondary').addClass('btn-outline-secondary')
      .filter(`[data-page="${page}"]`).removeClass('btn-outline-secondary').addClass('active btn-secondary');
    $('#page-title').text(PAGES[page][0]);
    $('#page-crumb').text(PAGES[page][1]);
    document.title = PAGES[page][0] + ' · Simulator Kebijakan Sampah Sumedang';
    tutupLaci();
    render();
    if (page === 'peta' && peta.map) setTimeout(() => peta.map.invalidateSize(), 50);
  }
  function tutupLaci() {
    $('#sidebar, #param-panel').removeClass('open');
    $('#backdrop').removeClass('show');
  }

  // ------------------------------------------------------------------ skenario & parameter
  function buildSkenario() {
    $('#sk-group').html(Object.entries(M.SKENARIO).map(([k, v]) =>
      `<button type="button" class="btn btn-outline-primary" data-sk="${k}" aria-pressed="false">${esc(v)}</button>`).join(''));
    $('#sk-group').on('click', '.btn', function () { S.sk = $(this).data('sk'); simpan(); render(); });
  }
  function syncSkenario() {
    $('#sk-group .btn').each(function () {
      const on = $(this).data('sk') === S.sk;
      $(this).toggleClass('active', on).attr('aria-pressed', on);
    });
  }

  const GRUP = {
    '#prm-utama': ['total_gerai', 'transaksi', 'kantong', 'berat', 'kepatuhan'],
    '#prm-efek': ['substitusi', 'perpindahan'],
    '#prm-lanjut': ['faktor_berbayar', 'faktor_bertahap', 'pertumbuhan'],
  };
  const fmtParam = (k, v) => nf(v, isInt(k) ? 0 : 1);
  function buildParam() {
    Object.entries(GRUP).forEach(([sel, keys]) => {
      $(sel).html(keys.map((k) => {
        const p = M.PARAM[k];
        return `<div class="prm" data-k="${k}">
          <div class="prm-head"><label for="rg-${k}">${esc(p.label)}<span class="info" title="${esc(p.keterangan)}"><i data-feather="info"></i></span></label>
            <span class="prm-val"><span class="v"></span> <small>${esc(p.satuan)}</small></span></div>
          <input type="range" class="custom-range" id="rg-${k}" min="${p.minimum}" max="${p.maksimum}" step="${p.langkah}">
          <div class="prm-ket">${esc(p.keterangan)}</div></div>`;
      }).join(''));
    });
    $('#param-panel').on('input', 'input[type=range]', function () {
      const k = $(this).closest('.prm').data('k');
      S.p[k] = Number(this.value);
      $(this).closest('.prm').find('.v').text(fmtParam(k, S.p[k]));
      simpan(); jadwalRender();
    });
    $('#btn-reset').on('click', () => { S.p = Object.assign({}, M.DEFAULT); S.sk = 'larangan'; syncParam(); simpan(); render(); toast('Parameter dikembalikan ke nilai awal'); });
    $('#btn-ket').on('click', function () {
      const on = !$('.prm').first().hasClass('show-ket');
      $('.prm').toggleClass('show-ket', on);
      $(this).text(on ? 'Sembunyikan keterangan' : 'Tampilkan keterangan');
    });
    $('#btn-lanjut').on('click', function () {
      const buka = $('#prm-lanjut').hasClass('d-none');
      $('#prm-lanjut').toggleClass('d-none', !buka);
      $(this).attr('aria-expanded', buka).html((buka ? '▾' : '▸') + ' Parameter skenario &amp; proyeksi');
    });
  }
  function syncParam() {
    Object.keys(M.DEFAULT).forEach((k) => {
      const el = document.getElementById('rg-' + k);
      if (el) el.value = S.p[k];
      $(`.prm[data-k="${k}"] .v`).text(fmtParam(k, S.p[k]));
    });
  }

  let rafId = null;
  function jadwalRender() {
    if (rafId) return;
    rafId = requestAnimationFrame(() => { rafId = null; render(); });
  }
  function render() {
    syncSkenario();
    ({ ringkasan: renderRingkasan, peta: renderPeta, proyeksi: renderProyeksi, asumsi: renderAsumsi })[S.page]();
  }

  // ------------------------------------------------------------------ RINGKASAN
  let chAlur = null, chSk = null;
  function renderRingkasan() {
    const p = S.p, sk = S.sk;
    const r = M.ringkasan(p, sk);
    const mc = M.monteCarlo(p, sk, 2000, M.TAHUN_DASAR, M.TAHUN_DASAR)[0];
    $('#r-bersih').text(nf(r.bersih));
    $('#r-bersih-sub').text(sk === 'saat_ini' ? 'tidak ada kebijakan' : `rentang P10–P90: ${nf(mc.p10)}–${nf(mc.p90)} ton`);
    $('#r-timbulan').text(nf(r.timbulan));
    $('#r-timbulan-sub').text(`≈ ${nf(r.lembar_juta)} juta lembar per tahun`);
    $('#r-efektif').text(nf(r.efektivitas * 100, 0));
    $('#r-kotor').text(nf(r.kotor));
    $('#r-sub').text(nf(r.substitusi));
    $('#r-pindah').text(nf(r.perpindahan));
    $('#r-lembar').text(nf(r.lembar_dicegah_juta));
    $('#r-alur-sub').text(`Skenario: ${M.SKENARIO[sk]} · seluruh Kabupaten Sumedang`);

    const bagian = [
      ['Pengurangan bersih', r.bersih, C.ungu],
      ['Kantong sampah pengganti', r.substitusi, C.pink],
      ['Pindah ke warung/pasar', r.perpindahan, C.amber],
      ['Tetap beredar', r.tetap, C.abu],
    ];
    $('#leg-alur').html(bagian.map(([n, v, c]) => `<div><span class="sw" style="background:${c}"></span>${n}: <b>${nf(v)} t</b></div>`).join(''));
    const seriesAlur = bagian.map(([n, v]) => ({ name: n, data: [Math.round(v * 10) / 10] }));
    if (!chAlur) {
      chAlur = new ApexCharts(document.querySelector('#ch-alur'), {
        chart: Object.assign({ type: 'bar', stacked: true, height: 110, sparkline: { enabled: false } }, APEX),
        series: seriesAlur,
        plotOptions: { bar: { horizontal: true, barHeight: '70%', borderRadius: 0 } },
        colors: bagian.map((b) => b[2]),
        stroke: { width: 2, colors: ['#fff'] },
        dataLabels: { enabled: false },
        legend: { show: false },
        grid: { borderColor: C.grid, padding: { left: 0, right: 8, top: -16, bottom: -6 } },
        xaxis: { categories: [''], labels: { formatter: (v) => nf(v, 0), style: { colors: C.redup } }, title: { text: 'ton per tahun', style: { color: C.redup, fontWeight: 500 } } },
        yaxis: { labels: { show: false } },
        tooltip: { y: { formatter: (v) => nf(v) + ' ton' } },
      });
      chAlur.render();
    } else chAlur.updateSeries(seriesAlur);

    const ks = Object.keys(M.SKENARIO);
    const nilai = ks.map((k) => Math.round(M.ringkasan(p, k).bersih * 10) / 10);
    const warna = ks.map((k) => (k === sk ? C.ungu : C.unguPudar));
    const optsSk = {
      chart: Object.assign({ type: 'bar', height: 250 }, APEX),
      series: [{ name: 'Pengurangan bersih', data: nilai }],
      plotOptions: { bar: { horizontal: true, distributed: true, barHeight: '62%', borderRadius: 6, dataLabels: { position: 'top' } } },
      colors: warna,
      dataLabels: { enabled: true, formatter: (v) => nf(v) + ' t', offsetX: 34, style: { colors: [C.tinta], fontWeight: 600 } },
      legend: { show: false },
      grid: { borderColor: C.grid },
      xaxis: { categories: ks.map((k) => M.SKENARIO[k] + (k === sk ? ' (dipilih)' : '')), max: Math.max(...nilai, 1) * 1.18, labels: { formatter: (v) => nf(v, 0), style: { colors: C.redup } } },
      yaxis: { labels: { style: { colors: '#59667a', fontSize: '12.5px' }, maxWidth: 200 } },
      tooltip: { y: { formatter: (v) => nf(v) + ' ton/tahun' } },
    };
    if (!chSk) { chSk = new ApexCharts(document.querySelector('#ch-skenario'), optsSk); chSk.render(); }
    else chSk.updateOptions({ series: optsSk.series, colors: warna, xaxis: optsSk.xaxis }, false, false);
  }

  // ------------------------------------------------------------------ PETA
  const peta = { map: null, geo: null, titik: null, renderer: null, cacheTitik: { key: null, data: [] }, hasil: [], H: {} };
  let chTop = null, tbKec = null;

  function warnaKec(q, maks) {
    if (q.diterapkan) {
      const t = q.bersih / maks;
      return t > 0.6 ? C.unguTua : t > 0.25 ? C.unguSedang : C.unguMuda;
    }
    return q.limpahan_masuk > 0 ? C.limpahan : C.abu;
  }
  const badge = (status) => `<span class="st-badge ${status === 'Diterapkan' ? 'st-on' : status === 'Menerima limpahan' ? 'st-limpah' : 'st-off'}">${status}</span>`;

  function initPeta() {
    peta.renderer = L.canvas({ padding: 0.3 });
    peta.map = L.map('map', { zoomControl: false }).fitBounds([[-7.05, 107.74], [-6.57, 108.23]]);
    L.control.zoom({ position: 'bottomright' }).addTo(peta.map);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18, attribution: '&copy; OpenStreetMap contributors' }).addTo(peta.map);
    peta.geo = L.geoJSON(D.geojson, {
      style: () => ({ weight: 1.2, color: '#fff', fillOpacity: 0.72 }),
      onEachFeature: (f, layer) => {
        layer.bindTooltip(() => {
          const q = peta.H[f.properties.id];
          return q ? `<b>${esc(q.nama)}</b><br>${q.status}<br>Gerai: ${nf(q.gerai, 0)}<br>Pengurangan bersih: ${nf(q.bersih)} t/th` +
            (q.limpahan_masuk > 0 ? `<br>Limpahan diterima: ${nf(q.limpahan_masuk)} t/th` : '') : '';
        }, { sticky: true, className: 'kec-tip' });
        layer.on('click', () => { S.fokus = f.properties.id; simpan(); renderPeta(); });
        layer.on('mouseover', () => layer.setStyle({ weight: 3, color: C.unguGelap }));
        layer.on('mouseout', () => gayaPoligon());
      },
    }).addTo(peta.map);
    peta.titik = L.layerGroup().addTo(peta.map);
    peta.fit = () => { peta.map.invalidateSize(); peta.map.fitBounds(peta.geo.getBounds(), { paddingTopLeft: [10, 40], paddingBottomRight: [10, 10] }); };
    setTimeout(peta.fit, 60);

    $('#pt-preset').html(Object.keys(PRESET).map((n) => `<button class="btn btn-outline-primary" data-preset="${esc(n)}">${esc(n)}</button>`).join(''));
    $('#pt-preset').on('click', '.btn', function () { S.terapan = new Set(PRESET[$(this).data('preset')]); simpan(); renderPeta(); });
    $('#pt-cari').on('input', filterDaftar);
    $('#pt-list').on('change', 'input[type=checkbox]', function (e) {
      e.stopPropagation();
      const id = $(this).data('id');
      this.checked ? S.terapan.add(id) : S.terapan.delete(id);
      simpan(); renderPeta();
    });
    $('#pt-list').on('click', '.kec-item', function (e) {
      if ($(e.target).closest('.custom-control').length) return;
      S.fokus = $(this).data('id'); simpan(); renderPeta();
      const lyr = peta.geo.getLayers().find((l) => l.feature.properties.id === S.fokus);
      if (lyr) peta.map.flyToBounds(lyr.getBounds(), { padding: [60, 60], maxZoom: 12, duration: 0.5 });
    });
    $('#pt-detail').on('click', '#pt-toggle', () => {
      S.terapan.has(S.fokus) ? S.terapan.delete(S.fokus) : S.terapan.add(S.fokus);
      simpan(); renderPeta();
    });
    $('#pt-titik').on('change', () => gambarTitik());
    $('#pt-legend').html(
      `<div><span class="sw" style="background:${C.unguTua}"></span><span class="sw" style="background:${C.unguSedang}"></span><span class="sw" style="background:${C.unguMuda}"></span>Diterapkan (pengurangan tinggi–rendah)</div>` +
      `<div><span class="sw" style="background:${C.limpahan}"></span>Menerima limpahan</div>` +
      `<div><span class="sw" style="background:${C.abu}"></span>Belum diterapkan</div>` +
      `<div><span class="sw dot" style="background:${C.unguGelap}"></span>Gerai patuh · <span class="sw dot" style="background:${C.pink}"></span>Gerai belum diatur</div>`);
    $('#pt-csv').on('click', () => {
      unduhCSV('hasil_per_kecamatan.csv',
        ['Kecamatan', 'Status', 'Gerai', 'Timbulan (t/th)', 'Pengurangan bersih (t/th)', 'Kantong pengganti (t/th)', 'Perpindahan (t/th)', 'Limpahan diterima (t/th)'],
        peta.hasil.map((q) => [q.nama, q.status, q.gerai, q.timbulan, q.bersih, q.substitusi, q.perpindahan, q.limpahan_masuk]));
    });
    initUnggah();
  }

  function gayaPoligon() {
    const maks = Math.max(...peta.hasil.map((q) => q.bersih), 1e-9);
    peta.geo.eachLayer((l) => {
      const id = l.feature.properties.id, q = peta.H[id];
      const fokus = id === S.fokus;
      l.setStyle({ fillColor: warnaKec(q, maks), fillOpacity: 0.72, color: fokus ? C.unguGelap : '#ffffff', weight: fokus ? 3 : 1.2 });
      if (fokus) l.bringToFront();
    });
  }

  function dataTitik(kec) {
    if (S.titikUnggah) return S.titikUnggah;
    const key = kec.map((k) => Math.round(k.gerai)).join(',');
    if (peta.cacheTitik.key !== key) peta.cacheTitik = { key, data: M.titikIlustrasi(kec) };
    return peta.cacheTitik.data;
  }
  function gambarTitik(kec) {
    peta.titik.clearLayers();
    if (!$('#pt-titik').prop('checked')) return;
    dataTitik(kec || M.kecamatan(S.p.total_gerai, S.override)).forEach((t) => {
      const on = S.terapan.has(t.kecamatan);
      L.circleMarker([t.lat, t.lon], { renderer: peta.renderer, radius: 3.2, weight: 1, color: '#fff', fillOpacity: 1,
        fillColor: on ? C.unguGelap : C.pink, interactive: false }).addTo(peta.titik);
    });
  }

  function filterDaftar() {
    const q = $('#pt-cari').val().toLowerCase().trim();
    $('#pt-list .kec-item').each(function () { $(this).toggle(!q || NAMA[$(this).data('id')].toLowerCase().includes(q)); });
  }

  function renderPeta() {
    if (!peta.map) initPeta();
    const p = S.p, sk = S.sk;
    $('#pt-alert').toggleClass('d-none', sk !== 'saat_ini');
    const kec = M.kecamatan(p.total_gerai, S.override);
    const hasil = M.spasial(kec, S.terapan, p, sk);
    peta.hasil = hasil;
    peta.H = Object.fromEntries(hasil.map((q) => [q.id, q]));

    $('#pt-jml').text(S.terapan.size);
    $('#pt-gerai').text(nf(sum(hasil.filter((q) => q.diterapkan), (q) => q.gerai), 0));
    $('#pt-gerai-tot').text(' / ' + nf(sum(hasil, (q) => q.gerai), 0));
    $('#pt-bersih').text(nf(sum(hasil, (q) => q.bersih)));
    $('#pt-limpah').text(nf(sum(hasil, (q) => q.limpahan_keluar)));

    gayaPoligon();
    gambarTitik(kec);

    // daftar kecamatan
    const urut = hasil.slice().sort((a, b) => a.nama.localeCompare(b.nama));
    $('#pt-list').html(urut.map((q) => `
      <div class="kec-item${q.id === S.fokus ? ' selected' : ''}" data-id="${q.id}">
        <div class="custom-control custom-checkbox">
          <input type="checkbox" class="custom-control-input" id="cb-${q.id}" data-id="${q.id}"${q.diterapkan ? ' checked' : ''}>
          <label class="custom-control-label" for="cb-${q.id}"><span class="sr-only">Terapkan di ${esc(q.nama)}</span></label>
        </div>
        <div class="meta"><b>${esc(q.nama)}</b><span class="${q.diterapkan ? 'tx-on' : q.limpahan_masuk > 0 ? 'tx-limpah' : ''}">${q.status}</span></div>
        <div class="val">${q.bersih > 0 ? nf(q.bersih) + ' t' : q.limpahan_masuk > 0 ? '+' + nf(q.limpahan_masuk) + ' t' : ''}</div>
      </div>`).join(''));
    filterDaftar();
    $(`#pt-preset .btn`).each(function () {
      const ids = PRESET[$(this).data('preset')];
      $(this).toggleClass('active', ids.length === S.terapan.size && ids.every((i) => S.terapan.has(i)));
    });

    // detail kecamatan fokus
    const f = peta.H[S.fokus];
    $('#pt-detail').html(`
      <div class="small text-muted">Detail · klik wilayah di peta</div>
      <h6>${esc(f.nama)}</h6>${badge(f.status)}
      <div class="detail-grid">
        <div><b>${nf(f.gerai, 0)}</b><span>Gerai</span></div>
        <div><b>${nf(f.timbulan)} t</b><span>Timbulan kantong/th</span></div>
        <div><b>${nf(f.bersih)} t</b><span>Pengurangan bersih/th</span></div>
        <div><b>${nf(f.limpahan_masuk)} t</b><span>Limpahan diterima/th</span></div>
      </div>
      <button class="btn btn-sm btn-block ${f.diterapkan ? 'btn-outline-secondary' : 'btn-primary'}" id="pt-toggle">
        ${f.diterapkan ? 'Cabut kebijakan di sini' : 'Terapkan kebijakan di sini'}</button>`);

    // dampak terbesar
    const top = hasil.filter((q) => q.bersih > 0).sort((a, b) => b.bersih - a.bersih).slice(0, 8);
    $('#ch-top').toggleClass('d-none', !top.length);
    $('#ch-top-kosong').toggleClass('d-none', !!top.length);
    const optsTop = {
      chart: Object.assign({ type: 'bar', height: Math.max(140, 44 + 32 * top.length) }, APEX),
      series: [{ name: 'Pengurangan bersih', data: top.map((q) => Math.round(q.bersih * 10) / 10) }],
      plotOptions: { bar: { horizontal: true, barHeight: '64%', borderRadius: 5, dataLabels: { position: 'top' } } },
      colors: [C.ungu],
      dataLabels: { enabled: true, formatter: (v) => nf(v), offsetX: 24, style: { colors: [C.tinta], fontWeight: 600 } },
      grid: { borderColor: C.grid, xaxis: { lines: { show: false } } },
      xaxis: { categories: top.map((q) => q.nama), max: Math.max(...top.map((q) => q.bersih), 1) * 1.3, labels: { show: false } },
      yaxis: { labels: { style: { colors: '#59667a' } } },
      tooltip: { y: { formatter: (v) => nf(v) + ' t/th' } },
    };
    if (top.length) {
      if (!chTop) { chTop = new ApexCharts(document.querySelector('#ch-top'), optsTop); chTop.render(); }
      else chTop.updateOptions(optsTop, false, false);
    }

    // tabel
    const rows = hasil.map((q) => [q.nama, q.status, q.gerai, q.timbulan, q.bersih, q.substitusi, q.perpindahan, q.limpahan_masuk]);
    if (!tbKec) {
      tbKec = $('#tb-kec').DataTable({
        data: rows, pageLength: 10, lengthChange: false, order: [[4, 'desc']], autoWidth: false,
        language: { search: 'Cari:', info: '_START_–_END_ dari _TOTAL_', infoEmpty: '', zeroRecords: 'Tidak ada data', paginate: { previous: '‹', next: '›' } },
        columns: [
          { title: 'Kecamatan' },
          { title: 'Status', render: (v, t) => (t === 'display' ? badge(v) : v) },
          { title: 'Gerai', className: 'num', render: (v, t) => (t === 'display' ? nf(v, 0) : v) },
          ...['Timbulan (t/th)', 'Bersih (t/th)', 'Pengganti (t/th)', 'Pindah (t/th)', 'Limpahan masuk (t/th)']
            .map((title) => ({ title, className: 'num', render: (v, t) => (t === 'display' ? nf(v, 2) : v) })),
        ],
      });
    } else tbKec.clear().rows.add(rows).draw(false);

    $('#pt-catatan').text('Batas kecamatan: data terbuka turunan GADM/cahyadsn, belum batas resmi. ' +
      (S.override ? 'Titik gerai berasal dari data yang diunggah. ' : 'Posisi titik gerai acak di dalam kecamatan dan jumlahnya asumsi (ilustrasi). ') +
      'Perpindahan belanja dari kecamatan yang menerapkan kebijakan dibagi rata ke kecamatan tetangga yang belum menerapkan.');
  }

  // unggah CSV lokasi gerai
  function parseCSV(teks) {
    const baris = teks.replace(/^﻿/, '').split(/\r?\n/).filter((b) => b.trim());
    if (!baris.length) return [];
    const sep = (baris[0].match(/;/g) || []).length > (baris[0].match(/,/g) || []).length ? ';' : ',';
    const head = baris[0].split(sep).map((h) => h.trim().replace(/^"|"$/g, '').toLowerCase());
    return baris.slice(1).map((b) => {
      const c = b.split(sep).map((x) => x.trim().replace(/^"|"$/g, ''));
      return Object.fromEntries(head.map((h, i) => [h, c[i]]));
    });
  }
  function initUnggah() {
    let berkas = null;
    $('#pt-file').on('change', function () { berkas = this.files[0] || null; $('#pt-terapkan').prop('disabled', !berkas); });
    $('#pt-terapkan').on('click', () => {
      if (!berkas) return;
      const fr = new FileReader();
      fr.onload = () => {
        const rows = parseCSV(String(fr.result));
        if (!rows.length || !('lat' in rows[0]) || !('lon' in rows[0])) { toast('Kolom lat dan lon tidak ditemukan.'); return; }
        const titik = rows.map((r) => ({ lat: parseFloat(String(r.lat).replace(',', '.')), lon: parseFloat(String(r.lon).replace(',', '.')) }))
          .filter((t) => isFinite(t.lat) && isFinite(t.lon));
        const ditetapkan = M.tetapkanKecamatan(titik);
        const dalam = ditetapkan.filter((t) => t.kecamatan);
        if (!dalam.length) { toast('Tidak ada titik di dalam Kabupaten Sumedang.'); return; }
        S.titikUnggah = dalam;
        S.override = {};
        dalam.forEach((t) => { S.override[t.kecamatan] = (S.override[t.kecamatan] || 0) + 1; });
        S.p.total_gerai = Math.min(Math.max(dalam.length, 50), 1500);
        syncParam(); render();
        $('#pt-reset-gerai').removeClass('d-none');
        $('#pt-sumber').text(`Saat ini: ${dalam.length} gerai dari berkas unggahan`);
        toast(`${dalam.length} gerai dipakai; ${titik.length - dalam.length} titik di luar Kabupaten Sumedang diabaikan.`);
      };
      fr.readAsText(berkas);
    });
    $('#pt-reset-gerai').on('click', function () {
      S.titikUnggah = null; S.override = null; S.p.total_gerai = M.DEFAULT.total_gerai;
      $(this).addClass('d-none');
      $('#pt-sumber').text('Saat ini: titik ilustrasi dari jumlah gerai asumsi');
      syncParam(); render();
    });
  }

  // ------------------------------------------------------------------ PROYEKSI
  const TARGET = { 2025: 10, 2026: 20, 2027: 30, 2028: 40, 2029: 50 };
  let chPr = null, chTarget = null, tbPr = null, prRows = [];
  function renderProyeksi() {
    const p = S.p, sk = S.sk;
    const mulai = Number($('#pr-mulai').val());
    const n = Number($('#pr-n').val());
    const residu = Number($('#pr-residu').val()) || 0;
    const proj = M.proyeksi(p, sk, mulai);
    const mc = M.monteCarlo(p, sk, n, mulai);
    const tahun = proj.map((r) => String(r.tahun));
    const akhir = proj[proj.length - 1], mcAkhir = mc[mc.length - 1];
    const kum = sum(proj, (r) => r.bersih);

    $('#pr-timbulan').text(nf(akhir.timbulan));
    $('#pr-gerai').text(`${nf(akhir.gerai, 0)} gerai`);
    $('#pr-bersih').text(nf(akhir.bersih));
    $('#pr-bersih-sub').text(`rentang P10–P90: ${nf(mcAkhir.p10)}–${nf(mcAkhir.p90)} ton`);
    $('#pr-kum-label').text(`Kumulatif ${tahun[0]}–${tahun[tahun.length - 1]}`);
    $('#pr-kum').text(nf(kum));
    $('#pr-kum-sub').text(`≈ ${nf(p.berat ? kum / p.berat : 0)} juta lembar kantong dicegah`);
    $('#pr-ch-sub').text(`Skenario ${M.SKENARIO[sk]}, mulai ${mulai} · pita = rentang P10–P90 dari ${nf(n, 0)} simulasi`);

    const r1 = (v) => Math.round(v * 10) / 10;
    const series = [
      { type: 'rangeArea', name: 'Rentang P10–P90', data: proj.map((r, i) => ({ x: tahun[i], y: [r1(r.timbulan - mc[i].p90), r1(r.timbulan - mc[i].p10)] })) },
      { type: 'line', name: 'Tanpa kebijakan', data: proj.map((r, i) => ({ x: tahun[i], y: r1(r.timbulan) })) },
      { type: 'line', name: 'Dengan kebijakan', data: proj.map((r, i) => ({ x: tahun[i], y: r1(r.timbulan - r.bersih) })) },
    ];
    const optsPr = {
      chart: Object.assign({ type: 'rangeArea', height: 360, zoom: { enabled: false } }, APEX),
      series,
      colors: [C.ungu, C.pink, C.ungu],
      fill: { opacity: [0.18, 1, 1] },
      stroke: { curve: 'straight', width: [0, 3, 3], dashArray: [0, 6, 0] },
      markers: { size: [0, 5, 5], strokeWidth: 2, strokeColors: '#fff', hover: { sizeOffset: 2 } },
      dataLabels: { enabled: false },
      legend: { position: 'bottom', horizontalAlign: 'left', fontSize: '12.5px', markers: { radius: 3 } },
      grid: { borderColor: C.grid },
      xaxis: { type: 'category', labels: axisLbl, tooltip: { enabled: false } },
      yaxis: { min: 0, forceNiceScale: true, labels: { formatter: (v) => nf(v, 0), style: { colors: C.redup } }, title: { text: 'ton per tahun', style: { color: C.redup, fontWeight: 500 } } },
      annotations: { xaxis: [{ x: String(mulai), borderColor: '#59667a', strokeDashArray: 4, label: { text: 'kebijakan berlaku', orientation: 'horizontal', style: { background: '#59667a', color: '#fff', fontFamily: 'Work Sans' } } }] },
      tooltip: { shared: true, y: { formatter: (v, o) => (Array.isArray(v) ? '' : nf(v) + ' ton') } },
    };
    if (!chPr) { chPr = new ApexCharts(document.querySelector('#ch-proyeksi'), optsPr); chPr.render(); }
    else chPr.updateOptions({ series, annotations: optsPr.annotations }, false, false);

    // target Masterplan
    const ada = residu > 0;
    $('#ch-target, #pr-target-cat').toggleClass('d-none', !ada);
    $('#pr-target-kosong').toggleClass('d-none', ada);
    if (ada) {
      const kontrib = proj.map((r) => Math.round(r.bersih / residu * 10000) / 100);
      const optsT = {
        chart: Object.assign({ type: 'line', height: 300 }, APEX),
        series: [
          { type: 'column', name: 'Kontribusi kebijakan ini', data: kontrib },
          { type: 'line', name: 'Target pengurangan residu', data: proj.map((r) => TARGET[r.tahun]) },
        ],
        colors: [C.ungu, C.amber],
        stroke: { width: [0, 3], dashArray: [0, 6] },
        markers: { size: [0, 5] },
        plotOptions: { bar: { columnWidth: '45%', borderRadius: 5 } },
        dataLabels: { enabled: true, enabledOnSeries: [0], formatter: (v) => nf(v, 2) + '%', offsetY: -8, background: { enabled: false }, style: { colors: [C.tinta], fontWeight: 600 } },
        legend: { position: 'bottom', horizontalAlign: 'left' },
        grid: { borderColor: C.grid },
        xaxis: { categories: tahun, labels: axisLbl },
        yaxis: { min: 0, labels: { formatter: (v) => nf(v, 0) + '%', style: { colors: C.redup } }, title: { text: '% dari residu', style: { color: C.redup, fontWeight: 500 } } },
        tooltip: { shared: true, y: { formatter: (v) => nf(v, 2) + '%' } },
      };
      if (!chTarget) { chTarget = new ApexCharts(document.querySelector('#ch-target'), optsT); chTarget.render(); }
      else chTarget.updateOptions({ series: optsT.series, xaxis: optsT.xaxis }, false, false);
    }

    prRows = proj.map((r, i) => [r.tahun, r.gerai, r.timbulan, r.bersih, r.substitusi, r.perpindahan, mc[i].p10, mc[i].p90]);
    if (!tbPr) {
      tbPr = $('#tb-proyeksi').DataTable({
        data: prRows, paging: false, searching: false, info: false, ordering: false, autoWidth: false,
        columns: [
          { title: 'Tahun' },
          { title: 'Gerai', className: 'num', render: (v, t) => (t === 'display' ? nf(v, 0) : v) },
          ...['Timbulan (t)', 'Bersih (t)', 'Pengganti (t)', 'Pindah (t)', 'P10 (t)', 'P90 (t)']
            .map((title) => ({ title, className: 'num', render: (v, t) => (t === 'display' ? nf(v) : v) })),
        ],
      });
    } else tbPr.clear().rows.add(prRows).draw(false);
  }

  // ------------------------------------------------------------------ ASUMSI
  let tbParam = null;
  function renderAsumsi() {
    const rows = M.PARAMETER.map((q) => [
      q.label, S.p[q.kunci], q.nilai,
      q.kunci === 'total_gerai' ? 'tetap' : `${fmtParam(q.kunci, q.mc_min)} – ${fmtParam(q.kunci, q.mc_maks)} ${q.satuan}`, q.keterangan, q.sumber, q.kunci, q.satuan,
    ]);
    if (!tbParam) {
      tbParam = $('#tb-param').DataTable({
        data: rows, paging: false, searching: false, info: false, ordering: false, autoWidth: false,
        columns: [
          { title: 'Parameter', render: (v) => `<b>${esc(v)}</b>` },
          { title: 'Nilai dipakai', className: 'num nw', render: (v, t, r) => `<span class="${v !== r[2] ? 'changed' : ''}">${fmtParam(r[6], v)}</span> <small class="text-muted">${esc(r[7])}</small>` },
          { title: 'Nilai awal', className: 'num nw', render: (v, t, r) => fmtParam(r[6], v) },
          { title: 'Rentang Monte Carlo', className: 'num nw' },
          { title: 'Keterangan', className: 'ket' },
          { title: 'Sumber', className: 'src' },
        ],
      });
      $('#as-csv').on('click', () => unduhCSV('parameter_model.csv',
        ['Parameter', 'Nilai dipakai', 'Nilai awal', 'Satuan', 'Rentang Monte Carlo', 'Keterangan', 'Sumber'],
        M.PARAMETER.map((q) => [q.label, S.p[q.kunci], q.nilai, q.satuan, q.kunci === 'total_gerai' ? 'tetap' : `${q.mc_min} – ${q.mc_maks}`, q.keterangan, q.sumber])));
    } else tbParam.clear().rows.add(rows).draw(false);
  }

  // ------------------------------------------------------------------ init
  $(function () {
    if (EMBED) document.body.classList.add('embed');
    buildSkenario();
    buildParam();
    syncParam();
    feather.replace();

    $('#btn-menu').on('click', () => { $('#sidebar').addClass('open'); $('#backdrop').addClass('show'); });
    $('#btn-param').on('click', () => { $('#param-panel').addClass('open'); $('#backdrop').addClass('show'); });
    $('#btn-param-close, #backdrop').on('click', tutupLaci);
    $(document).on('keydown', (e) => { if (e.key === 'Escape') tutupLaci(); });
    $('#embed-tabs').on('click', '.btn', function () { location.hash = $(this).data('page'); });
    $('#pr-mulai, #pr-n').on('change', render);
    $('#pr-residu').on('input', jadwalRender);
    $('#pr-csv').on('click', () => unduhCSV('proyeksi.csv', ['Tahun', 'Gerai', 'Timbulan (t)', 'Bersih (t)', 'Pengganti (t)', 'Pindah (t)', 'P10 (t)', 'P90 (t)'], prRows));

    window.addEventListener('hashchange', () => showPage(location.hash.slice(1)));
    showPage(location.hash.slice(1) || 'ringkasan');
  });
}());
