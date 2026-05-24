import json, time, threading
from config import *

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
            if self.timer:
                self.timer.cancel()
            self._add_historial("Alerta cancelada manualmente")
            self._transition("NORMAL")
            self._save()

    def _transition(self, new_state):
        self.state = new_state
        self.evento_inicio = time.time()
        self._add_historial(f"Estado → {new_state}")

        if new_state == "VERIFICANDO":
            self.countdown = TIEMPO_VERIFICACION
            self.timer = threading.Timer(
                TIEMPO_VERIFICACION, self._escalar
            )
            self.timer.start()
            threading.Thread(target=self._update_countdown, daemon=True).start()
        elif new_state == "NORMAL":
            self.countdown = 0

    def _update_countdown(self):
        for i in range(TIEMPO_VERIFICACION, 0, -1):
            if self.state != "VERIFICANDO":
                break
            self.countdown = i
            self._save()
            time.sleep(1)

    def _escalar(self):
        if self.state == "VERIFICANDO":
            self._add_historial("⚠️ ALERTA ESCALADA — sin respuesta")
            self.state = "ALERTA"
            self._save()
            threading.Timer(DURACION_ALERTA, self._resolver).start()

    def _resolver(self):
        if self.state == "ALERTA":
            self._add_historial("✅ Evento resuelto")
            self.state = "RESUELTO"
            self._save()
            threading.Timer(5, self._volver_normal).start()

    def _volver_normal(self):
        self.state = "NORMAL"
        self.countdown = 0
        self._save()

    def _add_historial(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.historial.append(f"{ts}  {msg}")
        if len(self.historial) > 8:
            self.historial = self.historial[-8:]

    def get_state(self):
        return {
            "state": self.state,
            "accel": self.accel_actual,
            "countdown": self.countdown,
            "historial": self.historial,
            "umbral": UMBRAL_ACELERACION,
            "lat": self.lat,
            "lon": self.lon,
            "gps_activo": self.gps_activo,
        }

    def _save(self):
        with open("state.json", "w") as f:
            json.dump(self.get_state(), f)
