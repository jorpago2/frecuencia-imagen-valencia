"""Frecuencia imagen audible: Valencia APP (AM) y Radio MARCA (FM).

Ejecutar: python frecuencia_imagen.py
Fuentes y límites del modelo: LEEME.txt. No recibe ni transmite señales RF.
"""

import argparse
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from scipy import signal
from scipy.io import wavfile

BASE = Path(__file__).resolve().parent
FS = 32000
FS_IF = 256000
DURATION = 24
RF, LO, IMAGE, IF = 120.1, 109.4, 98.7, 10.7  # MHz
REJECTION_DB = 40
IMAGE_AMPLITUDE = 10 ** (12 / 20)  # +12 dB respecto a la portadora AM
PODCAST = "https://omny.fm/shows/radio-marca-valencia/directo-marca-valencia-26-10-2026"
MEDIA = ("https://traffic.omny.fm/d/clips/4ac2c3a8-bb0c-499b-bf22-ac8400df1983/"
         "5b6911ad-d770-4db3-af9f-acd4011b011e/efe41438-1c99-4a8b-9e13-b4ef00df6d56/audio.mp3")
PILOT_TEXT = (
    "Valencia aproximación, Iberia dos tres cuatro, buenos días. "
    "Establecidos a cinco mil pies, rumbo uno dos cero, con información Alfa. "
    "Solicitamos vectores para la aproximación a Valencia. "
    "Descendiendo a tres mil pies, reducimos a ciento ochenta nudos. "
    "Iberia dos tres cuatro."
)


def load_audio(path):
    rate, data = wavfile.read(path)
    if data.dtype.kind == "i":
        data = data.astype(np.float64) / (2 ** (data.dtype.itemsize * 8 - 1))
    elif data.dtype == np.uint8:
        data = (data.astype(np.float64) - 128) / 128
    elif data.dtype.kind != "f":
        raise ValueError(f"Formato WAV no compatible: {path}")
    if data.ndim == 2:
        data = data.mean(axis=1)
    if data.ndim != 1 or len(data) < rate or not np.all(np.isfinite(data)):
        raise ValueError(f"Audio vacío, demasiado corto o inválido: {path}")
    data = data - data.mean()
    divisor = math.gcd(int(rate), FS)
    data = signal.resample_poly(data, FS // divisor, int(rate) // divisor)
    peak = np.max(np.abs(data))
    if peak < 1e-6:
        raise ValueError(f"El audio no contiene sonido: {path}")
    data /= peak
    # shortcut: se usa un único fragmento de 24 s; ampliar DURATION para otra actividad.
    data = data[:FS * DURATION]
    fade = min(int(.02 * FS), len(data) // 2)
    data[:fade] *= np.linspace(0, 1, fade)
    data[-fade:] *= np.linspace(1, 0, fade)
    return np.pad(data, (0, FS * DURATION - len(data)))


def voice_band(data):
    sos = signal.butter(4, [150, 3000], btype="bandpass", fs=FS, output="sos")
    return signal.sosfilt(sos, data)


def am_receiver(pilot, radio, rejection_db):
    """Envolvente compleja equivalente de la FI; no se muestrea la RF de 120 MHz.

    RF > OL: envolvente AM sin invertir. Imagen < OL: FM conjugada.
    z(t) = (1 + .65 p(t)) + A_i 10^(-R/20) exp(-j phi_FM(t)).
    Rechazo antes del mezclador, canal FI de +/-6 kHz, detector de envolvente.
    """
    p = signal.resample_poly(pilot, 8, 1)
    m = signal.resample_poly(radio, 8, 1)
    m = np.clip(m, -1, 1)
    phase = 2 * np.pi * 75000 / FS_IF * np.cumsum(m)
    image = IMAGE_AMPLITUDE * 10 ** (-rejection_db / 20) * np.exp(-1j * phase)
    z = 1 + .65 * p + image
    channel = signal.butter(6, 6000, fs=FS_IF, output="sos")
    envelope = np.abs(signal.sosfilt(channel, z))
    envelope = signal.resample_poly(envelope, 1, 8)
    result = voice_band((envelope - 1) / .65)
    # Elimina el arranque del detector; misma ventana para todos los estados.
    result[:int(.05 * FS)] *= np.linspace(0, 1, int(.05 * FS))
    return result


def build_buffers(pilot_path=None, radio_path=None):
    pilot = voice_band(load_audio(pilot_path or BASE / "audios/piloto_tts.wav"))
    pilot /= max(np.max(np.abs(pilot)), 1e-9)
    radio_full = load_audio(radio_path or BASE / "audios/radio_marca.wav")
    radio = voice_band(radio_full)
    radio /= max(np.max(np.abs(radio)), 1e-9)
    buffers = {
        "piloto": pilot,
        "radio": radio,
        "didactico_off": pilot + .9 * radio,
        "didactico_on": pilot + .9 * 10 ** (-REJECTION_DB / 20) * radio,
        "fisico_off": am_receiver(pilot, radio_full, 0),
        "fisico_on": am_receiver(pilot, radio_full, REJECTION_DB),
    }
    # Una ganancia fija por modelo; nunca renormalizar al activar el filtro.
    gains = {mode: .85 / max(np.max(np.abs(buffers[mode + suffix]))
                             for suffix in ("_on", "_off"))
             for mode in ("didactico", "fisico")}
    return {key: np.asarray(gains["fisico" if key.startswith("fisico") else "didactico"] * x,
                            dtype=np.float32) for key, x in buffers.items()}


def output_devices():
    import sounddevice as sd
    host = sd.default.hostapi
    devices = [(index, info) for index, info in enumerate(sd.query_devices())
               if info["max_output_channels"] > 0 and info["hostapi"] == host]
    if not devices:
        raise RuntimeError("No se encuentra ninguna salida de audio disponible.")
    return devices


def initial_output(devices, default_device):
    # El proyector HDMI puede aceptar audio sin tener un altavoz audible.
    for index, info in devices:
        if any(word in info["name"].lower() for word in ("altavoces", "speakers")):
            return index
    return next((index for index, _ in devices if index == default_device), devices[0][0])


class Player:
    def __init__(self, buffers, device=None):
        self.buffers = buffers
        self.device = device
        self.key = "didactico_off"
        self.last_key = self.key
        self.position = 0
        self.playing = False
        self.volume = .55
        self.last_volume = 0
        self.stream = None
        self.warning = ""

    def callback(self, outdata, frames, timing, status):
        if status:
            self.warning = str(status)
        if not self.playing:
            outdata.fill(0)
            self.last_volume = 0
            return
        key = self.key
        indices = (np.arange(frames) + self.position) % len(self.buffers[key])
        block = self.buffers[key][indices]
        if key != self.last_key:
            blend = np.linspace(0, 1, frames)
            block = self.buffers[self.last_key][indices] * (1 - blend) + block * blend
            self.last_key = key
        volume = self.volume
        block = block * np.linspace(self.last_volume, volume, frames)
        outdata[:] = block[:, None]
        self.last_volume = volume
        self.position = int((self.position + frames) % len(self.buffers[key]))

    def toggle(self):
        if self.stream is None:
            import sounddevice as sd
            info = sd.query_devices(self.device, "output")
            self.stream = sd.OutputStream(device=self.device, samplerate=FS,
                                          channels=min(2, info["max_output_channels"]), dtype="float32",
                                          blocksize=1024, callback=self.callback)
            try:
                self.stream.start()
            except Exception:
                self.stream.close()
                self.stream = None
                raise
        self.playing = not self.playing

    def close(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.playing = False

    def set_device(self, device):
        was_playing = self.playing
        self.close()
        self.device = device
        self.last_volume = 0
        if was_playing:
            self.toggle()


def launch_gui(buffers):
    import tkinter as tk
    from tkinter import ttk, messagebox
    import sounddevice as sd

    root = tk.Tk()
    root.title("Frecuencia imagen · Valencia APP / Radio MARCA")
    root.geometry("1020x790")
    root.minsize(960, 760)
    root.configure(bg="#eef2f7")
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background="#eef2f7")
    style.configure("TLabel", background="#eef2f7", font=("Segoe UI", 11))
    style.configure("TButton", font=("Segoe UI", 11), padding=8)
    style.configure("TRadiobutton", background="#eef2f7", font=("Segoe UI", 11))
    style.configure("Filter.TCheckbutton", background="#eef2f7", font=("Segoe UI", 15, "bold"))
    main = ttk.Frame(root, padding=18)
    main.pack(fill="both", expand=True)
    ttk.Label(main, text="DOS FRECUENCIAS, UNA MISMA FI", font=("Segoe UI", 23, "bold"),
              foreground="#172b4d").pack(anchor="w")
    ttk.Label(main, text="Escucha la señal del piloto y descubre qué ocurre con la frecuencia imagen.").pack(anchor="w", pady=(4, 12))
    canvas = tk.Canvas(main, height=225, bg="white", highlightthickness=0)
    canvas.pack(fill="x", pady=(0, 8))
    devices = output_devices()
    player = Player(buffers, initial_output(devices, sd.default.device[1]))
    filtering = tk.BooleanVar(value=False)
    mode = tk.StringVar(value="didactico")
    source = tk.StringVar(value="Receptor: ambas señales")
    status = tk.StringVar()
    explanation = tk.StringVar()
    clock = tk.StringVar(value="00:00 / 00:24 · bucle")

    def draw():
        canvas.delete("all")
        width = max(canvas.winfo_width(), 900)
        xs = [width * .17, width * .5, width * .83]
        colors = ["#bd4d16", "#64748b", "#006f86"]
        labels = ["98,7 MHz · IMAGEN", "109,4 MHz · OL", "120,1 MHz · RF"]
        details = ["Radio MARCA · FM", "Oscilador local", "Valencia APP · AM"]
        canvas.create_line(45, 115, width - 45, 115, fill="#cbd5e1", width=2, arrow="last")
        for i, x in enumerate(xs):
            height = 15 if i == 0 and filtering.get() else 60
            canvas.create_line(x, 115, x, 115 - height, fill=colors[i], width=6)
            canvas.create_text(x, 22, text=labels[i], fill=colors[i], font=("Segoe UI", 13, "bold"))
            canvas.create_text(x, 143, text=details[i], fill="#172b4d", font=("Segoe UI", 11))
        canvas.create_text(xs[0], 178, text="↓ −40 dB antes de mezclar" if filtering.get() else "↓ imagen sin rechazar",
                           fill=colors[0], font=("Segoe UI", 11, "bold"))
        canvas.create_text(xs[2], 178, text="↓ señal deseada", fill=colors[2], font=("Segoe UI", 11, "bold"))
        canvas.create_text(width / 2, 205, text="|98,7 − 109,4| = |120,1 − 109,4| = 10,7 MHz",
                           fill="#172b4d", font=("Segoe UI", 15, "bold"))
        canvas.create_text(width - 10, 125, text="f", fill="#64748b")

    def update_choice():
        if source.get().startswith("Solo piloto"):
            player.key = "piloto"
        elif source.get().startswith("Solo Radio"):
            player.key = "radio"
        else:
            player.key = mode.get() + ("_on" if filtering.get() else "_off")
        state_text = "ACTIVO · rechazo de 40 dB" if filtering.get() else "DESACTIVADO · entra la imagen"
        if source.get().startswith("Solo"):
            status.set("Escucha de referencia: el filtro no se aplica a los audios aislados.")
        else:
            status.set("Filtro de rechazo de imagen " + state_text)
        if mode.get() == "didactico":
            explanation.set("Modo didáctico: suma de audios para reconocer las dos fuentes. "
                            "Al activar el filtro, Radio MARCA baja 40 dB y el piloto conserva su nivel. "
                            "Esta suma no reproduce la demodulación AM de una interferencia FM.")
        else:
            explanation.set("Modelo AM: piloto AM + imagen FM (desviación ±75 kHz), canal FI de 12 kHz "
                            "y detector de envolvente. Radio MARCA puede oírse como distorsión o ruido. "
                            "Imagen de entrada: +12 dB; rechazo previo al mezclador: 40 dB.")
        draw()

    ttk.Checkbutton(main, text="Activar filtro de rechazo de imagen (40 dB)", variable=filtering,
                    command=update_choice, style="Filter.TCheckbutton").pack(anchor="w", pady=(0, 6))
    ttk.Label(main, textvariable=status, foreground="#006f86").pack(anchor="w", pady=(0, 12))
    modes = ttk.Frame(main)
    modes.pack(fill="x")
    ttk.Radiobutton(modes, text="Superposición didáctica", value="didactico", variable=mode,
                    command=update_choice).pack(side="left", padx=(0, 24))
    ttk.Radiobutton(modes, text="Receptor AM (modelo)", value="fisico", variable=mode,
                    command=update_choice).pack(side="left")
    ttk.Label(main, textvariable=explanation, wraplength=910, justify="left").pack(fill="x", pady=(8, 10))
    controls = ttk.Frame(main)
    controls.pack(fill="x")

    def toggle():
        try:
            player.toggle()
            play_button.configure(text="Pausar" if player.playing else "Reproducir")
        except Exception as exc:
            messagebox.showerror("Salida de audio", "No se ha podido abrir la salida de audio.\n"
                                 "Selecciona otra salida en la propia ventana.\n\n" + str(exc))

    play_button = ttk.Button(controls, text="Reproducir", command=toggle)
    play_button.pack(side="left")
    ttk.Button(controls, text="Volver al inicio", command=lambda: setattr(player, "position", 0)).pack(side="left", padx=10)
    ttk.Label(controls, textvariable=clock).pack(side="right")
    row = ttk.Frame(main)
    row.pack(fill="x", pady=(12, 10))
    ttk.Label(row, text="Escuchar:").pack(side="left", padx=(0, 10))
    selector = ttk.Combobox(row, textvariable=source, state="readonly", width=32,
                            values=["Receptor: ambas señales", "Solo piloto TTS", "Solo Radio MARCA"])
    selector.pack(side="left")
    selector.bind("<<ComboboxSelected>>", lambda event: update_choice())
    ttk.Label(row, text="Volumen").pack(side="left", padx=(25, 10))
    volume = ttk.Scale(row, from_=0, to=1, value=player.volume,
                        command=lambda value: setattr(player, "volume", float(value)))
    volume.pack(side="left", fill="x", expand=True)
    output_row = ttk.Frame(main)
    output_row.pack(fill="x", pady=(0, 4))
    ttk.Label(output_row, text="Salida de audio:").pack(side="left", padx=(0, 10))
    labels = [f"{info['name']} [{index}]" for index, info in devices]
    output_selector = ttk.Combobox(output_row, state="readonly", width=59, values=labels)
    output_selector.current(next(i for i, (index, _) in enumerate(devices) if index == player.device))
    output_selector.pack(side="left", fill="x", expand=True)

    def change_output(event):
        try:
            player.set_device(devices[output_selector.current()][0])
        except Exception as exc:
            messagebox.showerror("Salida de audio", str(exc))
        play_button.configure(text="Pausar" if player.playing else "Reproducir")

    output_selector.bind("<<ComboboxSelected>>", change_output)
    ttk.Separator(main).pack(fill="x", pady=10)
    ttk.Label(main, text="¿Por qué un filtro situado después del mezclador ya no puede separar ambas portadoras?",
              font=("Segoe UI", 12, "bold"), wraplength=910).pack(anchor="w", pady=4)
    ttk.Label(main, text="Voz TTS ficticia · Radio MARCA Valencia: fragmento de podcast, 26/10/2026.\n"
              "Esquema de frecuencias con alturas arbitrarias. Modelo docente; no es una recepción RF real.",
              foreground="#64748b", font=("Segoe UI", 10), wraplength=910).pack(anchor="w", pady=6)
    canvas.bind("<Configure>", lambda event: draw())

    def tick():
        seconds = player.position // FS
        clock.set(f"00:{seconds:02d} / 00:{DURATION:02d} · bucle")
        if player.warning:
            status.set("Aviso de audio: " + player.warning)
            player.warning = ""
        root.after(150, tick)

    def close():
        player.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    root.bind("<space>", lambda event: toggle() if event.widget == root else None)
    update_choice()
    tick()
    root.mainloop()


def prepare_audio():
    """Regenera las fuentes; sólo esta opción requiere red, FFmpeg y Windows TTS."""
    if sys.platform != "win32":
        raise RuntimeError("La regeneración TTS usa las voces locales de Windows.")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("Instala FFmpeg para extraer el fragmento de Radio MARCA.")
    (BASE / "audios").mkdir(exist_ok=True)
    # Rutas relativas al cwd evitan interpolar texto del usuario en código PowerShell.
    script = """
    Add-Type -AssemblyName System.Speech
    $synthDemo = New-Object System.Speech.Synthesis.SpeechSynthesizer
    try {
        $spanishDemo = @($synthDemo.GetInstalledVoices() | Where-Object {
            $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'es-ES'
        })
        if ($spanishDemo.Count -eq 0) { throw 'Instala una voz TTS en español de España.' }
        $pabloDemo = @($spanishDemo | Where-Object { $_.VoiceInfo.Name -eq 'Microsoft Pablo' })
        if ($pabloDemo.Count -gt 0) { $synthDemo.SelectVoice('Microsoft Pablo') }
        else { $synthDemo.SelectVoice($spanishDemo[0].VoiceInfo.Name) }
        $synthDemo.Rate = 0
        $synthDemo.SetOutputToWaveFile((Join-Path (Get-Location) 'audios/piloto_tts.wav'))
        $synthDemo.Speak((Get-Content 'audios/texto_piloto.txt' -Raw -Encoding UTF8))
    } finally { $synthDemo.Dispose() }
    """
    # Validar ambas fuentes antes de reemplazar los audios que ya funcionaban.
    with tempfile.TemporaryDirectory() as folder:
        stage = Path(folder)
        (stage / "audios").mkdir()
        (stage / "audios/texto_piloto.txt").write_text(PILOT_TEXT, encoding="utf-8")
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                        "$ErrorActionPreference = 'Stop'; " + script], cwd=stage, check=True, timeout=60)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-rw_timeout", "20000000",
                        "-ss", "45", "-i", MEDIA, "-t", str(DURATION), "-ac", "1", "-ar", str(FS),
                        "-y", str(stage / "audios/radio_marca.wav")], check=True, timeout=90)
        for name in ("piloto_tts.wav", "radio_marca.wav"):
            load_audio(stage / "audios" / name)
        for name in ("piloto_tts.wav", "radio_marca.wav", "texto_piloto.txt"):
            shutil.copyfile(stage / "audios" / name, BASE / "audios" / name)
    print("Audios preparados.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparar", action="store_true", help="Regenerar TTS y fragmento de Radio MARCA")
    parser.add_argument("--exportar", action="store_true", help="Guardar WAV comparativos sin abrir la ventana")
    args = parser.parse_args()
    if args.preparar:
        prepare_audio()
        return
    buffers = build_buffers()
    if args.exportar:
        folder = BASE / "comparaciones"
        folder.mkdir(exist_ok=True)
        for key, data in buffers.items():
            wavfile.write(folder / f"{key}.wav", FS, (data * 32767).astype(np.int16))
        print(f"Audios guardados en {folder}")
    else:
        launch_gui(buffers)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"No se puede iniciar la demostración: {exc}", file=sys.stderr)
        sys.exit(1)
