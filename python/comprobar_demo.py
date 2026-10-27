"""Comprobaciones numéricas y del reproductor, sin necesidad de altavoces."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
from scipy.io import wavfile

import frecuencia_imagen as demo


def main():
    assert abs(abs(demo.RF - demo.LO) - demo.IF) < 1e-12
    assert abs(abs(demo.IMAGE - demo.LO) - demo.IF) < 1e-12
    assert abs(demo.IMAGE - (demo.RF - 2 * demo.IF)) < 1e-12
    devices = [(3, {"name": "EPSON PJ"}), (4, {"name": "Altavoces (Realtek)"})]
    assert demo.initial_output(devices, 3) == 4
    assert demo.initial_output([(3, {"name": "HDMI"})], 3) == 3
    buffers = demo.build_buffers()
    for audio in buffers.values():
        assert audio.shape == (demo.FS * demo.DURATION,)
        assert audio.dtype == np.float32 and np.all(np.isfinite(audio))
        assert 0 < np.max(np.abs(audio)) < .851
    # Misma voz y ganancia en ambos estados: sólo cambia la contribución imagen.
    off = buffers["didactico_off"] - buffers["piloto"]
    on = buffers["didactico_on"] - buffers["piloto"]
    measured_db = float(20 * np.log10(np.linalg.norm(off) / np.linalg.norm(on)))
    assert abs(measured_db - demo.REJECTION_DB) < .001
    assert np.allclose(off, .9 * buffers["radio"], atol=1e-7)
    t = np.arange(demo.FS) / demo.FS
    pilot = .5 * np.sin(2 * np.pi * 700 * t)
    with patch.object(demo, "IMAGE_AMPLITUDE", 0):
        recovered = demo.am_receiver(pilot, np.zeros_like(pilot), 0)
    target = demo.voice_band(pilot)
    segment = slice(demo.FS // 2, None)
    # El filtro causal introduce retardo y fase; comprobar tono y amplitud recuperados.
    spectrum = np.abs(np.fft.rfft(recovered[segment]))
    frequency = np.fft.rfftfreq(len(recovered[segment]), 1 / demo.FS)[np.argmax(spectrum)]
    assert frequency == 700
    amplitude_ratio = np.std(recovered[segment]) / np.std(target[segment])
    assert .98 < amplitude_ratio < 1.02
    player = demo.Player(buffers)
    block = np.empty((1024, 1), dtype=np.float32)
    player.callback(block, 1024, None, None)
    assert np.all(block == 0) and player.position == 0
    player.playing = True
    for key in buffers:
        player.key = key
        old_position = player.position
        player.callback(block, 1024, None, None)
        assert player.position == old_position + 1024
        assert np.all(np.isfinite(block)) and np.max(np.abs(block)) < 1
    player.position = len(buffers["piloto"]) - 20
    player.callback(block, 1024, None, None)
    assert player.position == 1004
    player.playing = False
    player.callback(block, 1024, None, None)
    assert np.all(block == 0)
    # Las dos salidas estéreo deben llevar la misma señal, sin perder un canal.
    player.playing = True
    stereo_block = np.empty((1024, 2), dtype=np.float32)
    player.callback(stereo_block, 1024, None, None)
    assert np.max(np.abs(stereo_block)) > 0
    assert np.array_equal(stereo_block[:, 0], stereo_block[:, 1])
    with patch.object(player, "toggle") as reopen:
        previous_position = player.position
        player.set_device(4)
        assert player.device == 4 and player.position == previous_position
        reopen.assert_called_once()
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "silencio.wav"
        wavfile.write(path, demo.FS, np.zeros(demo.FS, dtype=np.int16))
        try:
            demo.load_audio(path)
        except ValueError:
            pass
        else:
            raise AssertionError("Un WAV silencioso debe rechazarse")
        path = Path(folder) / "stereo.wav"
        stereo = np.column_stack((pilot, pilot)).astype(np.float32)
        wavfile.write(path, demo.FS, stereo)
        assert demo.load_audio(path).shape == (demo.FS * demo.DURATION,)
    report = {
        "estado": "correcto",
        "rechazo_didactico_dB": measured_db,
        "tono_AM_recuperado_Hz": float(frequency),
        "relacion_amplitud_AM": float(amplitude_ratio),
        "comprobaciones": ["plan de frecuencias", "audios válidos y sin recorte",
                           "rechazo 40 dB sin cambiar piloto", "detector AM sin imagen",
                           "cambio de fuente sin reinicio", "pausa y bucle",
                           "rechazo de WAV silencioso", "lectura estéreo",
                           "salida inicial de altavoces", "salida estéreo en ambos canales",
                           "cambio de dispositivo sin reinicio"],
        "escucha_humana": "no realizada",
    }
    (demo.BASE / "verificacion.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
