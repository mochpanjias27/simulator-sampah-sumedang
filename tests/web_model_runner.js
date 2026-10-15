// Menjalankan web/js/model.js di Node untuk diuji kesetaraannya dengan src/model.py.
// Dipanggil oleh tests/test_model_web.py; masukan JSON lewat argumen pertama.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.resolve(__dirname, '..');
const ctx = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(root, 'web/js/data.js'), 'utf8'), ctx);
const M = require(path.join(root, 'web/js/model.js'))(ctx.window.SIM_DATA);

const kasus = JSON.parse(process.argv[2]);
const out = kasus.map(({ p, sk, terapan, mulai }) => ({
  ringkasan: M.ringkasan(p, sk),
  spasial: M.spasial(M.kecamatan(p.total_gerai), new Set(terapan), p, sk),
  proyeksi: M.proyeksi(p, sk, mulai),
  mc: M.monteCarlo(p, sk, 4000, mulai),
}));
process.stdout.write(JSON.stringify(out));
