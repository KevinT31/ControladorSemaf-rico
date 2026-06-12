# Tesis en LaTeX - versión visual mejorada

Proyecto generado a partir del documento Word original `[Tesis2][20213166][Tumbalobos][Kevin].docx`.

## Archivos

- `main.tex`: archivo principal en LaTeX.
- `media/`: carpeta con las 159 imágenes extraídas del documento original.
- `README.md`: instrucciones de compilación.

## Mejoras aplicadas

- Portada reconstruida y centrada con formato académico.
- Índice, índice de figuras e índice de tablas generados desde LaTeX.
- Capítulos, secciones y subsecciones con numeración automática profesional.
- Figuras centradas, escaladas al área útil de la página y con rótulos preservados.
- Etiquetas internas para figuras (`fig:N`) y tablas (`tbl:N`).
- Tablas con rótulo superior, espaciado mejorado y tamaño optimizado.
- Encabezados, numeración de página e hipervínculos internos configurados.
- Normalización de caracteres especiales para mejorar compatibilidad.

## Cómo compilar

Recomendado: PDFLaTeX.

```bash
pdflatex main.tex
pdflatex main.tex
pdflatex main.tex
```

En Overleaf:

1. Sube todo el contenido de esta carpeta.
2. Abre `main.tex`.
3. Selecciona `PDFLaTeX` como compilador.
4. Compila dos o tres veces para actualizar índices, lista de figuras y lista de tablas.

## Nota

El documento es pesado porque conserva 159 imágenes y muchas tablas largas. La compilación completa puede tardar varios minutos, especialmente en equipos lentos o en Overleaf gratuito.
