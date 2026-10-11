"""Regresiones del adaptador de tracks del núcleo científico."""

import pytest

from nucleo.estado_local import EstadoLocalInterseccion


def _track(track_id, centroide, velocidad_xy=None):
    return {
        "id": track_id,
        "centroide": centroide,
        "bbox": [0, 0, 10, 10],
        "velocidad_promedio": 20.0,
        "velocidad_xy": velocidad_xy,
        "clase": "car",
        "confianza": 0.9,
    }


def test_track_sin_vector_usa_desplazamiento_del_centroide():
    estado = EstadoLocalInterseccion("test")
    estado.actualizar_desde_tracks([_track(7, (10.0, 10.0))], 2.0, cam_mask=0)
    assert estado.Vavg.tolist() == [0.0, 0.0, 0.0, 0.0]

    estado.actualizar_desde_tracks([_track(7, (14.0, 10.0))], 2.0, cam_mask=0)
    assert estado.Vavg[2] == pytest.approx(20.0)  # E
    assert estado.Vavg[3] == 0.0


def test_track_sin_movimiento_no_se_asigna_arbitrariamente_al_sur():
    estado = EstadoLocalInterseccion("test")
    estado.actualizar_desde_tracks(
        [_track(7, (10.0, 10.0), velocidad_xy=(0.0, 0.0))],
        2.0,
        cam_mask=1,
    )
    assert estado.SC.tolist() == [0.0, 0.0, 0.0, 0.0]


@pytest.mark.parametrize("escala", [0, -1, float("nan"), float("inf"), True])
def test_escala_de_pixeles_debe_ser_finita_y_positiva(escala):
    estado = EstadoLocalInterseccion("test")
    with pytest.raises(ValueError, match="pixeles_por_metro"):
        estado.actualizar_desde_tracks([], escala)
