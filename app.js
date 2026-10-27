const $ = (id) => document.getElementById(id);
const names = ['piloto', 'radio', 'didactico_off', 'didactico_on', 'fisico_off', 'fisico_on'];
const assets = ['piloto', 'radio', 'fisico_off', 'fisico_on'];
let context, master, analyser, decoded, loading, sources = [], gains = {};
let playing = false, rejected = false, source = 'ambas', startedAt = 0;
let activeKey = 'didactico_off';
const canvas = $('waveform');
const drawing = canvas.getContext('2d');
const modeDescriptions = {
  didactico: 'Dos audios reconocibles para escuchar cómo la imagen contamina la señal deseada. Es una analogía, no una demodulación AM de la emisora FM.',
  fisico: 'Piloto AM + imagen FM, canal de FI y detector de envolvente. La imagen puede producir distorsión o ruido. Es un modelo, no una grabación RF.',
};

function status(message, error = false) {
  $('audio-status').textContent = message;
  $('audio-status').classList.toggle('error', error);
}

function selectedKey() {
  return source === 'ambas' ? `${$('mode').value}_${rejected ? 'on' : 'off'}` : source;
}

function updateMix() {
  activeKey = selectedKey();
  if (context && gains[activeKey]) {
    for (const name of names) {
      const parameter = gains[name].gain;
      parameter.cancelAndHoldAtTime(context.currentTime);
      parameter.linearRampToValueAtTime(name === activeKey ? 1 : 0, context.currentTime + .04);
    }
  }
  const nativeSource = source !== 'ambas';
  $('filter-note').textContent = nativeSource
    ? 'Escucha de referencia: el filtro no se aplica a las fuentes aisladas. Selecciona Ambas señales para comparar.'
    : 'Se aplica antes del mezclador. Al conmutar se conserva el instante de escucha y la ganancia del piloto.';
  $('mode-description').textContent = modeDescriptions[$('mode').value];
  $('signal-label').textContent = source === 'piloto' ? 'Piloto · TTS' : source === 'radio' ? 'Radio MARCA' : 'Salida del receptor';
}

function startSources() {
  for (const node of sources) { node.stop(); node.disconnect(); }
  sources = [];
  for (const node of Object.values(gains)) node.disconnect();
  gains = {};
  startedAt = context.currentTime + .06;
  for (const name of names) {
    const node = context.createBufferSource();
    node.buffer = decoded[name];
    node.loop = true;
    node.loopEnd = 24;
    const gain = context.createGain();
    gain.gain.value = name === selectedKey() ? 1 : 0;
    node.connect(gain).connect(master);
    node.start(startedAt);
    sources.push(node);
    gains[name] = gain;
  }
}

async function prepare() {
  if (!context) {
    const AudioEngine = window.AudioContext || window.webkitAudioContext;
    if (!AudioEngine) throw new Error('Este navegador no permite mezclar audio. Usa los reproductores convencionales de abajo.');
    context = new AudioEngine();
    master = context.createGain();
    master.gain.value = Number($('volume').value) / 100;
    analyser = context.createAnalyser();
    analyser.fftSize = 2048;
    master.connect(analyser).connect(context.destination);
  }
  // La activación ocurre directamente dentro del gesto del usuario.
  await context.resume();
  if (context.state !== 'running') throw new Error('El navegador no ha activado la salida. Pulsa Reproducir de nuevo.');
  if (!decoded) {
    loading ||= Promise.all(assets.map(async (name) => {
      const response = await fetch(new URL(`assets/${name}.mp3`, import.meta.url));
      if (!response.ok) throw new Error(`No se ha podido cargar ${name} (${response.status}).`);
      const buffer = await context.decodeAudioData(await response.arrayBuffer());
      if (buffer.duration < 24) throw new Error(`El audio ${name} está incompleto.`);
      return [name, buffer];
    })).then((entries) => Object.fromEntries(entries)).catch((error) => { loading = null; throw error; });
    decoded = await loading;
    // Mezclar las mismas fuentes decodificadas conserva exactamente los 40 dB.
    for (const state of ['off', 'on']) {
      const length = Math.min(decoded.piloto.length, decoded.radio.length);
      const buffer = context.createBuffer(1, length, context.sampleRate);
      const output = buffer.getChannelData(0);
      const pilot = decoded.piloto.getChannelData(0);
      const radio = decoded.radio.getChannelData(0);
      const imageGain = .9 * (state === 'on' ? .01 : 1);
      for (let i = 0; i < length; i++) output[i] = pilot[i] + imageGain * radio[i];
      decoded[`didactico_${state}`] = buffer;
    }
    startSources();
  }
}

$('play').addEventListener('click', async () => {
  const button = $('play');
  button.disabled = true;
  try {
    if (playing) {
      await context.suspend();
      playing = false;
      button.textContent = '▶ Reproducir';
      status('En pausa. Puedes cambiar el modo o el filtro.');
    } else {
      status('Preparando el audio…');
      for (const audio of document.querySelectorAll('audio')) audio.pause();
      await prepare();
      playing = true;
      button.textContent = 'Ⅱ Pausar';
      status('Reproduciendo en bucle · usa el filtro para comparar el mismo instante.');
    }
  } catch (error) {
    playing = false;
    button.textContent = '▶ Reproducir';
    status(error.message, true);
  } finally { button.disabled = false; }
});

$('filter').addEventListener('click', () => {
  rejected = !rejected;
  $('filter').setAttribute('aria-pressed', String(rejected));
  $('filter-state').textContent = rejected ? 'Activado · 40 dB' : 'Desactivado';
  $('filter-badge').textContent = rejected ? 'IMAGEN ATENUADA · −40 dB' : 'IMAGEN SIN RECHAZAR';
  $('filter-badge').classList.toggle('active', rejected);
  $('image-bar').classList.toggle('rejected', rejected);
  updateMix();
});
$('mode').addEventListener('change', updateMix);
for (const button of document.querySelectorAll('.source')) {
  button.addEventListener('click', () => {
    source = button.dataset.source;
    for (const item of document.querySelectorAll('.source')) {
      item.classList.toggle('selected', item === button);
      item.setAttribute('aria-pressed', String(item === button));
    }
    updateMix();
  });
}
$('volume').addEventListener('input', () => {
  const value = Number($('volume').value) / 100;
  $('volume-value').textContent = `${Math.round(value * 100)} %`;
  if (master) master.gain.setTargetAtTime(value, context.currentTime, .02);
});
$('restart').addEventListener('click', () => {
  if (decoded) startSources();
  $('clock').textContent = '00:00 / 00:24';
});
for (const audio of document.querySelectorAll('audio')) {
  audio.addEventListener('play', async () => {
    for (const other of document.querySelectorAll('audio')) if (other !== audio) other.pause();
    if (playing) {
      await context.suspend();
      playing = false;
      $('play').textContent = '▶ Reproducir';
      status('Escucha de referencia en el reproductor convencional.');
    }
  });
}

let lastDraw = 0;
function render(time) {
  requestAnimationFrame(render);
  if (time - lastDraw < 65) return;
  lastDraw = time;
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.round(canvas.clientWidth * ratio);
  const height = Math.round(canvas.clientHeight * ratio);
  if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
  drawing.clearRect(0, 0, width, height);
  drawing.strokeStyle = '#6f999722';
  drawing.lineWidth = ratio;
  for (let y = height / 4; y < height; y += height / 4) {
    drawing.beginPath(); drawing.moveTo(0, y); drawing.lineTo(width, y); drawing.stroke();
  }
  let data = new Float32Array(512);
  if (playing && analyser) { data = new Float32Array(analyser.fftSize); analyser.getFloatTimeDomainData(data); }
  drawing.strokeStyle = '#9ad8c5'; drawing.lineWidth = 1.5 * ratio; drawing.beginPath();
  let squares = 0;
  data.forEach((sample, i) => {
    squares += sample * sample;
    const x = i / (data.length - 1) * width;
    const y = height / 2 - sample * height * .44;
    i ? drawing.lineTo(x, y) : drawing.moveTo(x, y);
  });
  drawing.stroke();
  const db = 20 * Math.log10(Math.sqrt(squares / data.length));
  $('level').textContent = Number.isFinite(db) ? `${Math.round(db)} dBFS` : '−∞ dBFS';
  $('level').setAttribute('aria-valuenow', String(Math.max(-60, Math.min(0, Number.isFinite(db) ? db : -60))));
  if (context && decoded) {
    const seconds = Math.floor(Math.max(0, context.currentTime - startedAt) % 24);
    $('clock').textContent = `00:${String(seconds).padStart(2, '0')} / 00:24`;
  }
}
requestAnimationFrame(render);
