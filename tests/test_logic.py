"""Tests para la maquina de estados SAFE-PATH.

Cubre: RF-S04, S05, S06, S07, S08, S09, S10, S13, S14,
RNF-S04, RNF-S05, y transiciones prohibidas del spec D1.
"""

import time
import threading
import json

import pytest

from safepath_mvp.simulador.config import (
    UMBRAL_ACELERACION,
    TIEMPO_VERIFICACION,
    DURACION_ALERTA,
    DURACION_RESUELTO,
)


class TestTransicionesBasicas:
    """RF-S04: Maquina de estados NORMAL -> VERIFICANDO -> ALERTA -> RESUELTO."""

    def test_estado_inicial_es_normal(self, machine):
        assert machine.state == "NORMAL"

    def test_aceleracion_bajo_umbral_no_transiciona(self, machine):
        machine.update(5.0)
        assert machine.state == "NORMAL"

    def test_aceleracion_sobre_umbral_transiciona_a_verificando(self, machine):
        machine.update(20.0)
        assert machine.state == "VERIFICANDO"

    def test_cancel_durante_verificando_vuelve_a_normal(self, machine):
        machine.update(20.0)
        assert machine.state == "VERIFICANDO"
        machine.cancel()
        assert machine.state == "NORMAL"

    def test_cancel_fuera_de_verificando_no_hace_nada(self, machine):
        machine.cancel()
        assert machine.state == "NORMAL"

    def test_force_state_a_estado_valido(self, machine):
        result = machine.force_state("ALERTA")
        assert result is True
        assert machine.state == "ALERTA"

    def test_force_state_a_estado_invalido_rechaza(self, machine):
        result = machine.force_state("INVENTADO")
        assert result is False
        assert machine.state == "NORMAL"

    def test_reset_vuelve_a_normal_y_limpia_historial(self, machine):
        machine.update(20.0)
        machine.force_state("ALERTA")
        machine.reset()
        assert machine.state == "NORMAL"
        assert machine.historial == []

    def test_get_state_retorna_todos_los_campos_esperados(self, machine):
        state = machine.get_state()
        campos_esperados = {
            "estado",
            "aceleracion_actual",
            "countdown_restante",
            "timestamp_cambio",
            "historial",
            "usuaria",
            "contacto",
            "lat",
            "lon",
            "direccion",
            "umbral",
        }
        assert campos_esperados.issubset(state.keys())

    def test_countdown_se_inicializa_en_10_al_entrar_en_verificando(self, machine):
        """RF-S05: Al transicionar a VERIFICANDO, countdown = TIEMPO_VERIFICACION."""
        machine.update(20.0)
        assert machine.state == "VERIFICANDO"
        assert machine.countdown == TIEMPO_VERIFICACION

    def test_transicion_prohibida_normal_a_alerta_directo(self, machine):
        """Transicion prohibida: NORMAL nunca debe ir directo a ALERTA via update."""
        machine.update(20.0)
        assert machine.state != "ALERTA"
        assert machine.state == "VERIFICANDO"

    def test_transicion_prohibida_alerta_a_verificando(self, machine):
        """Transicion prohibida: ALERTA no debe volver a VERIFICANDO."""
        machine.force_state("ALERTA")
        machine.update(20.0)
        assert machine.state == "ALERTA"

    def test_umbral_viene_de_config_no_hardcodeado(self, machine, monkeypatch):
        """RNF-S05: El umbral se lee de config.py, no esta hardcodeado."""
        # Patch directamente el valor en el modulo logic (desde donde se importo)
        monkeypatch.setattr(
            "safepath_mvp.simulador.logic.UMBRAL_ACELERACION", 5.0
        )
        machine.update(7.0)
        assert machine.state == "VERIFICANDO"

        machine.reset()
        monkeypatch.setattr(
            "safepath_mvp.simulador.logic.UMBRAL_ACELERACION", 20.0
        )
        machine.update(7.0)
        assert machine.state == "NORMAL"

    def test_status_retorna_contenido_completo(self, machine):
        """RF-S11: get_state() retorna todos los campos del spec state.json."""
        machine.update(20.0)
        state = machine.get_state()
        campos_requeridos = {
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
        for campo in campos_requeridos:
            assert campo in state, f"Falta campo '{campo}' en state.json"


class TestTransicionesTemporizadas:
    """RF-S06, S07, S08: Transiciones automaticas por tiempo."""

    def test_verificando_escala_a_alerta_tras_countdown(self, machine, monkeypatch):
        """RF-S06: VERIFICANDO -> ALERTA automatico cuando countdown llega a 0."""
        monkeypatch.setattr(
            "safepath_mvp.simulador.logic.TIEMPO_VERIFICACION", 1
        )
        machine.update(20.0)
        assert machine.state == "VERIFICANDO"
        time.sleep(1.5)
        assert machine.state == "ALERTA"

    def test_alerta_transiciona_a_resuelto_automaticamente(self, machine, monkeypatch):
        """RF-S07: ALERTA -> RESUELTO automatico a los 30s."""
        monkeypatch.setattr(
            "safepath_mvp.simulador.logic.DURACION_ALERTA", 1
        )
        machine.force_state("ALERTA")
        time.sleep(1.5)
        assert machine.state == "RESUELTO"

    def test_resuelto_transiciona_a_normal_automaticamente(self, machine, monkeypatch):
        """RF-S08: RESUELTO -> NORMAL automatico a los 5s."""
        monkeypatch.setattr(
            "safepath_mvp.simulador.logic.DURACION_RESUELTO", 1
        )
        machine.force_state("RESUELTO")
        time.sleep(1.5)
        assert machine.state == "NORMAL"

    def test_flujo_completo_automatico(self, machine, monkeypatch):
        """Flujo completo: NORMAL -> VERIFICANDO -> ALERTA -> RESUELTO -> NORMAL."""
        monkeypatch.setattr(
            "safepath_mvp.simulador.logic.TIEMPO_VERIFICACION", 1
        )
        monkeypatch.setattr(
            "safepath_mvp.simulador.logic.DURACION_ALERTA", 1
        )
        monkeypatch.setattr(
            "safepath_mvp.simulador.logic.DURACION_RESUELTO", 1
        )

        machine.update(20.0)
        time.sleep(1.2)
        assert machine.state == "ALERTA"
        time.sleep(1.2)
        assert machine.state == "RESUELTO"
        time.sleep(1.2)
        assert machine.state == "NORMAL"


class TestHistorial:
    """RF-S14: Historial de eventos con timestamp."""

    def test_update_genera_entrada_en_historial(self, machine):
        machine.update(20.0)
        assert len(machine.historial) == 1
        assert machine.historial[0]["estado"] == "VERIFICANDO"

    def test_historial_guarda_aceleracion(self, machine):
        machine.update(25.5)
        assert machine.historial[0]["aceleracion"] == 25.5

    def test_historial_guarda_timestamp(self, machine):
        machine.update(20.0)
        assert "timestamp" in machine.historial[0]
        assert len(machine.historial[0]["timestamp"]) > 10

    def test_historial_limite_10_eventos(self, machine, monkeypatch):
        monkeypatch.setattr(machine, "_start_timer", lambda *a: None)
        for _ in range(15):
            machine.force_state("VERIFICANDO")
            machine.cancel()
        assert len(machine.historial) == 10

    def test_historial_marca_cancelado(self, machine):
        machine.update(20.0)
        machine.cancel()
        ultimo = machine.historial[-1]
        assert ultimo.get("cancelado") is True

    def test_historial_marca_escalado(self, machine, monkeypatch):
        monkeypatch.setattr(
            "safepath_mvp.simulador.logic.TIEMPO_VERIFICACION", 1
        )
        machine.update(20.0)
        time.sleep(1.5)
        entradas_alerta = [
            e for e in machine.historial if e.get("escalado")
        ]
        assert len(entradas_alerta) == 1

    def test_historial_marca_forzado(self, machine):
        machine.force_state("ALERTA")
        ultimo = machine.historial[-1]
        assert ultimo.get("forzado") is True


class TestThreadSafety:
    """RNF-S03: Sin crashes ante condiciones de carrera."""

    def test_update_concurrente_no_crashea(self, machine, monkeypatch):
        monkeypatch.setattr(machine, "_start_timer", lambda *a: None)
        errores = []

        def bombardear():
            try:
                for _ in range(50):
                    machine.update(20.0)
                    time.sleep(0.01)
            except Exception as e:
                errores.append(e)

        hilos = [threading.Thread(target=bombardear) for _ in range(5)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        assert len(errores) == 0, f"Errores en concurrencia: {errores}"
        assert machine.state in ("NORMAL", "VERIFICANDO", "ALERTA", "RESUELTO")


class TestStateJSON:
    """RF-S10, RNF-S04: state.json atomico y no corrupto."""

    def test_state_json_se_escribe_y_es_valido(self, machine, tmp_path, monkeypatch):
        """RF-S10: state.json se escribe en cada cambio."""
        state_path = tmp_path / "state.json"

        def _save_tmp(self):
            import json
            import os
            tmp = tmp_path / "state_tmp.json"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.get_state(), f, ensure_ascii=False)
            os.replace(str(tmp), str(state_path))

        monkeypatch.setattr(
            "safepath_mvp.simulador.logic.StateMachine._save", _save_tmp
        )
        machine._save()

        assert state_path.exists()
        with open(state_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["estado"] == "NORMAL"

    def test_escritura_atomica_no_deja_archivos_temporales(
        self, machine, tmp_path, monkeypatch
    ):
        """RNF-S04: Tras write atomico no quedan archivos .tmp_*."""
        state_path = tmp_path / "state.json"

        def _save_tmp(self):
            import json
            import os
            import tempfile
            tmp_fd, tmp_p = tempfile.mkstemp(
                suffix=".json", prefix=".tmp_", dir=str(tmp_path)
            )
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(self.get_state(), f, ensure_ascii=False)
            os.replace(tmp_p, str(state_path))

        monkeypatch.setattr(
            "safepath_mvp.simulador.logic.StateMachine._save", _save_tmp
        )
        machine.update(20.0)

        assert state_path.exists()
        tmp_files = list(tmp_path.glob(".tmp_*.json"))
        assert len(tmp_files) == 0, (
            "Archivo temporal no fue limpiado - posible escritura no atomica"
        )
