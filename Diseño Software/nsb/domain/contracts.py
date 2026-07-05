"""Contratos de datos de NSB v2.1 (Pydantic v2).

Reglas de diseño:

- ``extra="forbid"`` en payloads científicos: un campo desconocido es un error,
  no algo que se ignora en silencio.
- ``allow_inf_nan=False`` en TODOS los floats: Pydantic v2 acepta NaN/inf por
  defecto, lo que dejaría sin efecto la validación de entradas no finitas que
  exige la spec (§11). Con esto, un NaN se rechaza en la frontera del sistema.
- Ningún contrato usa reloj de pared para decidir: ``wall_time_iso`` es solo
  informativo. El tiempo de decisión es ``sim_time_s`` (fuente: SUMO) o el
  reloj inyectado del nodo.
- Los ``schema_version`` permiten evolución del protocolo sin ambigüedad.
"""
from __future__ import annotations

from typing import Annotated, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from nsb.domain.enums import (
    Direction,
    Mode,
    PhaseId,
    SignalColor,
    SignalGroup,
    SourceKind,
    Verdict,
)

SCHEMA_STATE = "nsb.state/1"
SCHEMA_REC = "nsb.rec/1"
SCHEMA_DEC = "nsb.dec/1"

# Floats finitos (rechazan NaN/inf en validación)
FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
NonNegFloat = Annotated[float, Field(ge=0, allow_inf_nan=False)]
UnitFloat = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class ApproachState(_StrictModel):
    """Mediciones CRUDAS de una dirección (NS o EO).

    El ICV y el PI NO viajan aquí: se calculan en el nodo edge con el núcleo
    canónico — ese es precisamente el punto del edge computing.
    """
    queue_m: NonNegFloat = 0.0            # longitud de cola (metros)
    speed_kmh: NonNegFloat = 0.0          # velocidad promedio en movimiento
    flow_veh_min: NonNegFloat = 0.0       # flujo (veh/min)
    num_vehicles: Annotated[int, Field(ge=0)] = 0
    stopped_vehicles: Annotated[int, Field(ge=0)] = 0


class QualityFlags(_StrictModel):
    """Flags de calidad del sensado (relevantes para video de dron, §16)."""
    valid: bool = True                    # False => el nodo inhibe adaptación
    camera_moving: bool = False           # dron móvil: velocidades no confiables
    calibrated: bool = False              # hay calibración px/m confiable


class EvEvent(_StrictModel):
    """Evento de vehículo de emergencia detectado (spec §22)."""
    approach: Direction
    confidence: UnitFloat
    eta_s: Optional[NonNegFloat] = None
    track_id: Optional[str] = None


class TrafficState(_StrictModel):
    """Contrato canónico de estado de tráfico (spec §12).

    Producido por cualquier fuente (SUMO HIL, video, replay, manual) y
    consumido por el pipeline de decisión del nodo.
    """
    schema_version: str = SCHEMA_STATE
    experiment_id: str
    intersection_id: str
    source: SourceKind
    seq: Annotated[int, Field(ge=0)]      # monótono por experimento
    sim_time_s: Optional[NonNegFloat] = None   # None para video en vivo
    wall_time_iso: Optional[str] = None   # SOLO informativo, nunca decisorio
    control_interval_s: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    approaches: Dict[Direction, ApproachState]
    ev_ns: UnitFloat = 0.0                # entrada EV difusa dirección NS
    ev_eo: UnitFloat = 0.0
    ev_event: Optional[EvEvent] = None
    quality: QualityFlags = Field(default_factory=QualityFlags)
    metadata: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _ambas_direcciones(self) -> "TrafficState":
        faltan = {Direction.NS, Direction.EO} - set(self.approaches)
        if faltan:
            raise ValueError(
                f"TrafficState requiere ambas direcciones; faltan: "
                f"{sorted(d.value for d in faltan)}")
        return self


class PlanSemaforico(_StrictModel):
    """Plan de tiempos de un ciclo (lo que la tesis llama temporización).

    Los límites duros NO se validan aquí sino en la capa de seguridad
    (``nucleo.seguridad_semaforica``): este contrato transporta, la seguridad
    dictamina. Sí se exige finitud y positividad básica.
    """
    t_verde_ns: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    t_verde_eo: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    t_ambar: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 3.0
    t_todo_rojo: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 2.0


class ComputedIndicators(_StrictModel):
    """Indicadores calculados por el nodo (trazabilidad + golden master)."""
    icv_ns: UnitFloat
    pi_ns: UnitFloat
    ev_ns: UnitFloat
    icv_eo: UnitFloat
    pi_eo: UnitFloat
    ev_eo: UnitFloat


class PredictorInfo(_StrictModel):
    """Estado del predictor opcional (spec §21). CNN-LSTM no existe en el
    repo: por defecto todo es False y ``fallback_reason`` lo documenta."""
    enabled: bool = False
    available: bool = False
    used: bool = False
    fallback_reason: Optional[str] = "predictor_deshabilitado"
    inference_ms: Optional[NonNegFloat] = None


class RecommendationEnvelope(_StrictModel):
    """Salida del pipeline de decisión; entrada de la autoridad (TSC)."""
    schema_version: str = SCHEMA_REC
    experiment_id: str
    intersection_id: str
    seq: Annotated[int, Field(ge=0)]      # eco del TrafficState origen
    sim_time_s: Optional[NonNegFloat] = None
    recommendation_id: str                # f"{experiment_id}/{seq}"
    computed: ComputedIndicators
    plan: PlanSemaforico
    delta_pct_ns: Annotated[float, Field(allow_inf_nan=False)]
    delta_pct_eo: Annotated[float, Field(allow_inf_nan=False)]
    reglas_disparadas: List[str] = Field(default_factory=list)
    ev_preempt: Optional[Direction] = None
    predictor: PredictorInfo = Field(default_factory=PredictorInfo)
    processing_ms: NonNegFloat = 0.0
    mode: Mode


class AppliedPhase(_StrictModel):
    """Fase efectivamente aplicada por la autoridad + estado de los 12 LEDs."""
    phase_id: PhaseId
    since_s: FiniteFloat                  # en el reloj activo (sim o pared)
    signal_groups: Dict[SignalGroup, SignalColor]
    plan_en_vigor: PlanSemaforico

    @model_validator(mode="after")
    def _cuatro_grupos(self) -> "AppliedPhase":
        faltan = set(SignalGroup) - set(self.signal_groups)
        if faltan:
            raise ValueError(
                f"AppliedPhase requiere los 4 grupos de señal; faltan: "
                f"{sorted(g.value for g in faltan)}")
        return self


class DecisionEnvelope(_StrictModel):
    """Salida de la autoridad (spec §14): veredicto + fase aplicada."""
    schema_version: str = SCHEMA_DEC
    experiment_id: str
    seq: Annotated[int, Field(ge=0)]
    recommendation_id: Optional[str] = None   # None si la rec fue inválida
    verdict: Verdict
    reasons: List[str] = Field(default_factory=list)
    corrections: List[Dict] = Field(default_factory=list)  # de clamp_tiempos
    plan_aplicado: Optional[PlanSemaforico] = None  # None si REJECT sin cambio
    safe_mode: bool = False
    safe_mode_reason: Optional[str] = None
    applied_phase: AppliedPhase
    processing_ms: NonNegFloat = 0.0
    actuation_ms: NonNegFloat = 0.0
    mode: Mode
