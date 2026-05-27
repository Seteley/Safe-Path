"""Maquina de estados de la pulsera SAFE-PATH.

Implementa el flujo NORMAL -> VERIFICANDO -> ALERTA -> RESUELTO -> NORMAL
con timers thread-safe y escritura atomica a state.json.
"""

from __future__ import annotations

import json
import time
import threading
import os
from datetime import datetime, timezone
from typing import Any, Optional

from .config import *
from ..shared.schema import ESTADOS_VALIDOS
from ..shared.utils import atomic_write_json, setup_logging

logger = setup_logging("safepath.statemachine")


def ahora() -> str:
    """Timestamp UTC en formato ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


class StateMachine:
    """Maquina de estados thread-safe de la pulsera SAFE-PATH.

    Estados: NORMAL -> VERIFICANDO -> ALERTA -> RESUELTO -> NORMAL
    Thread-safe para acceso concurrente desde Flask y timers internos.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.state: str = "NORMAL"
        self.accel_actual: float = 0.0
        self.countdown: int = 0
        self.evento_inicio: Optional[float] = None
        self.historial: list[dict[str, Any]] = []
        self.timer: Optional[threading.Timer] = None
        self._timers: list[threading.Timer] = []
        self.lat: float = UBICACION_LAT
        self.lon: float = UBICACION_LON
        self.gps_activo: bool = False
        self.timestamp_cambio: str = ahora()
        self.timestamp_inicio_verificando: Optional[str] = None
        self._save()

    # ── Metodos publicos (thread-safe) ────────────────────────────

    def update(self, accel: float) -> None:
        """RF-S01, S03: Procesa nueva lectura de aceleracion y evalua transicion."""
        with self._lock:
            self.accel_actual = round(accel, 2)
            if self.state == "NORMAL" and accel > UMBRAL_ACELERACION:
                self._transition("VERIFICANDO")
            self._save()

    def update_location(self, lat: float | None, lon: float | None) -> None:
        """Actualiza coordenadas GPS si son validas."""
        with self._lock:
            if lat is not None and lon is not None:
                self.lat = round(lat, 6)
                self.lon = round(lon, 6)
                self.gps_activo = True

    def cancel(self) -> None:
        """RF-S09: Cancela verificacion en curso, retorna a NORMAL."""
        with self._lock:
            if self.state == "VERIFICANDO":
                self._cancelar_todos_los_timers()
                self._add_historial("NORMAL", self.accel_actual, cancelado=True)
                self.state = "NORMAL"
                self.countdown = 0
                self.timestamp_cambio = ahora()
                self.timestamp_inicio_verificando = None
                self._save()

    def force_state(self, estado: str) -> bool:
        """RF-S12: Fuerza transicion manual a cualquier estado valido."""
        if estado not in ESTADOS_VALIDOS:
            return False
        with self._lock:
            self._cancelar_todos_los_timers()
            self._add_historial(estado, self.accel_actual, forzado=True)
            self.state = estado
            self.timestamp_cambio = ahora()
            if estado == "VERIFICANDO":
                self.timestamp_inicio_verificando = ahora()
                self.countdown = TIEMPO_VERIFICACION
                self.timer = threading.Timer(TIEMPO_VERIFICACION, self._escalar)
                self._timers.append(self.timer)
                self.timer.start()
                threading.Thread(
                    target=self._update_countdown, daemon=True
                ).start()
            else:
                self.countdown = 0
                self.timestamp_inicio_verificando = None
                if estado == "ALERTA":
                    self._notificar_alerta()
                    self._start_timer(DURACION_ALERTA, self._resolver)
                elif estado == "RESUELTO":
                    self._start_timer(DURACION_RESUELTO, self._volver_normal)
            self._save()
        return True

    def reset(self) -> None:
        """RF-S13: Reinicia maquina a estado NORMAL, cancela todos los timers."""
        with self._lock:
            self._cancelar_todos_los_timers()
            self.state = "NORMAL"
            self.accel_actual = 0.0
            self.countdown = 0
            self.timestamp_cambio = ahora()
            self.timestamp_inicio_verificando = None
            self.historial = []
            self.timer = None
            self._save()

    def get_state(self) -> dict[str, Any]:
        """RF-S11: Retorna snapshot completo del estado actual."""
        return {
            "estado": self.state,
            "aceleracion_actual": self.accel_actual,
            "countdown_restante": self.countdown,
            "timestamp_cambio": self.timestamp_cambio,
            "timestamp_inicio_verificando": self.timestamp_inicio_verificando,
            "historial": list(self.historial),
            "usuaria": USUARIA,
            "contacto": CONTACTO,
            "lat": self.lat,
            "lon": self.lon,
            "direccion": DIRECCION,
            "umbral": UMBRAL_ACELERACION,
        }

    # ── Metodos internos (deben llamarse con lock adquirido) ──────

    def _start_timer(self, delay: float, callback) -> None:
        """Crea y arranca un timer trackeado. PRE: lock adquirido."""
        t = threading.Timer(delay, callback)
        self._timers.append(t)
        t.start()

    def _cancelar_todos_los_timers(self) -> None:
        """Cancela y limpia todos los timers activos. PRE: lock adquirido."""
        for t in self._timers:
            try:
                t.cancel()
            except Exception:
                pass
        self._timers.clear()
        self.timer = None

    def _transition(self, new_state: str) -> None:
        """PRE: lock adquirido."""
        self.state = new_state
        self.timestamp_cambio = ahora()
        self.evento_inicio = time.time()
        self._add_historial(new_state, self.accel_actual)

        if new_state == "VERIFICANDO":
            self.timestamp_inicio_verificando = ahora()
            self.countdown = TIEMPO_VERIFICACION
            self._cancelar_todos_los_timers()
            self.timer = threading.Timer(TIEMPO_VERIFICACION, self._escalar)
            self._timers.append(self.timer)
            self.timer.start()
            threading.Thread(
                target=self._update_countdown, daemon=True
            ).start()
        elif new_state == "NORMAL":
            self.countdown = 0
            self.timestamp_inicio_verificando = None

    def _update_countdown(self) -> None:
        """Actualiza countdown cada segundo hasta salir de VERIFICANDO."""
        for i in range(TIEMPO_VERIFICACION, 0, -1):
            if self.state != "VERIFICANDO":
                break
            self.countdown = i
            self._save()
            time.sleep(1)

    def _escalar(self) -> None:
        """RF-S06: Callback - transita VERIFICANDO -> ALERTA."""
        try:
            with self._lock:
                if self.state != "VERIFICANDO":
                    return
                self._add_historial("ALERTA", self.accel_actual, escalado=True)
                self.state = "ALERTA"
                self.timestamp_cambio = ahora()
                self._save()
                self._notificar_alerta()
                self._start_timer(DURACION_ALERTA, self._resolver)
        except Exception:
            logger.exception(
                "CRITICO: _escalar() fallo - estado actual=%s", self.state
            )

    def _resolver(self) -> None:
        """RF-S07: Callback - transita ALERTA -> RESUELTO."""
        try:
            with self._lock:
                if self.state != "ALERTA":
                    return
                self._add_historial("RESUELTO", self.accel_actual)
                self.state = "RESUELTO"
                self.timestamp_cambio = ahora()
                self._save()
                self._start_timer(DURACION_RESUELTO, self._volver_normal)
        except Exception:
            logger.exception(
                "CRITICO: _resolver() fallo - estado actual=%s", self.state
            )

    def _volver_normal(self) -> None:
        """RF-S08: Callback - transita RESUELTO -> NORMAL."""
        try:
            with self._lock:
                self.state = "NORMAL"
                self.countdown = 0
                self.timestamp_cambio = ahora()
                self.timestamp_inicio_verificando = None
                self._save()
        except Exception:
            logger.exception(
                "CRITICO: _volver_normal() fallo - forzando NORMAL"
            )
            with self._lock:
                self.state = "NORMAL"
                self.countdown = 0
                self._save()

    def _add_historial(
        self,
        estado: str,
        aceleracion: float,
        cancelado: bool = False,
        escalado: bool = False,
        forzado: bool = False,
    ) -> None:
        """RF-S14: Registra entrada en historial con flags opcionales."""
        entrada: dict[str, Any] = {
            "estado": estado,
            "timestamp": ahora(),
            "aceleracion": aceleracion,
        }
        if cancelado:
            entrada["estado"] = "NORMAL"
            entrada["cancelado"] = True
        if escalado:
            entrada["escalado"] = True
        if forzado:
            entrada["forzado"] = True
        self.historial.append(entrada)
        if len(self.historial) > 10:
            self.historial = self.historial[-10:]

    def _save(self) -> None:
        """RF-S10, RNF-S04: Escribe estado a state.json de forma atomica."""
        state_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "state.json",
        )
        atomic_write_json(state_path, self.get_state())

    def _notificar_alerta(self) -> None:
        """Envia notificacion al contacto de confianza en un hilo aparte."""
        try:
            from .notifications import enviar_alerta_sms

            threading.Thread(
                target=enviar_alerta_sms,
                args=(self.get_state(),),
                daemon=True,
            ).start()
        except ImportError:
            logger.warning(
                "Modulo notifications.py no encontrado - notificacion omitida"
            )
