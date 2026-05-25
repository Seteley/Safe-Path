"""Fixtures compartidas para todos los tests."""

import json
import os
import sys
import shutil
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from safepath_mvp.simulador.logic import StateMachine


@pytest.fixture
def machine(tmp_path, monkeypatch):
    """StateMachine fresca y aislada para cada test.

    Redirige _save() a un archivo temporal para no tocar
    el state.json real del proyecto.
    """
    state_path = tmp_path / "state.json"

    def _save_tmp(self):
        tmp_fd, tmp_p = tempfile.mkstemp(
            suffix=".json", prefix=".tmp_", dir=str(tmp_path)
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(self.get_state(), f, ensure_ascii=False)
            try:
                os.replace(tmp_p, str(state_path))
            except PermissionError:
                shutil.move(tmp_p, str(state_path))
        except Exception:
            if os.path.exists(tmp_p):
                os.unlink(tmp_p)
            raise

    monkeypatch.setattr(
        "safepath_mvp.simulador.logic.StateMachine._save", _save_tmp
    )
    sm = StateMachine()

    # Desactivar _update_countdown para tests (evita threads huerfanos)
    monkeypatch.setattr(sm, "_update_countdown", lambda: None)

    yield sm
    sm.reset()


@pytest.fixture
def state_file(tmp_path):
    """Redirige state.json a archivo temporal."""
    state_path = tmp_path / "state.json"
    yield state_path


@pytest.fixture(autouse=True)
def mock_notificaciones(monkeypatch):
    """Previene que los tests envien emails reales."""

    def _fake_notificar(self):
        pass

    monkeypatch.setattr(
        "safepath_mvp.simulador.logic.StateMachine._notificar_alerta",
        _fake_notificar,
    )


@pytest.fixture
def client(tmp_path):
    """Cliente de test de Flask con state.json aislado y machine reseteada."""
    import safepath_mvp.simulador.logic as logic_mod
    import safepath_mvp.simulador.server as server_mod

    state_path = tmp_path / "state.json"

    def _save_tmp(self):
        tmp_fd, tmp_p = tempfile.mkstemp(
            suffix=".json", prefix=".tmp_", dir=str(tmp_path)
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(self.get_state(), f, ensure_ascii=False)
            try:
                os.replace(tmp_p, str(state_path))
            except PermissionError:
                shutil.move(tmp_p, str(state_path))
        except Exception:
            if os.path.exists(tmp_p):
                os.unlink(tmp_p)
            raise

    original_save = logic_mod.StateMachine._save
    logic_mod.StateMachine._save = _save_tmp

    # Resetear la maquina global antes de cada test
    server_mod.machine.reset()

    from safepath_mvp.simulador.server import app

    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

    logic_mod.StateMachine._save = original_save

