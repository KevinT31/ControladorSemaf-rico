# OverLeaf Local

Editor LaTeX local tipo Overleaf: arbol de archivos, editor con resaltado,
subida/importacion de ZIP y preview PDF en el navegador.

## Uso rapido

```powershell
npm install
npm run install-tectonic
npm start
```

Abre la URL que imprime la consola, normalmente:

```text
http://127.0.0.1:3042
```

Tus archivos LaTeX van dentro de `workspace/`. Puedes pegar ahi un proyecto
grande, subir archivos desde la interfaz o importar un `.zip` exportado de
Overleaf.

## Compiladores

La app usa el primer compilador disponible en este orden:

```text
tools/tectonic/tectonic.exe
tectonic
latexmk
lualatex
xelatex
pdflatex
```

Si ya tienes MiKTeX o TeX Live instalado, tambien funcionara. Si no, el comando
`npm run install-tectonic` descarga Tectonic de forma portatil en `tools/`.

## Limites locales

No hay limite de proyecto impuesto por Overleaf. El limite real sera tu disco,
RAM y el compilador LaTeX. Para proyectos enormes, deja los archivos pesados en
`workspace/` y compila desde el navegador.
