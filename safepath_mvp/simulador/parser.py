"""Extraccion de datos de acelerometro y GPS desde payloads HTTP JSON.

Soporta multiples formatos: Sensor Logger (Android/iOS), Phyphox, sensores nativos.
"""

from __future__ import annotations

import math
from typing import Optional


def buscar_aceleracion_en_dict(
    d: dict, profundidad: int = 0
) -> Optional[tuple[float, float, float]]:
    """Busca recursivamente campos de aceleracion en un diccionario anidado."""
    if profundidad > 5 or d is None:
        return None

    patrones = [
        ("ax", "ay", "az"),
        ("x", "y", "z"),
        ("accelerometerAccelerationX", "accelerometerAccelerationY", "accelerometerAccelerationZ"),
        ("accelerationX", "accelerationY", "accelerationZ"),
        ("accelX", "accelY", "accelZ"),
        ("accel_x", "accel_y", "accel_z"),
        ("ACCX", "ACCY", "ACCZ"),
        ("userAccelerationX", "userAccelerationY", "userAccelerationZ"),
    ]

    for px, py, pz in patrones:
        if px in d and py in d and pz in d:
            try:
                return float(d[px]), float(d[py]), float(d[pz])
            except (ValueError, TypeError):
                pass

    for k, v in d.items():
        if isinstance(v, dict):
            result = buscar_aceleracion_en_dict(v, profundidad + 1)
            if result:
                return result

    return None


def extraer_aceleracion(
    data: dict | list | None,
) -> Optional[tuple[float, float, float]]:
    """Extrae (ax, ay, az) de cualquier estructura JSON anidada."""
    if data is None:
        return None

    if isinstance(data, list) and len(data) > 0:
        for item in reversed(data):
            if isinstance(item, dict):
                result = buscar_aceleracion_en_dict(item)
                if result:
                    return result
        return None

    if isinstance(data, dict):
        result = buscar_aceleracion_en_dict(data)
        if result:
            return result

        for k in ("payload", "data", "records", "measurements", "sensorData"):
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


def buscar_gps_en_dict(
    d: dict, profundidad: int = 0
) -> Optional[tuple[float, float]]:
    """Busca recursivamente lat/lon en diccionario anidado."""
    if profundidad > 5 or d is None:
        return None

    patrones = [
        ("latitude", "longitude"),
        ("lat", "lon"),
        ("lat", "lng"),
        ("lat", "long"),
        ("locationLatitude", "locationLongitude"),
        ("gpsLatitude", "gpsLongitude"),
        ("GpsLat", "GpsLon"),
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


def extraer_gps(data: dict | list | None) -> Optional[tuple[float, float]]:
    """Extrae (lat, lon) de cualquier estructura JSON anidada."""
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

        for k in ("payload", "data", "records", "measurements", "location"):
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


def calcular_aceleracion_neta(
    ax: float, ay: float, az: float, gravedad: float = 9.8
) -> float:
    """RF-S02: Calcula magnitud neta = |sqrt(ax^2 + ay^2 + az^2) - gravedad|."""
    magnitude = math.sqrt(ax ** 2 + ay ** 2 + az ** 2)
    return abs(magnitude - gravedad)
