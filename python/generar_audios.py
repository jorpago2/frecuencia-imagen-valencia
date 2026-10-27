"""Genera los cuatro assets de la web a partir de los WAV y del modelo Python."""
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from scipy.io import wavfile
from frecuencia_imagen import BASE, FS, build_buffers


def main():
    output = BASE.parent / "assets"
    output.mkdir(exist_ok=True)
    buffers = build_buffers()
    with tempfile.TemporaryDirectory() as folder:
        for name in ("piloto", "radio", "fisico_off", "fisico_on"):
            audio = buffers[name]
            assert np.all(np.isfinite(audio)) and np.max(np.abs(audio)) < 1
            wave = Path(folder) / f"{name}.wav"
            wavfile.write(wave, FS, (audio * 32767).astype(np.int16))
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wave),
                            "-c:a", "libmp3lame", "-b:a", "96k", str(output / f"{name}.mp3")],
                           check=True)
    print("Cuatro audios generados. Los estados didácticos se mezclan en el navegador.")


if __name__ == "__main__":
    main()
