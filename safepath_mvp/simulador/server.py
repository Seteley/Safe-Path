"""SAFE-PATH - Servidor Flask (Dimension 1: Simulador de Pulsera).

Consulta periodicamente Phyphox (HTTP GET) para obtener acelerometro y GPS,
los procesa con la maquina de estados y expone endpoints REST para el dashboard.
"""

import threading
import time

import requests as http_client
from flask import Flask, jsonify, request

from ..shared.schema import ESTADOS_VALIDOS
from ..shared.utils import get_local_ip, setup_logging
from .config import GRAVEDAD, HOST, PHYPHOX_IP, PHYPHOX_POLL_INTERVAL, PHYPHOX_PORT, PORT
from .logic import StateMachine
from .parser import (
    calcular_aceleracion_neta,
    extraer_aceleracion,
    extraer_aceleracion_phyphox,
    extraer_gps,
    extraer_gps_phyphox,
)

logger = setup_logging("safepath.server")

app = Flask(__name__)
machine = StateMachine()


# ── Endpoints principales (spec D1) ──────────────────────────────


def phyphox_poller() -> None:
    """Hilo daemon que consulta Phyphox cada PHYPHOX_POLL_INTERVAL segundos."""
    base = f"http://{PHYPHOX_IP}:{PHYPHOX_PORT}"
    url_accel = f"{base}/get?accX=full&accY=full&accZ=full"
    url_gps = f"{base}/get?lat=full&lon=full"
    logger.info("Phyphox poller iniciado → %s", base)

    while True:
        try:
            resp = http_client.get(url_accel, timeout=0.5)
            resultado = extraer_aceleracion_phyphox(resp.json())
            if resultado:
                ax, ay, az = resultado
                net = calcular_aceleracion_neta(ax, ay, az, GRAVEDAD)
                machine.update(net)
                logger.debug("Phyphox accel ax=%.2f ay=%.2f az=%.2f net=%.2f", ax, ay, az, net)
        except Exception as exc:
            logger.debug("Phyphox accel no disponible: %s", exc)

        try:
            resp_gps = http_client.get(url_gps, timeout=0.5)
            gps = extraer_gps_phyphox(resp_gps.json())
            if gps:
                machine.update_location(*gps)
        except Exception as exc:
            logger.debug("Phyphox GPS no disponible: %s", exc)

        time.sleep(PHYPHOX_POLL_INTERVAL)


@app.route("/data", methods=["POST"])
def receive_data() -> tuple:
    """RF-S01: Recibe datos del acelerometro y GPS (endpoint manual / fallback)."""
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

        gps_str = f" GPS=({machine.lat:.6f},{machine.lon:.6f})" if gps else ""
        logger.debug(
            "ax=%.2f ay=%.2f az=%.2f net=%.2f state=%s%s",
            ax,
            ay,
            az,
            net_acceleration,
            machine.state,
            gps_str,
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


@app.route("/mobile", methods=["GET"])
def mobile_view() -> tuple:
    """Vista móvil minimalista para control desde teléfono."""
    from .mobile_html import MOBILE_HTML

    return MOBILE_HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


# ── Startup ──────────────────────────────────────────────────────

if __name__ == "__main__":
    from .tunnel import start_tunnel

    local_ip = get_local_ip()
    print("=" * 55)
    print("  SAFE-PATH SERVER (D1 - Simulador de Pulsera)")
    print(f"  IP detectada: {local_ip}")
    print(
        f"  Phyphox → http://{PHYPHOX_IP}:{PHYPHOX_PORT} (polling {int(PHYPHOX_POLL_INTERVAL * 1000)} ms)"
    )
    print("  POST /data       <- Fallback manual (sin Phyphox)")
    print("  GET  /status     <- Estado completo")
    print("  GET  /cancel     <- Cancelar verificacion")
    print("  GET  /trigger?estado=X  <- Forzar estado (Plan B)")
    print("  GET  /reset      <- Reiniciar para nueva demo")
    print("  GET  /ping       <- Health check")
    print("  GET  /mobile     <- Vista movil (telefono)")
    print("=" * 55)

    t = threading.Thread(target=phyphox_poller, daemon=True, name="phyphox-poller")
    t.start()

    start_tunnel(PORT)
    print("=" * 55)
    app.run(host=HOST, port=PORT)
