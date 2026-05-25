import json, time, threading, os
from datetime import datetime, timezone
from config import *
from schema import ESTADOS_VALIDOS


def ahora():
    return datetime.now(timezone.utc).isoformat()


class StateMachine:
    def __init__(self):
        self.state = "NORMAL"
        self.accel_actual = 0.0
        self.countdown = 0
        self.evento_inicio = None
        self.historial = []
        self.timer = None
        self.lat = UBICACION_LAT
        self.lon = UBICACION_LON
        self.gps_activo = False
        self.timestamp_cambio = ahora()
        self.timestamp_inicio_verificando = None
        self._save()

    def update(self, accel):
        self.accel_actual = round(accel, 2)
        if self.state == "NORMAL" and accel > UMBRAL_ACELERACION:
            self._transition("VERIFICANDO")
        self._save()

    def update_location(self, lat, lon):
        if lat is not None and lon is not None:
            self.lat = round(lat, 6)
            self.lon = round(lon, 6)
            self.gps_activo = True

    def cancel(self):
        if self.state == "VERIFICANDO":
            self._cancelar_timer()
            self._add_historial("NORMAL", self.accel_actual, cancelado=True)
            self._transition("NORMAL")
            self._save()

    def force_state(self, estado):
        if estado not in ESTADOS_VALIDOS:
            return False
        self._cancelar_timer()
        if estado == self.state:
            self._add_historial(estado, self.accel_actual, forzado=True)
        else:
            self._add_historial(estado, self.accel_actual, forzado=True)
        self.state = estado
        self.timestamp_cambio = ahora()
        if estado == "VERIFICANDO":
            self.timestamp_inicio_verificando = ahora()
            self.countdown = TIEMPO_VERIFICACION
            self.timer = threading.Timer(
                TIEMPO_VERIFICACION, self._escalar
            )
            self.timer.start()
            threading.Thread(target=self._update_countdown, daemon=True).start()
        else:
            self.countdown = 0
            self.timestamp_inicio_verificando = None
            if estado == "ALERTA":
                self._notificar_alerta()
                threading.Timer(DURACION_ALERTA, self._resolver).start()
            elif estado == "RESUELTO":
                threading.Timer(5, self._volver_normal).start()
        self._save()
        return True

    def reset(self):
        self._cancelar_timer()
        self.state = "NORMAL"
        self.accel_actual = 0.0
        self.countdown = 0
        self.timestamp_cambio = ahora()
        self.timestamp_inicio_verificando = None
        self.historial = []
        self.timer = None
        self._save()

    def _cancelar_timer(self):
        if self.timer:
            self.timer.cancel()
            self.timer = None

    def _transition(self, new_state):
        self.state = new_state
        self.timestamp_cambio = ahora()
        self.evento_inicio = time.time()
        self._add_historial(new_state, self.accel_actual)

        if new_state == "VERIFICANDO":
            self.timestamp_inicio_verificando = ahora()
            self.countdown = TIEMPO_VERIFICACION
            self._cancelar_timer()
            self.timer = threading.Timer(
                TIEMPO_VERIFICACION, self._escalar
            )
            self.timer.start()
            threading.Thread(target=self._update_countdown, daemon=True).start()
        elif new_state == "NORMAL":
            self.countdown = 0
            self.timestamp_inicio_verificando = None

    def _update_countdown(self):
        for i in range(TIEMPO_VERIFICACION, 0, -1):
            if self.state != "VERIFICANDO":
                break
            self.countdown = i
            self._save()
            time.sleep(1)

    def _escalar(self):
        if self.state == "VERIFICANDO":
            self._add_historial("ALERTA", self.accel_actual, escalado=True)
            self.state = "ALERTA"
            self.timestamp_cambio = ahora()
            self._save()
            self._notificar_alerta()
            threading.Timer(DURACION_ALERTA, self._resolver).start()

    def _resolver(self):
        if self.state == "ALERTA":
            self._add_historial("RESUELTO", self.accel_actual)
            self.state = "RESUELTO"
            self.timestamp_cambio = ahora()
            self._save()
            threading.Timer(5, self._volver_normal).start()

    def _volver_normal(self):
        self.state = "NORMAL"
        self.countdown = 0
        self.timestamp_cambio = ahora()
        self.timestamp_inicio_verificando = None
        self._save()

    def _add_historial(self, estado, aceleracion, cancelado=False, escalado=False, forzado=False):
        entrada = {
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

    def get_state(self):
        return {
            "estado": self.state,
            "aceleracion_actual": self.accel_actual,
            "countdown_restante": self.countdown,
            "timestamp_cambio": self.timestamp_cambio,
            "timestamp_inicio_verificando": self.timestamp_inicio_verificando,
            "historial": self.historial,
            "usuaria": USUARIA,
            "contacto": CONTACTO,
            "lat": self.lat,
            "lon": self.lon,
            "direccion": DIRECCION,
            "umbral": UMBRAL_ACELERACION,
        }

    def _save(self):
        tmp = "state_tmp.json"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.get_state(), f, ensure_ascii=False)
        os.replace(tmp, "state.json")

    def _notificar_alerta(self):
        """Envia notificacion al contacto de confianza en un hilo aparte."""
        try:
            from notifications import enviar_alerta_email
            threading.Thread(
                target=enviar_alerta_email,
                args=(self.get_state(),),
                daemon=True
            ).start()
        except ImportError:
            print("[!] Modulo notifications.py no encontrado")
