"""Tests de integracion para los endpoints Flask.

Cubre: RF-S01, S09, S11, S12, S13, S15, RNF-S03.
"""

import json
import threading


class TestEndpointsBasicos:
    """Endpoints del spec D1: /status, /ping, /cancel, /trigger, /reset."""

    def test_ping_retorna_alive(self, client):
        rv = client.get("/ping")
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data["status"] == "alive"

    def test_cancel_retorna_200(self, client):
        rv = client.get("/cancel")
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data["status"] == "cancelado"

    def test_reset_retorna_200(self, client):
        rv = client.get("/reset")
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data["status"] == "reseteado"
        assert data["estado"] == "NORMAL"

    def test_trigger_estado_valido(self, client):
        rv = client.get("/trigger?estado=ALERTA")
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data["estado"] == "ALERTA"

    def test_trigger_estado_invalido_retorna_400(self, client):
        rv = client.get("/trigger?estado=INVENTADO")
        assert rv.status_code == 400

    def test_trigger_case_insensitive(self, client):
        """Trigger debe funcionar con mayusculas/minusculas."""
        rv = client.get("/trigger?estado=alerta")
        assert rv.status_code == 200

    def test_status_retorna_200(self, client):
        """RF-S11: /status retorna 200 con estado completo."""
        rv = client.get("/status")
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert "estado" in data
        assert "aceleracion_actual" in data
        assert "historial" in data

    def test_alias_sensor_funciona(self, client):
        rv = client.post("/sensor", json={"ax": 1, "ay": 2, "az": 9.8})
        assert rv.status_code == 200

    def test_alias_state_funciona(self, client):
        rv = client.get("/state")
        assert rv.status_code == 200


class TestEndpointData:
    """RF-S01: POST /data con payloads de acelerometro."""

    def test_data_con_aceleracion_retorna_200(self, client):
        rv = client.post("/data", json={"ax": 1, "ay": 2, "az": 9.8})
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data["status"] == "ok"
        assert "accel" in data

    def test_data_sin_json_retorna_400(self, client):
        """RNF-S03: Payload no-JSON no crashea."""
        rv = client.post("/data", data="no es json")
        assert rv.status_code == 400

    def test_data_sin_aceleracion_retorna_400(self, client):
        """RF-S15: Datos irrelevantes no crashean."""
        rv = client.post("/data", json={"foo": "bar"})
        assert rv.status_code == 400

    def test_data_vacio_retorna_400(self, client):
        rv = client.post("/data", json={})
        assert rv.status_code == 400


class TestEndpointFlujo:
    """Flujo completo: POST data -> status -> cancel -> status."""

    def test_pipeline_completo_cancel(self, client):
        """RF-S09, S11: POST data -> VERIFICANDO -> cancel -> NORMAL."""
        rv = client.post("/data", json={"ax": 30, "ay": 0, "az": 9.8})
        assert rv.status_code == 200

        rv = client.get("/status")
        assert json.loads(rv.data)["estado"] == "VERIFICANDO"

        rv = client.get("/cancel")
        assert rv.status_code == 200

        rv = client.get("/status")
        assert json.loads(rv.data)["estado"] == "NORMAL"

    def test_pipeline_completo_reset(self, client):
        """RF-S13: POST data -> VERIFICANDO -> reset -> NORMAL."""
        client.post("/data", json={"ax": 30, "ay": 0, "az": 9.8})

        rv = client.get("/reset")
        assert rv.status_code == 200

        rv = client.get("/status")
        assert json.loads(rv.data)["estado"] == "NORMAL"

    def test_pipeline_trigger_reset(self, client):
        """RF-S12, S13: Forzar ALERTA -> reset -> NORMAL limpio."""
        client.get("/trigger?estado=ALERTA")

        rv = client.get("/status")
        assert json.loads(rv.data)["estado"] == "ALERTA"

        client.get("/reset")

        rv = client.get("/status")
        assert json.loads(rv.data)["estado"] == "NORMAL"
        assert json.loads(rv.data)["historial"] == []
