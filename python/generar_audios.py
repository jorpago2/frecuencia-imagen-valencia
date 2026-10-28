"""Genera audios AM por nivel y PSD de las señales moduladas para la web."""
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from scipy.io import wavfile
from scipy import signal
from frecuencia_imagen import (BASE, FS, FS_IF, IMAGE_AMPLITUDE, am_receiver,
                              build_buffers, load_audio, voice_band)

LEVELS = list(range(0, 61, 5))


def physical_key(db):
    return "fisico_off" if db == 0 else "fisico_on" if db == 40 else f"fisico_{db:02d}"


def spectra(pilot, radio, gain, peaks):
    p = signal.resample_poly(pilot, 8, 1)
    m = np.clip(signal.resample_poly(radio, 8, 1), -1, 1)
    phase = 2 * np.pi * 75000 / FS_IF * np.cumsum(m)
    settings = dict(fs=FS_IF, nperseg=8192, noverlap=4096,
                    return_onesided=False, detrend=False, scaling="density")
    f, desired = signal.welch(1 + .65 * p, **settings)
    _, image = signal.welch(IMAGE_AMPLITUDE * np.exp(1j * phase), **settings)
    order = np.argsort(f)
    f, desired, image = f[order], desired[order], image[order]
    reference = float(np.max(desired))

    def points(power, span, group):
        mask = np.abs(f) <= span
        frequencies = f[mask]
        db = 10 * np.log10(np.maximum(power[mask] / reference, 1e-16))
        # Máximos por grupo conservan los picos visibles al reducir el JSON.
        return [[round(float(np.mean(frequencies[i:i+group])), 3),
                 round(float(np.max(db[i:i+group])), 3)]
                for i in range(0, len(frequencies), group)]

    return {"desired": points(desired, 6000, 1), "image": points(image, 120000, 8),
            "physical_levels": LEVELS, "physical_gain": gain, "physical_peaks": peaks,
            "sample_rate": FS_IF, "welch_bin_hz": FS_IF / 8192,
            "description": "PSD media de 24 s. Referencia: pico PSD AM antes de mezclar.",
            "mixer_loss_db": float(20 * np.log10(2))}


def main():
    output = BASE.parent / "assets"
    output.mkdir(exist_ok=True)
    pilot = voice_band(load_audio(BASE / "audios/piloto_tts.wav"))
    pilot /= np.max(np.abs(pilot))
    radio = load_audio(BASE / "audios/radio_marca.wav")
    physical = {}
    for db in LEVELS:
        physical[physical_key(db)] = am_receiver(pilot, radio, db).astype(np.float32)
        print(f"Modelo AM: {db} dB", flush=True)
    # La misma ganancia para TODOS los niveles, sin normalización por estado.
    gain = .85 / max(float(np.max(np.abs(x))) for x in physical.values())
    buffers = {key: value * gain for key, value in physical.items()}
    reference = build_buffers()
    buffers.update({name: reference[name] for name in ("piloto", "radio")})
    peaks = {str(db): float(np.max(np.abs(buffers[physical_key(db)]))) for db in LEVELS}
    with tempfile.TemporaryDirectory() as folder:
        for name, audio in buffers.items():
            assert np.all(np.isfinite(audio)) and np.max(np.abs(audio)) < .851
            wave = Path(folder) / f"{name}.wav"
            wavfile.write(wave, FS, (audio * 32767).astype(np.int16))
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wave),
                            "-c:a", "libmp3lame", "-b:a", "96k", str(output / f"{name}.mp3")],
                           check=True)
    data = spectra(pilot, radio, gain, peaks)
    (output / "spectra.json").write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print("Generados 13 niveles AM, dos referencias y los espectros.")


if __name__ == "__main__":
    main()
