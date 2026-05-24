from flask import Flask, request, jsonify
import json, time, math, threading, socket
from config import *
from logic import StateMachine

app = Flask(__name__)
machine = StateMachine()


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def buscar_aceleracion_en_dict(d, profundidad=0):
    """Busca recursivamente valores ax/ay/az o x/y/z en un dict."""
    if profundidad > 5 or d is None:
        return None

    # Patrones de nombres de campos
    patrones = [
        ('ax', 'ay', 'az'),
        ('x', 'y', 'z'),
        ('accelerometerAccelerationX', 'accelerometerAccelerationY', 'accelerometerAccelerationZ'),
        ('accelerationX', 'accelerationY', 'accelerationZ'),
        ('accelX', 'accelY', 'accelZ'),
        ('accel_x', 'accel_y', 'accel_z'),
        ('ACCX', 'ACCY', 'ACCZ'),
        ('userAccelerationX', 'userAccelerationY', 'userAccelerationZ'),
    ]

    for px, py, pz in patrones:
        if px in d and py in d and pz in d:
            try:
                return float(d[px]), float(d[py]), float(d[pz])
            except (ValueError, TypeError):
                pass

    # Buscar en sub-objetos
    for k, v in d.items():
        if isinstance(v, dict):
            result = buscar_aceleracion_en_dict(v, profundidad + 1)
            if result:
                return result

    return None


def extraer_aceleracion(data):
    """Intenta extraer aceleración de cualquier estructura JSON."""
    if data is None:
        return None

    # 1. Array de lecturas (Sensor Logger manda batches)
    if isinstance(data, list) and len(data) > 0:
        # Tomar la última lectura del batch
        for item in reversed(data):
            if isinstance(item, dict):
                result = buscar_aceleracion_en_dict(item)
                if result:
                    return result
            elif isinstance(item, (int, float)):
                pass
        return None

    # 2. Objeto con payload anidado (formato común de Sensor Logger)
    if isinstance(data, dict):
        # Probar primero en el nivel raíz
        result = buscar_aceleracion_en_dict(data)
        if result:
            return result

        # Buscar en 'payload' o 'data'
        for k in ('payload', 'data', 'records', 'measurements', 'sensorData'):
            if k in data:
                sub = data[k]
                if isinstance(sub, dict):
                    result = buscar_aceleracion_en_dict(sub)
                    if result:
                        return result
                elif isinstance(sub, list) and len(sub) > 0:
                    for item in reversed(sub):
                        if isinstance(item, dict):
                            result = buscar_aceleracion_en_dict(item)
                            if result:
                                return result

    return None


def buscar_gps_en_dict(d, profundidad=0):
    """Busca recursivamente latitud/longitud en un dict."""
    if profundidad > 5 or d is None:
        return None

    patrones = [
        ('latitude', 'longitude'),
        ('lat', 'lon'),
        ('lat', 'lng'),
        ('lat', 'long'),
        ('locationLatitude', 'locationLongitude'),
        ('gpsLatitude', 'gpsLongitude'),
        ('GpsLat', 'GpsLon'),
    ]

    for p_lat, p_lon in patrones:
        if p_lat in d and p_lon in d:
            try:
                lat = float(d[p_lat])
                lon = float(d[p_lon])
                if -90 <= lat <= 90 and -180 <= lon <= 180 and not (lat == 0 and lon == 0):
                    return lat, lon
            except (ValueError, TypeError):
                pass

    for k, v in d.items():
        if isinstance(v, dict):
            result = buscar_gps_en_dict(v, profundidad + 1)
            if result:
                return result

    return None


def extraer_gps(data):
    """Intenta extraer coordenadas GPS de cualquier estructura JSON."""
    if data is None:
        return None

    if isinstance(data, list):
        for item in reversed(data):
            if isinstance(item, dict):
                result = buscar_gps_en_dict(item)
                if result:
                    return result
        return None

    if isinstance(data, dict):
        result = buscar_gps_en_dict(data)
        if result:
            return result

        for k in ('payload', 'data', 'records', 'measurements', 'location'):
            if k in data:
                sub = data[k]
                if isinstance(sub, dict):
                    result = buscar_gps_en_dict(sub)
                    if result:
                        return result
                elif isinstance(sub, list):
                    for item in reversed(sub):
                        if isinstance(item, dict):
                            result = buscar_gps_en_dict(item)
                            if result:
                                return result

    return None


@app.route('/sensor', methods=['POST'])
def receive_sensor():
    try:
        raw = request.get_data(as_text=True)
        print(f"\n[->] POST recibido ({len(raw)} bytes): {raw[:500]}")

        data = request.json
        if data is None:
            print("[!] JSON inválido o vacío")
            return jsonify({"status": "error", "msg": "JSON inválido"}), 400

        resultado = extraer_aceleracion(data)
        if resultado is None:
            if isinstance(data, dict):
                claves = list(data.keys())
            elif isinstance(data, list):
                claves = f"list[{len(data)} items]"
            else:
                claves = str(type(data).__name__)
            print(f"[!] No se encontraron campos de aceleración. Tipo: {type(data).__name__}, Info: {claves}")
            return jsonify({"status": "error", "msg": "campos no reconocidos",
                            "received_type": type(data).__name__}), 400

        ax, ay, az = resultado
        magnitude = math.sqrt(ax**2 + ay**2 + az**2)
        net_acceleration = abs(magnitude - 9.8)

        gps = extraer_gps(data)
        if gps:
            lat, lon = gps
            machine.update_location(lat, lon)

        gps_str = f" GPS=({machine.lat:.6f},{machine.lon:.6f})" if gps else ""
        print(f"    ax={ax:.2f} ay={ay:.2f} az={az:.2f} "
              f"mag={magnitude:.2f} net={net_acceleration:.2f} "
              f"state={machine.state}{gps_str}")

        machine.update(net_acceleration)
        return jsonify({"status": "ok", "accel": round(net_acceleration, 2)})
    except Exception as e:
        print(f"[!!!] ERROR en /sensor: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route('/cancel', methods=['POST'])
def cancel_alert():
    machine.cancel()
    return jsonify({"status": "cancelled"})


@app.route('/state', methods=['GET'])
def get_state():
    return jsonify(machine.get_state())


@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "alive", "state": machine.state})


@app.route('/debug/trigger', methods=['GET'])
def debug_trigger():
    machine.update(20.0)
    return jsonify(machine.get_state())


if __name__ == '__main__':
    local_ip = get_local_ip()
    print("=" * 55)
    print("  SAFE-PATH SERVER")
    print(f"  IP local detectada: {local_ip}")
    print(f"  Sensor endpoint:  http://{local_ip}:{PORT}/sensor")
    print(f"  Debug trigger:    http://{local_ip}:{PORT}/debug/trigger")
    print(f"  Cancel endpoint:  http://{local_ip}:{PORT}/cancel")
    print(f"  Ping:             http://{local_ip}:{PORT}/ping")
    print("=" * 55)
    app.run(host=HOST, port=PORT)
