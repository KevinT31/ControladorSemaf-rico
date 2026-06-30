# Informe de revisión de `mainV2.tex`

## A. Diagnóstico breve

### Fortalezas

- El documento ya contiene diseño electrónico, mecánico, control difuso, nube, ciberseguridad, SUMO y costos.
- Existe una arquitectura híbrida local–nube y se reconoce al controlador semafórico como autoridad final.
- Hay cálculos, CAD, esquemas, código de apoyo y una plataforma de simulación que pueden convertirse en evidencia defendible.
- El estado del arte cubre los ejes tecnológicos relevantes y ya incluye una síntesis de criterios adoptados.

### Debilidades detectadas

- La lista original de exigencias no tenía códigos, criterios de aceptación ni método de verificación.
- La solución aparecía como una suma de tecnologías y no como resultado explícito de una matriz morfológica y una evaluación ponderada.
- Los objetivos no cubrían todos los entregables ni estaban vinculados con evidencia concreta.
- La validación describía la plataforma, pero no cerraba una comparación reproducible con tabla de resultados, réplicas, semillas y condiciones comunes.
- Nube, RL y CNN–LSTM ocupaban una posición excesivamente central respecto del núcleo realmente validable.
- Las conclusiones afirmaban mejoras sin mostrar en el texto una tabla cuantitativa completa.
- Se mezclaban actuación semafórica, recomendación y autoridad final, lo que podía generar preguntas de seguridad funcional.

### Riesgos ante jurado

- “¿Dónde está la evidencia de que mejora el tráfico y bajo qué demanda?”
- “¿Qué ocurre si se cae la nube, falla la cámara o llega un parámetro malicioso?”
- “¿El Raspberry Pi controla directamente las luces?”
- “¿Por qué eligió cámara, control difuso y Azure frente a otras alternativas?”
- “¿Qué parte fue validada y qué parte es solo propuesta?”
- “¿Los valores de tiempos, IP, autonomía, costos y desempeño fueron calculados, medidos o asumidos?”
- “¿Por qué se incluyen RL y CNN–LSTM si no son necesarios para cumplir el objetivo?”

## B. Plan de mejora aplicado por capítulos

| Capítulo | Problema principal | Mejora incorporada |
|---|---|---|
| Resumen/Introducción | Alcance amplio y resultado poco delimitado | Resumen centrado en módulo complementario, simulación y límites |
| 1 | Problema urbano más que problema de ingeniería | Cadena sensado–edge–nube–seguridad y necesidad técnica concreta |
| 1 | Objetivos incompletos | Objetivo general verificable y 10 objetivos con entregables |
| 1 | Alcance defensivo | Inclusiones, exclusiones y etapas posteriores de madurez |
| 2 | Tecnologías desconectadas | Criterios adoptados y separación entre núcleo y futuro |
| 3 | Exigencias sin verificación | Tabla codificada con criterio, justificación, prioridad y prueba |
| 3 | Falta de selección justificable | Matriz morfológica, cuatro conceptos y evaluación ponderada |
| 3 | Frontera ambigua | Caja negra formal y arquitectura edge–nube–controlador |
| 3 | Falta de cierre | Matriz de trazabilidad de objetivos |
| 4 | Selección por componente | Tabla función–alternativas–criterio–falla–requerimiento |
| 5 | Mecánica como añadido | Requerimientos mecánicos y métodos de verificación |
| 6 | Exceso de IA | Difuso como núcleo; RL/CNN–LSTM como experimental/futuro |
| 6 | Fallos no sistematizados | Modos normal, nube, desconectado, sensado degradado y manual |
| 6 | Seguridad genérica | Modelo de 10 amenazas con mitigación y evidencia |
| 7 | Plataforma confundida con validación | Protocolo A–E, parámetros, tabla SUMO y caso de desconexión |
| 7 | Sin cierre de requisitos | Matriz de cumplimiento |
| Conclusiones | Genéricas y sobreafirmadas | Diez conclusiones vinculadas con objetivos y nueve recomendaciones |

## E. Figuras recomendadas

Las tres primeras ya fueron incorporadas como diagramas esquemáticos en LaTeX. Conviene reemplazarlas luego por figuras vectoriales definitivas:

1. Caja negra con entradas, salidas y frontera del módulo.
2. Estructura funcional por nueve dominios.
3. Arquitectura edge–nube–controlador con frontera de seguridad.
4. Flujo de datos: cámara → variables → ICV → difuso → validación → recomendación.
5. Diagrama de estados y modos degradados.
6. Zonas de confianza de ciberseguridad y flujos autenticados.
7. Flujo del experimento SUMO y exportación de métricas.
8. Gráficos A vs. B con barras/boxplots e intervalos de confianza.

## F. Checklist para defensa

### Evidencia que debe estar lista

- Archivos `.sumocfg`, rutas, demanda, semillas y versión de SUMO.
- CSV de cada réplica para control fijo y control difuso.
- Tabla 7.1 completa y gráficos con unidades.
- Prueba de desconexión y retorno al modo local/base.
- Barrido de entradas del difuso que demuestre límites de fase.
- Cálculo final de potencia y autonomía.
- Factor de seguridad, desplazamiento y temperatura máxima del diseño.
- Matriz de amenazas y demostración de rechazo de parámetros inválidos.
- CAPEX/OPEX actualizado con fecha, fuente y supuestos.

### Preguntas que debe poder responder

- Qué variable mide realmente la cámara y cómo se valida.
- Cómo se calcula y calibra el ICV.
- Por qué el difuso es preferible para el núcleo de tesis.
- Qué interfaz existe con el controlador y quién decide finalmente.
- Qué ocurre ante falla de cámara, nube, energía o credenciales.
- Qué parte fue simulada, diseñada, implementada en software o solo propuesta.
- Bajo qué condiciones una mejora porcentual es válida.
- Qué falta para pasar de tesis a prototipo y de prototipo a piloto vial.

### Límites que deben defenderse

- No se fabricó ni instaló un sistema en vía pública.
- No se certificó seguridad funcional ni ciberseguridad.
- No se validó compatibilidad con todas las marcas de controladores.
- RL y CNN–LSTM no forman parte del cumplimiento mínimo del objetivo general.
- Los resultados SUMO no equivalen a desempeño en tráfico real sin calibración y piloto.
