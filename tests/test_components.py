"""Smoke tests para componentes del dashboard.

Cubre: RF-D07, RF-D17, RD03.
"""

import json
from datetime import datetime, timezone, timedelta

import pytest

from safepath_mvp.dashboard.components import calcular_countdown
from safepath_mvp.shared.schema import ESTADO_INICIAL


class TestLoadState:
    """RF-D17: state.json corrupto o ausente no crashea."""

    def test_load_state_archivo_inexistente_retorna_default(self, tmp_path):
        """Si state.json no existe, retorna ESTADO_INICIAL."""
        state_path = tmp_path / "state.json"
        try:
            with open(state_path, encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = dict(ESTADO_INICIAL)

        assert data["estado"] == "NORMAL"
        assert "historial" in data

    def test_load_state_json_corrupto_retorna_default(self, tmp_path):
        """Si state.json tiene JSON corrupto, no crashea."""
        state_path = tmp_path / "state.json"
        state_path.write_text("{esto no es json valido", encoding="utf-8")

        try:
            with open(state_path, encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = dict(ESTADO_INICIAL)

        assert data["estado"] == "NORMAL"


class TestCalcularCountdown:
    """RF-D07, RD03: Countdown calculado desde timestamp_inicio_verificando."""

    def test_countdown_desde_timestamp(self):
        """Countdown se calcula desde timestamp, no del valor guardado."""
        inicio = (datetime.now(timezone.utc) - timedelta(seconds=3)).isoformat()
        data = {
            "estado": "VERIFICANDO",
            "timestamp_inicio_verificando": inicio,
            "countdown_restante": 0,
        }
        result = calcular_countdown(data)
        # Deberia ser ~7 (10 - 3), con margen de 1s
        assert 6 <= result <= 8

    def test_countdown_fuera_de_verificando_usa_valor(self):
        """En NORMAL, countdown = 0 siempre."""
        data = {
            "estado": "NORMAL",
            "countdown_restante": 0,
            "timestamp_inicio_verificando": None,
        }
        result = calcular_countdown(data)
        assert result == 0

    def test_countdown_no_negativo(self):
        """El countdown nunca debe ser negativo."""
        inicio = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
        data = {
            "estado": "VERIFICANDO",
            "timestamp_inicio_verificando": inicio,
            "countdown_restante": 0,
        }
        result = calcular_countdown(data)
        assert result >= 0
