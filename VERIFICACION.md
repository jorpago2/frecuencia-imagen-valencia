# Verificación · 27/10/2026

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
