# Frecuencia imagen · Valencia

Laboratorio sonoro de CSAF para explorar un receptor superheterodino sintonizado
a Valencia APP. Incluye voz TTS ficticia de un piloto, un fragmento de Radio MARCA
Valencia y un rechazo de imagen conmutable de 40 dB.

**Web:** https://jorpago2.github.io/frecuencia-imagen-valencia/

## Uso

Pulsa **Reproducir**; alterna el filtro y compara los modos:

- **Superposición didáctica:** audios reconocibles; la contribución imagen baja
  40 dB y la contribución del piloto conserva su nivel.
- **Receptor AM · modelo:** piloto AM e imagen FM, filtro de canal y detector de
  envolvente. La interferencia puede sonar como distorsión o ruido.

La conmutación conserva el instante de escucha. Los botones de fuentes aisladas
son referencias sin filtro. La página también incluye reproductores HTML de audio
convencionales para escuchar cada fuente sin el mezclador interactivo.

El audio comienza con un gesto del usuario; no hay reproducción automática.
No se requieren cuentas, instalación, servicios de pago ni API TTS durante el uso.

## Plan de frecuencias

| Elemento | Frecuencia |
| --- | --- |
| Señal deseada: Valencia APP, AM | 120,1 MHz |
| Oscilador local, inyección baja | 109,4 MHz |
| FI elegida para la actividad | 10,7 MHz |
| Imagen: Radio MARCA Valencia, FM | 98,7 MHz |

`abs(120.1 - 109.4) = abs(98.7 - 109.4) = 10.7 MHz`.

El mezclador lleva ambas bandas al mismo centro de FI. El preselector rechaza
la imagen antes de la mezcla. Un filtro de FI no elimina por completo la imagen
coincidente sin afectar también al canal útil.

La FI es una hipótesis docente. La coincidencia no demuestra una interferencia
real observada en Valencia ni describe un receptor aeronáutico concreto.

## Desarrollo y comprobación

Web estática sin dependencias JavaScript ni proceso de compilación. Servir esta
carpeta por HTTP; no abrir `index.html` mediante `file://`:

```sh
python -m http.server 8765
```

Visitar `http://localhost:8765`. GitHub Pages publica la rama `main`, carpeta raíz.

```sh
node --check app.js
python -m pip install -r python/requirements.txt
python python/comprobar_demo.py
python python/generar_audios.py
```

La generación de MP3 requiere FFmpeg. Los audios ya vienen incluidos. El modelo
y los WAV originales están en `python/`; la reproducción web usa únicamente las
herramientas de audio del navegador, sin depender de PortAudio/sounddevice.

## Modelo y niveles

El modo físico se calcula a 256 kHz mediante la envolvente compleja equivalente
de la FI. AM: índice 0,65. FM: desviación máxima ±75 kHz. Imagen de entrada: +12 dB
respecto a la portadora AM. Canal FI Butterworth de orden 6, ±6 kHz. Detector de
envolvente y audio a 150–3000 Hz. Rechazo previo al mezclador: 0/40 dB.

Se conserva una ganancia por pareja con/sin filtro; los modos tienen ganancias
distintas y sus volúmenes absolutos no deben interpretarse como potencias RF.
No se incluyen AGC, saturación, ruido térmico, preénfasis, estéreo o RDS.

En la web, los dos estados didácticos se calculan a partir de las mismas fuentes
decodificadas: `p + 0.9*r` y `p + 0.009*r`. Así se conserva el rechazo de amplitud
1/100 en la contribución imagen pese a la codificación MP3 de las fuentes. Los
estados físicos se precalculan en Python. La transición dura 40 ms.

## Fuentes y derechos

- [ENAIRE, AIP LEVC AD 2.18](https://aip.enaire.es/AIP/contenido_AIP/AD/AD2/LEVC/LE_AD_2_LEVC_es.html): Valencia APP, 120,100 MHz.
- [Directorio Radio MARCA Valencia](https://radios.com.es/6484-radio-marca-valencia.html): 98,7 FM.
- [Directo Marca Valencia, 26/10/2026](https://omny.fm/shows/radio-marca-valencia/directo-marca-valencia-26-10-2026): fragmento de 00:45 a 01:09; no es captura RF.
- Piloto: diálogo ficticio con voz TTS local Microsoft Pablo; no imita a una
  persona concreta y no es una comunicación aérea grabada.

El fragmento de Radio MARCA y sus versiones procesadas conservan los derechos
de sus titulares. Su inclusión en este ejemplo docente no otorga una licencia
abierta para redistribuir el programa. No es una web oficial de ENAIRE ni de Radio
MARCA. Las fuentes externas están identificadas también en la propia web.
