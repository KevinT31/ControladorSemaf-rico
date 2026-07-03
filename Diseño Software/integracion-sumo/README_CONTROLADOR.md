# Controlador canónico: `difuso_ia` (ControladorDifusoIA)

**Este es el controlador que representa el producto final de la tesis.** Los
experimentos multibaseline, la campaña estadística y (opcionalmente) el
backend usan ESTA implementación: `integracion-sumo/difuso_ia.py`.

```
sensado real (TraCI) ──> selección de fase acíclica (rotación + salto)
                          │        ▲ veto CNN-LSTM (cola predicha por fase,
                          │          con gating por régimen y margen de
                          │          confianza; fallback trazado)
                          ▼
                     duración difusa Mamdani Cap.6 (ICV + PI reales;
                     flujo = CRUCES por ventana, ContadorCruces)
                          ▼
                     transición segura (ámbar >= 3 s SIEMPRE — sintetizado
                     si el programa no trae fase 'y' —, todo-rojo del
                     programa respetado, verde en [10, 45] s)
                          ▼
                        SUMO
```

## Quién usa qué

| Consumidor | Ruta | Controlador |
|---|---|---|
| Benchmark multibaseline | `comparacion_multibaseline.ejecutar_estrategia(..., 'difuso_ia')` | `difuso_ia.ControladorDifusoIA` |
| Campaña estadística | `campania_difuso_ia.py` | idem (variantes guardia/off/sombra) |
| Backend (opcional) | `servidor-backend` con `CONTROL_ADAPTATIVO=difuso_ia` | idem |
| Plataforma `experimentos/` | `runner.py` (`fixed/fuzzy/fuzzy_predictive_ai`) | pipeline PREVIO por ejes NS/EO; se conserva para el predictor de ICV y de referencia histórica |
| `nucleo/controlador_difuso.py` (9 reglas) | legacy | NO usar en evaluación |

El motor difuso de la duración es único: `nucleo/controlador_difuso_capitulo6.py`.
La capa de límites duros es única: `nucleo/seguridad_semaforica.py` (LIMITES).

## Ejecutar

```bash
cd "Diseño Software/integracion-sumo"

# una corrida (IA encendida, modo guardia)
python -c "import comparacion_multibaseline as M; \
  print(M.ejecutar_estrategia(r'escenarios\lima-centro\comparacion.sumocfg', 7, 700, 'difuso_ia'))"

# IA APAGADA (mismo controlador, sin CNN-LSTM):    params_ia={'modo_ia': 'off'}
# MODO SOMBRA (predice y registra, jamás actúa):   params_ia={'modo_ia': 'sombra'}
# TRAZA POR INFERENCIA:                            params_ia={'log_ia': 'ruta.csv'}

# campaña completa reproducible (checkpoints por semilla; re-ejecuta también
# las líneas base con el MISMO aparato de medición corregido)
python campania_difuso_ia.py --alta 30 --media 10 --rerun-bases --sufijo v3
```

## Parámetros (PARAMS_DEFECTO en difuso_ia.py)

Seguridad (no negociables, se fuerzan en __init__): `t_verde_min=10`,
`t_verde_max=45` (⊂ [10,120] duros), `t_ambar>=3`, `t_todo_rojo>=2` si se
activa. Operación: `t_starve=45` + `starve_check_s=5` (anti-inanición
re-evaluada DURANTE el verde; cota real de espera ≈ t_starve + 5 + ámbar),
`gap_umbral_s=2`, `umbral_skip=1.0`. IA: `modo_ia`, `ia_veto`,
`ia_margen_veto` (confianza del veto), `ia_gate_sat=6`, `ia_gate_dens=4`
(gating por régimen MFD), `ia_ext=False` (descartada por ablación).

## Trazabilidad

- `log_ia` (CSV): filas `decision` (una por fase evaluada: cola actual vs
  predicha, demanda efectiva, veto, gate, sat_ema, dens_red, latencia de
  inferencia, duración aplicada, motivo de fallback) y filas `muestra`
  (cola real por fase cada 15 s) para evaluar post-hoc falsos vetos/permisos.
- `resumen_ia()`: predicciones, fallbacks POR MOTIVO, vetos (reales y en
  sombra), gate cerrado, latencia p50/p95, errores de paso, fallos de sensor,
  ámbar sintetizados, todo-rojos servidos, cortes por inanición.
- Cada corrida del benchmark registra: semilla, versión de SUMO, teleports,
  backlog de inserción, vehículos insertados; la campaña añade git hash y los
  parámetros efectivos de cada estrategia.

## Métricas (definiciones únicas)

- **Flujo**: vehículos que CRUZAN (salen del carril) por ventana móvil
  (`comparacion_sumo.ContadorCruces`). Nunca vehículos presentes.
- **ICV de control**: `nucleo/indice_congestion.CalculadorICV.calcular`
  (4 términos, pesos 0.35/0.25/0.25/0.15) con el flujo anterior.
- **ICV_red** de las tablas: PROXY de red de 2 términos (fracción detenida +
  caída de velocidad) — etiquetado como proxy, no confundir con el ICV de
  control.
- **Demora**: `demora_media_veh_s` = veh·s detenidos / vehículos insertados
  (denominador honesto). `demora_media_s` (por arribo) se conserva por
  continuidad histórica pero castiga doble el throughput bajo.
- **Validez**: `teleports` y `backlog` se reportan SIEMPRE; si difieren mucho
  entre estrategias, la comparación de demora/throughput está sesgada.

## Tests

```bash
cd "Diseño Software" && python -m pytest tests -q
```
26 tests: límites y modo seguro de `seguridad_semaforica`, síntesis de ámbar,
todo-rojo del programa, invariantes sobre SUMO real (nunca verde→rojo sin
ámbar; ámbar ≥ 3 s; verde ≥ 10 s; todo-rojo servido), flujo por cruces no
saturado, reproducibilidad por semilla, metadatos, y degradación de la IA
(modelo ausente, modo off, normalización desalineada ⇒ IA desactivada con
error explícito).
