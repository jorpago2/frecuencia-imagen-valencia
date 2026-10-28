export const LEVELS = Array.from({ length: 13 }, (_, index) => index * 5);
export const physicalKey = (db) => db === 0 ? 'fisico_off' : db === 40 ? 'fisico_on' : `fisico_${String(db).padStart(2, '0')}`;
export const amplitude = (db) => 10 ** (-db / 20);
export const AUDIO_NAMES = ['piloto', 'radio', ...LEVELS.map(physicalKey)];

export function mixWeights(mode, source, db) {
  if (!LEVELS.includes(db)) throw new RangeError('El rechazo debe estar entre 0 y 60 dB, en pasos de 5.');
  if (source === 'piloto' || source === 'radio') return { [source]: 1 };
  return mode === 'fisico' ? { [physicalKey(db)]: 1 } : { piloto: 1, radio: .9 * amplitude(db) };
}

export function spectralPoints(points, db, loss = 0, inverted = false) {
  const transformed = points.map(([frequency, power]) => [inverted ? -frequency : frequency, power - db - loss]);
  return inverted ? transformed.reverse() : transformed;
}
