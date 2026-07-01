# CONTINUAR_CLAUDE.md — Estado de la tesis (mainV4)

_Última actualización: 2026-07-01 (sesión pulido Turnitin — 2ª pasada: fuente, planos, URLs, μ, imágenes)_

## Sesión 2026-07-01 (2ª pasada) — Fuente, planos restaurados, URLs, ecuación, imágenes

Continuación del pulido. Peticiones: separar «Fuente:» de la leyenda; repaso visual (gráficos
descuadrados, textos/tablas recortadas); imágenes en HD; corregir imágenes con texto que no coincide
con la tesis; y **restaurar planos de anexos que una pasada previa había eliminado**.

- **«Fuente:» separada:** `\fuente` pasó de `\vspace{-2pt}` a `\vspace{3pt}` (antes quedaba pegada a la
  leyenda tras el cambio a bloque). Verificado.
- **Planos de Anexos RESTAURADOS (regresión corregida):** V4 había reemplazado los 21 planos del autor por
  un párrafo («se conservan como CAD digital»). Se restauraron en `cierre.tex` → ANEXO D, agrupados por
  sección igual que en `main.tex` (V1): D.1 vista general (image3); D.2 Sección E rack DIN/rieles (138,94,
  62,137,32,121,59); D.3 Sección G gabinete (34,23,142); D.4 Sección M mecanismo cámara (135,98,38,119);
  D.5 Sección V zócalo (123,63,92,4); D.6 Sección P poste (129); D.7 Sección Z zapata (106). Con
  `\captionsetup[figure]{list=no}` para no saturar el índice. **NO borrar estos planos de nuevo.**
- **URLs de bibliografía (texto recortado):** se salían del margen y se truncaban porque estaban en
  `\href{}{\ul{}}` (soul no corta línea). Script convirtió las **89** a `\url{}` (xurl ya cargado → corta
  en cualquier carácter y sigue clicable). `bibliografia_items.tex.bak` = respaldo.
- **Ecuación μ (pág. 142) recortada:** μ_Bajo/μ_Medio/μ_Alto estaban lado a lado con `\;\;`; μ_Alto se
  cortaba. Reescritas en `aligned` apiladas y alineadas al `=` (cap6, subsec. Variables lingüísticas).
- **Imágenes con texto incongruente corregidas (edición raster PIL, Arial):**
  `media/image66.png` (fig 3.10): «INA219, SHT31»→«WCS1600, DS18B20» y «Servomotores»→«Motor paso a paso».
  `media/image33.png` (fig 3.11): «Procesar con Apache Spark»→«Analizar datos en la nube»; «Integrar datos
  API Google Maps»→«Integrar datos de tráfico». Originales respaldados en scratchpad (`*_ORIG.png`) y en
  git. Quedó SIN tocar «Enviar Datos a central vía HTTP/HTTPS» (ambiguo).
- **Tablas apaisadas OK:** las 6 `landscape` (Tabla 3.3, matriz morfológica, evaluación, trazabilidad,
  selección electrónica, modelo de amenazas) se ven completas; los avisos «Annotation out of page
  boundary» son solo rectángulos de hyperlink (cosmético), no cortes.
- **Compila EXIT=0, 202 pág (191→202: +11 por los planos), 0 refs/citas sin resolver.** `mainV4.pdf`
  (raíz) sincronizado. **Sin commitear.**
- **PENDIENTE HD (no se puede sin reexportar):** 12 imágenes con DPI de impresión <130 (renders CAD de
  cap5 y algún diagrama): image130,61,13,96,109,90,83,134,149,42,111,73. No se puede añadir detalle real
  por software; el autor debe **reexportar desde el CAD/origen a mayor resolución**. Los diagramas de flujo
  (image66/33) también son de baja resolución; lo ideal sería rehacerlos vectoriales (TikZ) — ofrecido.

## Sesión 2026-07-01 — Pulido para Turnitin (figuras que se salían + sangría "tab")

Petición del usuario: perfeccionar para Turnitin, evitar fotos demasiado grandes (en especial las
**verticales/largas** cuyo rótulo «Figura X.Y» se salía de la hoja), ubicar bien todo y **quitar el
"tab"** (sangría) del inicio de los párrafos.

- **Diagnóstico con datos (scratchpad):** 9 figuras superaban el 78 % de la altura de página; 5 pasaban
  del 100 % (la imagen sola más alta que la hoja → leyenda perdida). Caso peor: la **Figura 3.10**
  apilaba DOS imágenes verticales (`image66` 163 % + `image33` 124 %) en un mismo `figure` (~287 % de
  página): `image66` desbordaba el margen inferior e `image33` **y la leyenda desaparecían por completo**.
- **Fix 1 — tope de altura global** en el preámbulo de `mainV4.tex`: se redefine `\includegraphics` para
  añadir `height=0.80\textheight,keepaspectratio`. Con keepaspectratio solo encoge las verticales; las
  demás no cambian. Garantiza que imagen + leyenda quepan siempre en la página.
- **Fix 2 — partir la Figura 3.10** en `cap3_diseno_conceptual.tex`: ahora son dos figuras independientes,
  `fig:flujo-completo` (parte 1 de 2) y `fig:flujo-completo-b` (parte 2 de 2), cada una en su página con
  leyenda visible; se actualizó la referencia del texto a «Las Figuras 3.10 y 3.11…». (Las figuras
  siguientes corrieron +1 en la numeración, auto-actualizado.)
- **Fix 3 — párrafos en bloque:** `\parindent` 1.25cm → **0pt** y `\parskip` 0.25em → **8pt** (separación
  vertical clara, sin "tab" al inicio). `\parskip=0pt` forzado en la portada para no descuadrarla, y en
  `\fuente` para que la línea «Fuente:» quede pegada a su leyenda.
- **Compila EXIT=0, 191 pág (antes 187; +4 por el bloque y la figura partida), 0 refs/citas sin resolver,
  0 overfull hbox.** `mainV4.pdf` (raíz) sincronizado. Verificación visual OK (portada, texto en bloque,
  Fig. 3.10/3.11 partidas, Fig. 5.15 vertical). **Sin commitear** (lo decide el usuario).
- **Nota (no era el encargo):** los rótulos DENTRO del diagrama de flujo (`image66/image33`) mencionan
  INA219/SHT31, Apache Spark, API Google Maps y servomotores, que no coinciden con el texto (WCS1600/
  DS18B20, MQTT/Azure). Está "quemado" en el PNG; requeriría reexportar el diagrama fuente.

## Sesión 2026-06-30 — Integridad de citas (tarea retomada "a la mitad")

Se cerró la limpieza de consistencia post-revisión. Los FLAGS (a) UPS y (b) sensores ya estaban
reconciliados; el pendiente real era **FLAG (c) citas sin entrada en la bibliografía**, que resultó
ser más amplio de lo anotado. Un audit automatizado (`scratchpad/cite_audit.py`, cruza cada cita
autor-año del texto contra `bibliografia_items.tex`) detectó **17 citas colgadas/erróneas**; se
resolvieron **todas** → **0 colgadas de 29**.

- **14 entradas reales añadidas** + se reemplazó el huérfano MTC (s.f.) por MTC (2020). Fuentes
  verificadas por web (sin fabricar nada): MML = Decreto de Alcaldía 13-2022; ATU = RD
  D-000008-2024-ATU/DIR; MTC = RD 017-2020-MTC/18 (Manual ITS); Koukol et al. = 2015 (Math. Prob.
  Eng. 979160 — de ahí salen el 74 % y FUSICO).
- **Citas no verificables corregidas a fuentes canónicas reales** (cap2 estado del arte): MOG2 →
  Zivkovic 2004; HOG → Dalal & Triggs **2005**; Haar → Viola & Jones 2001; YOLO → Redmon et al. 2016;
  DeepSORT → Wojke et al. **2017**; debilidad de Webster en saturación → Webster 1958; MQTT →
  Banks & Gupta 2014 (OASIS). Sacyr 2021 → s.f. Materiales 5052-H32: Atlas/MatWeb/ThomasNet/Wevolver.
- **Compila EXIT=0, 187 pág, 0 referencias/citas sin resolver, 0 errores.** `mainV4.pdf` (raíz)
  sincronizado. Sin commitear (lo decide el usuario).

_Anterior:_

## Qué se hizo en esta sesión

1. **Diagnóstico del estado heredado.** Una sesión previa ya había generado `mainV3.tex` +
   `build_v3/` (compilado a `build_v3/out/mainV3.pdf`, 173 pág) e iniciado una iteración `mainV4.tex` +
   `build_v4/` con el front matter corregido (numeración romana del RESUMEN ya bien ubicada) y el
   `cap2_estado_arte.tex` ampliado. **No se rehízo ese trabajo.**
2. **Corrección de rutas en `build_v4/cierre.tex`:** apuntaba a `build_v3/bibliografia_items` y
   `build_v3/anexo_componentes`; ahora apunta correctamente a `build_v4/...`.
3. **Compilación y verificación de `mainV4.tex`** con Tectonic (`tools/tectonic/tectonic.exe`).
   Resultado: **PDF de 176 páginas, exit 0, 0 referencias sin resolver, 0 citas sin resolver,
   0 errores fatales, 0 placeholders** (`[SUMO]`, `[COMPLETAR]`, etc.).
4. **Verificación visual** de páginas clave (renderizadas con PyMuPDF): ÍNDICE DE CONTENIDO con líderes
   de puntos y numeración romana/arábiga correcta; ÍNDICE DE FIGURAS/TABLAS **agrupados por "CAPÍTULO N"**
   (igual que la tesis de referencia); tabla de resultados SUMO A-vs-B real en el Cap. 7. Todo correcto.
5. **PDF copiado a la raíz** como `mainV4.pdf` para fácil acceso.

## Archivos modificados / creados en esta sesión

- `build_v4/cierre.tex` — corregidas 2 rutas de `\input` (build_v3 → build_v4).
- `mainV4.pdf` (raíz) — copia del PDF compilado (`build_v4/out/mainV4.pdf`).
- `build_v4/out/` — artefactos de compilación (mainV4.pdf, .log, .aux, .toc, .lof, .lot).
- `CONTINUAR_CLAUDE.md` — este archivo.
- Memoria del asistente actualizada (`mainv3-tesis-estado`).

## Estado actual del documento (mainV4)

- **Versión vigente:** `mainV4.tex` → `\input{build_v4/...}` (introduccion, cap1..cap7, cierre;
  cierre incluye `bibliografia_items` y `anexo_componentes`).
- Front matter PUCP completo; Estado del Arte en 5 secciones por subsistema con tablas comparativas;
  RL/CNN-LSTM como "trabajo futuro"; Cap. 7 con **resultados SUMO reales** (control fijo vs difuso,
  lima-centro, 3 semillas: ICV −2.0 %, demora −5.4 %, cola −3.6 %, velocidad +1.4 %; la semilla 2 no
  mejora, reportado con honestidad); matriz de cumplimiento sin celdas vacías.
- **Reparto de páginas:** front matter i–viii; CAP. 1 en pág. 3; CAP. 7 en PDF 142; CONCLUSIONES PDF 154;
  BIBLIOGRAFÍA PDF 157; ANEXOS PDF 164; total 176.

## Qué quedó pendiente

1. **(Principal) Recorte a ≤110 páginas antes de los anexos.** Hoy el cuerpo + bibliografía ≈ 158 págs.
   Hay que mover detalle fino a anexos y condensar (costos, descripciones de componentes, estructura de
   funciones) **sin perder evidencia ni rigor**. El usuario pidió hacer esto en una segunda pasada.
2. **Datos del Informe de Similitud** (placeholders de línea para %, DNI, ORCID y fecha) — completar con
   los datos reales cuando estén disponibles.
3. **Cosmético:** algunas tablas en `landscape` muy anchas generan avisos «Annotation out of page
   boundary» (hyperlinks que se salen del margen) y 58 overfull hbox. No afecta la lectura; opcional pulir.

## Comandos para verificar

```bash
cd "C:/Users/P5PractTI/Desktop/OverLeaf_Local/workspace/tesis_kevin_latex_bien_formateado"
TECT="C:/Users/P5PractTI/Desktop/OverLeaf_Local/tools/tectonic/tectonic.exe"
# Compilar (genera build_v4/out/mainV4.pdf):
"$TECT" -X compile mainV4.tex --outdir build_v4/out --keep-logs --keep-intermediates
# Verificar páginas:
python -c "from pypdf import PdfReader;print(len(PdfReader('build_v4/out/mainV4.pdf').pages),'páginas')"
# Verificar que NO haya refs sin resolver ni placeholders:
grep -cE "Warning: (Reference|Citation) .* undefined" build_v4/out/mainV4.log
grep -rnoE "\[(SUMO|COMPLETAR|CALCULAR|VALIDAR|EVALUAR)[^]]*\]" build_v4/*.tex
```
En Overleaf: subir `mainV4.tex` + carpeta `build_v4/` + `media/` y compilar con pdfLaTeX (el `\%` ya está
parcheado para no romper en modo matemático).

## Prompt sugerido para continuar

> Continúa con la tesis en `workspace/tesis_kevin_latex_bien_formateado/`. La versión vigente es
> `mainV4.tex` (modular, `build_v4/`), ya compila limpio (176 pág, sin placeholders). Ahora haz la
> **segunda pasada: reducir a ≤110 páginas antes de los anexos**, moviendo el detalle fino a anexos y
> condensando (costos, descripciones de componentes, estructura de funciones, análisis largos), **sin
> eliminar la evidencia real (resultados SUMO, ICV, FEM) ni romper referencias**. Compila con Tectonic
> (`tools/tectonic/tectonic.exe -X compile mainV4.tex --outdir build_v4/out`) y verifica páginas y que
> sigan en 0 las referencias sin resolver. No descartes contenido sin reubicarlo.
