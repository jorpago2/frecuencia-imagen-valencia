# Frecuencia imagen · Valencia

Laboratorio sonoro de CSAF para explorar un receptor superheterodino sintonizado
a Valencia APP. Incluye voz TTS ficticia de un piloto, un fragmento de Radio MARCA
Valencia, rechazo de imagen ajustable de 0 a 60 dB y espectros RF/FI vinculados.

**Web:** https://jorpago2.github.io/frecuencia-imagen-valencia/

## Uso

Pulsa **Reproducir**; mueve el deslizador (0–60 dB, pasos de 5 dB), alterna el filtro y compara los modos:

- **Superposición didáctica:** audios reconocibles; la contribución imagen baja
  los dB elegidos y la contribución del piloto conserva su nivel.
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
node --test test_audio.mjs
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
envolvente y audio a 150–3000 Hz. Rechazo previo al mezclador: 0–60 dB, pasos de 5 dB.

Se conserva una sola ganancia para los 13 niveles físicos; los modos tienen ganancias
distintas y sus volúmenes absolutos no deben interpretarse como potencias RF.
No se incluyen AGC, saturación, ruido térmico, preénfasis, estéreo o RDS.

En la web, el modo didáctico mezcla las mismas fuentes decodificadas con
`p + 0.9*10**(-R/20)*r`. El rechazo no altera la contribución del piloto. El modo
AM utiliza 13 audios recalculados antes del detector, uno por cada nivel del
selector; no se interpola entre dos resultados de la demodulación no lineal.
La transición dura 40 ms y todos los audios comparten el instante de reproducción.

## Espectros interactivos

El deslizador junto a los gráficos y el del reproductor están sincronizados.
Se muestran PSD medias de 24 segundos obtenidas de las señales AM y FM
modeladas, a 256 kHz, con Welch (8192 muestras, solapamiento 4096, sin quitar DC
para conservar la portadora). No son FFT de las voces ni medidas RF reales.

- Antes del mezclador: salida del preselector; ventanas alrededor de 98,7 MHz
  (±120 kHz) y 120,1 MHz (±6 kHz), con ruptura del eje y escalas distintas.
- Después del mezclador: producto diferencia alrededor de 10,7 MHz, antes del
  canal de FI; imagen conjugada/invertida y pérdida de 6,02 dB de cada producto
  de un multiplicador ideal. El modelo de audio compensa ese factor común.
- La zona sombreada marca ±6 kHz. Se puede ampliar la vista de FI a ±8 kHz.
- Las curvas comparten referencia: pico PSD de la AM antes de mezclar. Se resta
  R dB a la imagen sin renormalizar; la referencia gris muestra la imagen sin
  rechazo. Se agrupan 8 puntos FM por su máximo para aligerar la representación.
- La lectura +12−R dBc compara la potencia imagen con la portadora AM de entrada;
  la ordenada de los gráficos representa densidad espectral, no potencia integrada.

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
