import { spectralPoints } from './audio-model.js';

let data, rejection = 0;
const $ = (id) => document.getElementById(id);
const signed = (value) => `${value > 0 ? '+' : ''}${value}`;

function draw(id, after) {
  if (!data) return;
  const svg = $(id);
  const width = Math.max(280, svg.clientWidth);
  const height = 268, left = 47, right = width - 17, top = 39, bottom = 213;
  const y = (db) => bottom - (db + 110) / 115 * (bottom - top);
  let markup = `<defs><clipPath id="${id}-clip"><rect x="${left}" y="${top}" width="${right-left}" height="${bottom-top}"/></clipPath></defs>`;
  markup += `<text x="2" y="16" class="axis-title">PSD (dB rel.)</text>`;
  for (const db of [0, -20, -40, -60, -80, -100]) {
    markup += `<line x1="${left}" x2="${right}" y1="${y(db)}" y2="${y(db)}" class="grid-line"/><text x="${left-8}" y="${y(db)+4}" text-anchor="end" class="tick-label">${db}</text>`;
  }
  const path = (points, x, color, kind, baseline = false) => {
    const d = points.map(([frequency, db], index) => `${index ? 'L' : 'M'}${x(frequency).toFixed(2)},${y(db).toFixed(2)}`).join(' ');
    return `<path d="${d}" fill="none" stroke="${color}" stroke-width="${baseline ? 1 : 1.6}" ${baseline ? 'stroke-dasharray="4 3" opacity=".65"' : ''} clip-path="url(#${id}-clip)" class="spectrum-curve" data-kind="${kind}"/>`;
  };
  const axis = (x, span, ticks) => {
    markup += `<line x1="${x(-span)}" x2="${x(span)}" y1="${bottom}" y2="${bottom}" class="axis-line"/>`;
    for (const tick of ticks) {
      markup += `<line x1="${x(tick)}" x2="${x(tick)}" y1="${bottom}" y2="${bottom+5}" class="axis-line"/><text x="${x(tick)}" y="${bottom+19}" text-anchor="middle" class="tick-label">${signed(tick/1000)}</text>`;
    }
  };
  const desired = spectralPoints(data.desired, 0, after ? data.mixer_loss_db : 0);
  const image = spectralPoints(data.image, rejection, after ? data.mixer_loss_db : 0, after);
  const original = spectralPoints(data.image, 0, after ? data.mixer_loss_db : 0, after);
  if (after) {
    const span = $('fi-zoom').checked ? 8000 : 120000;
    const x = (frequency) => left + (frequency + span) / (2 * span) * (right - left);
    markup += `<rect x="${x(-6000)}" y="${top}" width="${x(6000)-x(-6000)}" height="${bottom-top}" fill="#137d8312"/><text x="${(left+right)/2}" y="21" text-anchor="middle" class="panel-title">Ambas señales centradas en 10,7 MHz</text>`;
    for (const edge of [-6000, 6000]) markup += `<line x1="${x(edge)}" x2="${x(edge)}" y1="${top}" y2="${bottom}" stroke="#137d8360" stroke-dasharray="3 3"/>`;
    markup += path(original, x, '#94a09e', 'baseline', true);
    markup += path(image, x, '#b55520', 'image');
    markup += path(desired, x, '#137d83', 'desired');
    axis(x, span, [-span, -span/2, 0, span/2, span]);
    markup += `<text x="${(left+right)/2}" y="257" text-anchor="middle" class="axis-title">Desviación respecto de 10,7 MHz (kHz)</text>`;
  } else {
    const gap = 28, half = (right-left-gap)/2;
    const xImage = (frequency) => left + (frequency+120000)/240000*half;
    const xDesired = (frequency) => left + half + gap + (frequency+6000)/12000*half;
    markup += `<text x="${left+half/2}" y="21" text-anchor="middle" class="panel-title image-label">FM · 98,7 MHz</text><text x="${right-half/2}" y="21" text-anchor="middle" class="panel-title desired-label">AM · 120,1 MHz</text>`;
    markup += path(original, xImage, '#94a09e', 'baseline', true);
    markup += path(image, xImage, '#b55520', 'image');
    markup += path(desired, xDesired, '#137d83', 'desired');
    const middle = left + half + gap/2;
    markup += `<rect x="${left+half+2}" y="${top}" width="${gap-4}" height="${bottom-top}" fill="#fffdf6"/><text x="${middle}" y="${bottom+4}" text-anchor="middle" class="axis-break">∕∕</text>`;
    axis(xImage, 120000, [-120000, 0, 120000]);
    axis(xDesired, 6000, [-6000, 0, 6000]);
    markup += `<text x="${(left+right)/2}" y="257" text-anchor="middle" class="axis-title">Desviación de cada portadora (kHz) · eje RF interrumpido</text>`;
  }
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.setAttribute('aria-label', `${after ? 'Después' : 'Antes'} del mezclador. Imagen atenuada ${rejection} dB; señal deseada sin rechazo.`);
  svg.innerHTML = markup;
}

export function updateSpectra(db) {
  rejection = db;
  $('spectra-summary').textContent = `Rechazo aplicado: ${db} dB · Imagen a ${signed(12-db)} dBc en RF`;
  draw('spectrum-rf', false);
  draw('spectrum-if', true);
}

export async function initSpectra() {
  $('fi-zoom').addEventListener('change', () => draw('spectrum-if', true));
  const observer = new ResizeObserver(() => updateSpectra(rejection));
  observer.observe($('spectrum-rf'));
  try {
    const response = await fetch(new URL('./assets/spectra.json', import.meta.url));
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    data = await response.json();
    for (const name of ['desired', 'image']) {
      if (!Array.isArray(data[name]) || !data[name].length || !data[name].every(p => p.length === 2 && p.every(Number.isFinite))) throw new Error('Datos de espectro inválidos');
    }
    updateSpectra(rejection);
  } catch (error) {
    $('spectra-status').textContent = `No se han podido cargar los espectros: ${error.message}. Recarga la página.`;
    data = null;
  }
}
