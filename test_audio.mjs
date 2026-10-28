import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, statSync } from 'node:fs';
import { LEVELS, AUDIO_NAMES, mixWeights, physicalKey, spectralPoints } from './audio-model.js';

test('el deslizador atenúa la imagen y mantiene el piloto; aisladas sin filtro', () => {
  for (const db of LEVELS) {
    const mix = mixWeights('didactico', 'ambas', db);
    assert.equal(mix.piloto, 1);
    assert.ok(Math.abs(20 * Math.log10(mix.radio / .9) + db) < 1e-10);
    assert.deepEqual(mixWeights('fisico', 'piloto', db), { piloto: 1 });
    assert.deepEqual(mixWeights('didactico', 'radio', db), { radio: 1 });
  }
  assert.throws(() => mixWeights('fisico', 'ambas', 17), RangeError);
});

test('cada nivel AM tiene un audio calculado, válido y sin normalización individual', () => {
  const data = JSON.parse(readFileSync(new URL('./assets/spectra.json', import.meta.url)));
  assert.deepEqual(data.physical_levels, LEVELS);
  assert.equal(new Set(AUDIO_NAMES).size, 15);
  assert.ok(data.physical_gain > 0);
  for (const db of LEVELS) {
    const key = physicalKey(db);
    assert.deepEqual(mixWeights('fisico', 'ambas', db), { [key]: 1 });
    assert.ok(statSync(new URL(`./assets/${key}.mp3`, import.meta.url)).size > 100000);
    assert.ok(data.physical_peaks[db] > 0 && data.physical_peaks[db] <= .851);
  }
  assert.ok(Math.max(...Object.values(data.physical_peaks)) - Math.min(...Object.values(data.physical_peaks)) > .3);
});

test('espectros: rechazo exacto en dB, inversión de imagen y pérdida de mezcla', () => {
  const data = JSON.parse(readFileSync(new URL('./assets/spectra.json', import.meta.url)));
  assert.ok(data.desired.length > 300 && data.image.length > 900);
  assert.equal(Math.max(...data.desired.map(p => p[1])), 0);
  assert.ok(Math.abs(data.mixer_loss_db - 6.020599913) < 1e-8);
  for (const db of LEVELS) {
    const before = spectralPoints(data.image, db);
    const after = spectralPoints(data.image, db, data.mixer_loss_db, true);
    for (let i = 0; i < before.length; i++) {
      assert.equal(before[i][0], data.image[i][0]);
      assert.ok(Math.abs(before[i][1] - data.image[i][1] + db) < 1e-10);
      const reversed = after[after.length - 1 - i];
      assert.equal(reversed[0], -before[i][0]);
      assert.ok(Math.abs(reversed[1] - before[i][1] + data.mixer_loss_db) < 1e-10);
    }
  }
});
