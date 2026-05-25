"""
schema.py — Contrato del state.json

Define los nombres de campos, tipos de datos, valores por defecto
y estados válidos que comparten logic.py (backend) y dashboard.py (frontend).

Importar desde aquí en lugar de hardcodear strings en cada archivo.
"""
from config import *

# ── Estados válidos de la máquina ──────────────────────────────
ESTADOS_VALIDOS = {"NORMAL", "VERIFICANDO", "ALERTA", "RESUELTO"}

# ── Campos del state.json con sus valores por defecto ──────────
ESTADO_INICIAL = {
    "estado":                         "NORMAL",
    "aceleracion_actual":             0.0,
    "countdown_restante":             0,
    "timestamp_cambio":               "",
    "timestamp_inicio_verificando":   None,
    "historial":                      [],
    "usuaria":                        USUARIA,
    "contacto":                       CONTACTO,
    "lat":                            UBICACION_LAT,
    "lon":                            UBICACION_LON,
    "direccion":                      DIRECCION,
    "umbral":                         UMBRAL_ACELERACION,
}

# ── Campos de cada entrada del historial ───────────────────────
CAMPOS_HISTORIAL = {"estado", "timestamp", "aceleracion"}
FLAGS_HISTORIAL = {"cancelado", "escalado", "forzado"}

# ── Paleta de colores SafeCorp (dashboard) ─────────────────────
COLOR_NORMAL       = "#22c55e"
COLOR_VERIFICANDO  = "#eab308"
COLOR_ALERTA       = "#ef4444"
COLOR_RESUELTO     = "#6b7280"

# ── Umbrales adicionales ───────────────────────────────────────
UMBRAL_MOVIMIENTO_GPS = 0.00004  # grados (~4m) — filtro anti-ruido del GPS
