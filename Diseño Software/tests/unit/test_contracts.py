"""Tests de los contratos de dominio: rechazo de NaN/inf, campos extra,
direcciones faltantes y framing del protocolo HIL."""

import pytest
from pydantic import ValidationError

from nsb.domain.contracts import (
    ApproachState,
    AppliedPhase,
    PlanSemaforico,
    TrafficState,
)
from nsb.domain.enums import (
    Direction,
    PhaseId,
    SignalColor,
    SignalGroup,
    SourceKind,
    WireType,
)
from nsb.domain.wire import (
    MAX_LINE_BYTES,
    WireDecodeError,
    WireEnvelope,
    decode,
    edad_segundos,
    encode,
)


def _estado_base(**overrides):
    base = dict(
        experiment_id="exp-test",
        intersection_id="int-01",
        source=SourceKind.MANUAL,
        seq=0,
        sim_time_s=0.0,
        control_interval_s=25.0,
        approaches={
            Direction.NS: ApproachState(queue_m=10.0, speed_kmh=20.0,
                                        flow_veh_min=5.0, num_vehicles=8,
                                        stopped_vehicles=3),
            Direction.EO: ApproachState(),
        },
    )
    base.update(overrides)
    return TrafficState(**base)


class TestTrafficState:
    def test_valido(self):
        st = _estado_base()
        assert st.seq == 0
        assert st.quality.valid is True

    @pytest.mark.parametrize("malo", [float("nan"), float("inf"), float("-inf")])
    def test_rechaza_no_finitos_en_approach(self, malo):
        with pytest.raises(ValidationError):
            _estado_base(approaches={
                Direction.NS: ApproachState(queue_m=malo),
                Direction.EO: ApproachState(),
            })

    @pytest.mark.parametrize("malo", [float("nan"), float("inf")])
    def test_rechaza_no_finitos_en_ev(self, malo):
        with pytest.raises(ValidationError):
            _estado_base(ev_ns=malo)

    def test_rechaza_direccion_faltante(self):
        with pytest.raises(ValidationError, match="ambas direcciones"):
            _estado_base(approaches={Direction.NS: ApproachState()})

    def test_rechaza_campo_extra(self):
        with pytest.raises(ValidationError):
            _estado_base(campo_inventado=1)

    def test_rechaza_seq_negativo(self):
        with pytest.raises(ValidationError):
            _estado_base(seq=-1)

    def test_ev_fuera_de_rango(self):
        with pytest.raises(ValidationError):
            _estado_base(ev_ns=1.5)


class TestPlanSemaforico:
    def test_valido(self):
        p = PlanSemaforico(t_verde_ns=30, t_verde_eo=40)
        assert p.t_ambar == 3.0 and p.t_todo_rojo == 2.0

    @pytest.mark.parametrize("malo", [float("nan"), float("inf"), 0, -5])
    def test_rechaza_verdes_invalidos(self, malo):
        with pytest.raises(ValidationError):
            PlanSemaforico(t_verde_ns=malo, t_verde_eo=30)

    def test_no_valida_limites_duros(self):
        # El contrato transporta; los límites los dictamina la capa de
        # seguridad (200 s pasa aquí y se recorta/rechaza en el TSC).
        p = PlanSemaforico(t_verde_ns=200, t_verde_eo=30)
        assert p.t_verde_ns == 200


class TestAppliedPhase:
    def _grupos(self):
        return {
            SignalGroup.NORTE: SignalColor.VERDE,
            SignalGroup.SUR: SignalColor.VERDE,
            SignalGroup.ESTE: SignalColor.ROJO,
            SignalGroup.OESTE: SignalColor.ROJO,
        }

    def test_valido(self):
        ap = AppliedPhase(phase_id=PhaseId.NS_VERDE, since_s=0.0,
                          signal_groups=self._grupos(),
                          plan_en_vigor=PlanSemaforico(t_verde_ns=30, t_verde_eo=30))
        assert ap.signal_groups[SignalGroup.NORTE] is SignalColor.VERDE

    def test_rechaza_grupo_faltante(self):
        grupos = self._grupos()
        del grupos[SignalGroup.OESTE]
        with pytest.raises(ValidationError, match="4 grupos"):
            AppliedPhase(phase_id=PhaseId.NS_VERDE, since_s=0.0,
                         signal_groups=grupos,
                         plan_en_vigor=PlanSemaforico(t_verde_ns=30, t_verde_eo=30))


class TestWire:
    def test_roundtrip(self):
        env = WireEnvelope(type=WireType.STATE, experiment_id="e1", seq=7,
                           payload={"k": 1})
        out = decode(encode(env))
        assert out.type is WireType.STATE
        assert out.seq == 7
        assert out.payload == {"k": 1}
        assert out.sent_at_iso  # encode lo rellena

    def test_linea_termina_en_newline(self):
        raw = encode(WireEnvelope(type=WireType.HEARTBEAT))
        assert raw.endswith(b"\n")
        assert raw.count(b"\n") == 1

    def test_decode_json_malformado(self):
        with pytest.raises(WireDecodeError):
            decode(b"esto no es json\n")

    def test_decode_no_objeto(self):
        with pytest.raises(WireDecodeError):
            decode(b"[1, 2, 3]\n")

    def test_decode_tipo_desconocido(self):
        with pytest.raises(WireDecodeError):
            decode(b'{"type": "tipo_inventado"}\n')

    def test_decode_linea_gigante(self):
        with pytest.raises(WireDecodeError, match="excede"):
            decode(b"x" * (MAX_LINE_BYTES + 1))

    def test_campo_extra_se_ignora(self):
        # Forward-compat: el envelope tolera campos futuros.
        out = decode(b'{"type": "bye", "campo_futuro": 1}\n')
        assert out.type is WireType.BYE

    def test_edad_segundos(self):
        env = WireEnvelope(type=WireType.STATE,
                           sent_at_iso="2026-07-05T10:00:00+00:00")
        edad = edad_segundos(env, ahora_iso="2026-07-05T10:00:05+00:00")
        assert edad == pytest.approx(5.0)

    def test_edad_sin_timestamp_es_none(self):
        assert edad_segundos(WireEnvelope(type=WireType.STATE)) is None

    def test_edad_timestamp_invalido_es_none(self):
        env = WireEnvelope(type=WireType.STATE, sent_at_iso="no-es-fecha")
        assert edad_segundos(env) is None
