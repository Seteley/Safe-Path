"""Tests para validacion del contrato state.json.

Verifica que ESTADO_INICIAL y ESTADOS_VALIDOS cumplen con el spec D1.
"""

from safepath_mvp.shared.schema import (
    ESTADO_INICIAL,
    ESTADOS_VALIDOS,
    CAMPOS_HISTORIAL,
    FLAGS_HISTORIAL,
    COLOR_NORMAL,
    COLOR_VERIFICANDO,
    COLOR_ALERTA,
    COLOR_RESUELTO,
)


class TestEstadoInicial:
    """ESTADO_INICIAL debe reflejar el modelo de datos del spec D1."""

    def test_estado_inicial_es_normal(self):
        assert ESTADO_INICIAL["estado"] == "NORMAL"

    def test_estado_inicial_tiene_todos_los_campos(self):
        campos = {
            "estado",
            "aceleracion_actual",
            "countdown_restante",
            "timestamp_cambio",
            "timestamp_inicio_verificando",
            "historial",
            "usuaria",
            "contacto",
            "lat",
            "lon",
            "direccion",
            "umbral",
        }
        assert set(ESTADO_INICIAL.keys()) == campos

    def test_historial_inicial_vacio(self):
        assert ESTADO_INICIAL["historial"] == []

    def test_aceleracion_inicial_es_cero(self):
        assert ESTADO_INICIAL["aceleracion_actual"] == 0.0

    def test_countdown_inicial_es_cero(self):
        assert ESTADO_INICIAL["countdown_restante"] == 0


class TestEstadosValidos:
    """ESTADOS_VALIDOS debe contener los 4 estados del spec."""

    def test_4_estados_definidos(self):
        assert ESTADOS_VALIDOS == {"NORMAL", "VERIFICANDO", "ALERTA", "RESUELTO"}


class TestCamposHistorial:
    """CAMPOS_HISTORIAL debe coincidir con el spec."""

    def test_campos_esperados_en_historial(self):
        assert CAMPOS_HISTORIAL == {"estado", "timestamp", "aceleracion"}

    def test_flags_esperados(self):
        assert FLAGS_HISTORIAL == {"cancelado", "escalado", "forzado"}


class TestColores:
    """La paleta SafeCorp debe estar definida."""

    def test_colores_definidos(self):
        assert COLOR_NORMAL == "#22c55e"
        assert COLOR_VERIFICANDO == "#eab308"
        assert COLOR_ALERTA == "#ef4444"
        assert COLOR_RESUELTO == "#6b7280"
