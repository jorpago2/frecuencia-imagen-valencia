# Verificación

## Deslizador y espectros · 28/10/2026

- `node --check app.js`, `node --check spectra.js` y `node --test test_audio.mjs`:
  correctos; tres pruebas automatizadas sobre los trece niveles 0–60 dB.
- Ganancia del piloto constante en la mezcla didáctica, rechazo de amplitud
  `10^(-R/20)` y fuentes aisladas independientes del filtro.
- Trece audios AM calculados con rechazo previo al detector, una misma ganancia
  en todos los niveles y picos inferiores a 0,851 antes de la codificación MP3.
- PSD AM/FM generadas mediante Welch, conservando la portadora DC; verificados
  el desplazamiento de R dB, inversión de la imagen y pérdida de mezcla 6,0206 dB.
- Navegador local: reproducción AM, cambios de 0/20/60 dB, sincronización entre
  deslizadores, bypass y zoom de FI; contador avanza sin reiniciar la escucha.
- Curva AM RF inalterada al mover el deslizador; curva imagen cambia y vuelve
  exactamente a su trazado original al desactivar el filtro.
- Revisión visual de las curvas RF/FI, incluida una pantalla móvil de 390 px
  sin desbordamiento horizontal. Consola sin advertencias o errores.

## Versión inicial · 27/10/2026

- Sintaxis JavaScript: `node --check app.js`, correcta.
- Modelo Python: `python python/comprobar_demo.py`, correcto. Rechazo didáctico
  de 40,0 dB; recuperación de tono AM de 700 Hz y amplitud relativa 1,0011.
- Navegador: reproducción, conmutación del filtro, selección de fuente, cambio
  de modo y pausa probados en la vista previa; sin errores de consola.
- Escucha humana: el usuario confirmó que el audio de la vista previa se oye.
- Diseño: revisión visual en el navegador; comprobación de ancho móvil de
  390 px sin desbordamiento horizontal.
- Publicación: HTML, JavaScript, CSS y los cuatro MP3 devuelven HTTP 200 desde
  GitHub Pages y coinciden por SHA-256 con los archivos locales publicados.
- Web pública: reproducción y filtro comprobados en la URL desplegada,
  contador avanzando y sin errores de consola.

La comprobación auditiva no es una validación de un receptor RF físico. No se
ha hecho una revisión exhaustiva de todos los navegadores o dispositivos.
