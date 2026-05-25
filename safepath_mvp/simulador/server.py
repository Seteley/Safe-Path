"""SAFE-PATH - Servidor Flask (Dimension 1: Simulador de Pulsera).

Recibe datos del acelerometro via HTTP POST, los procesa con la
maquina de estados y expone endpoints REST para el dashboard.
"""

from flask import Flask, request, jsonify
import math
from .config import *
from .logic import StateMachine
from .parser import extraer_aceleracion, extraer_gps, calcular_aceleracion_neta
from ..shared.schema import ESTADOS_VALIDOS
from ..shared.utils import get_local_ip, setup_logging

logger = setup_logging("safepath.server")

app = Flask(__name__)
machine = StateMachine()


# ── Endpoints principales (spec D1) ──────────────────────────────


@app.route("/data", methods=["POST"])
def receive_data() -> tuple:
    """RF-S01: Recibe datos del acelerometro y GPS desde Sensor Logger."""
    try:
        raw = request.get_data(as_text=True)
        logger.info("POST /data recibido (%d bytes): %.500s", len(raw), raw)

        data = request.get_json(silent=True)
        if data is None:
            logger.warning("JSON invalido o vacio en /data")
            return jsonify({"status": "error", "msg": "JSON invalido"}), 400

        resultado = extraer_aceleracion(data)
        if resultado is None:
            if isinstance(data, dict):
                claves = list(data.keys())
            elif isinstance(data, list):
                claves = f"list[{len(data)} items]"
            else:
                claves = str(type(data).__name__)
            logger.warning(
                "No se encontraron campos de aceleracion. Tipo: %s, Info: %s",
                type(data).__name__,
                claves,
            )
            return jsonify(
                {
                    "status": "error",
                    "msg": "campos no reconocidos",
                    "received_type": type(data).__name__,
                }
            ), 400

        ax, ay, az = resultado
        net_acceleration = calcular_aceleracion_neta(ax, ay, az, GRAVEDAD)

        gps = extraer_gps(data)
        if gps:
            lat, lon = gps
            machine.update_location(lat, lon)

        gps_str = (
            f" GPS=({machine.lat:.6f},{machine.lon:.6f})" if gps else ""
        )
        logger.debug(
            "ax=%.2f ay=%.2f az=%.2f net=%.2f state=%s%s",
            ax, ay, az, net_acceleration, machine.state, gps_str,
        )

        machine.update(net_acceleration)
        return jsonify({"status": "ok", "accel": round(net_acceleration, 2)})
    except Exception as e:
        logger.exception("ERROR en /data: %s", e)
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route("/status", methods=["GET"])
def get_status() -> tuple:
    """RF-S11: Retorna el estado actual completo."""
    return jsonify(machine.get_state())


@app.route("/cancel", methods=["GET", "POST"])
def cancel_alert() -> tuple:
    """RF-S09: Cancela verificacion en curso."""
    machine.cancel()
    return jsonify({"status": "cancelado"})


@app.route("/trigger", methods=["GET"])
def trigger_state() -> tuple:
    """RF-S12: Fuerza un estado manualmente (?estado=X)."""
    estado = request.args.get("estado", "").upper()
    if estado not in ESTADOS_VALIDOS:
        return jsonify(
            {
                "status": "error",
                "msg": f"estado invalido. Usar: {', '.join(sorted(ESTADOS_VALIDOS))}",
            }
        ), 400
    machine.force_state(estado)
    return jsonify({"status": "ok", "estado": machine.state})


@app.route("/reset", methods=["GET"])
def reset_state() -> tuple:
    """RF-S13: Resetea a NORMAL para nueva demo."""
    machine.reset()
    return jsonify({"status": "reseteado", "estado": machine.state})


# ── Alias (compatibilidad con versiones anteriores) ──────────────


@app.route("/sensor", methods=["POST"])
def receive_sensor() -> tuple:
    return receive_data()


@app.route("/state", methods=["GET"])
def get_state() -> tuple:
    return get_status()


@app.route("/ping", methods=["GET"])
def ping() -> tuple:
    return jsonify({"status": "alive", "state": machine.state})


# ── Startup ──────────────────────────────────────────────────────

if __name__ == "__main__":
    local_ip = get_local_ip()
    print("=" * 55)
    print("  SAFE-PATH SERVER (D1 - Simulador de Pulsera)")
    print(f"  IP detectada: {local_ip}")
    print(f"  POST /data       <- Sensor Logger (acelerometro)")
    print(f"  GET  /status     <- Estado completo")
    print(f"  GET  /cancel     <- Cancelar verificacion")
    print(f"  GET  /trigger?estado=X  <- Forzar estado (Plan B)")
    print(f"  GET  /reset      <- Reiniciar para nueva demo")
    print(f"  GET  /ping       <- Health check")
    print("=" * 55)
    app.run(host=HOST, port=PORT)
