"""Componentes visuales del dashboard SAFE-PATH.

Cada funcion renderiza una seccion especifica de la UI.
Separado de dashboard.py para permitir desarrollo en paralelo.
"""

from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from typing import Any

import folium
import requests
import streamlit as st

from ..simulador.config import (
    CONTACTO,
    DIRECCION,
    TIEMPO_VERIFICACION,
    UBICACION_LAT,
    UBICACION_LON,
    UMBRAL_ACELERACION,
    UMBRAL_MOVIMIENTO_GPS,
    USUARIA,
)
from ..shared.schema import (
    COLOR_ALERTA,
    COLOR_NORMAL,
    COLOR_RESUELTO,
    COLOR_VERIFICANDO,
)

COLORES: dict[str, str] = {
    "NORMAL": COLOR_NORMAL,
    "VERIFICANDO": COLOR_VERIFICANDO,
    "ALERTA": COLOR_ALERTA,
    "RESUELTO": COLOR_RESUELTO,
}

EMOJIS: dict[str, str] = {
    "NORMAL": "\U0001f7e2",
    "VERIFICANDO": "\U0001f7e1",
    "ALERTA": "\U0001f534",
    "RESUELTO": "\U0001f535",
}

NAVY = "#1e2d4f"


# ── CSS global ────────────────────────────────────────────────────────────────

def inject_global_css() -> None:
    """Inyecta CSS global: fondo claro, fuente Inter, padding reset."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body,
        [data-testid="stApp"],
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background-color: #f0f4f8 !important;
            font-family: 'Inter', sans-serif !important;
        }

        [data-testid="stMainBlockContainer"] {
            padding-top: 0 !important;
            background-color: #f0f4f8 !important;
            font-family: 'Inter', sans-serif !important;
        }

        footer { visibility: hidden; }

        /* Anular estilos por defecto de metricas */
        [data-testid="stMetricLabel"] { color: #64748b !important; }
        [data-testid="stMetricValue"] { color: #1e293b !important; }

        /* Botones Streamlit */
        [data-testid="stButton"] button {
            border-radius: 8px !important;
            font-size: 0.82rem !important;
            font-family: 'Inter', sans-serif !important;
        }

        /* Ocultar completamente el header nativo de Streamlit */
        header[data-testid="stHeader"],
        .stAppHeader {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            min-height: 0 !important;
            max-height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            overflow: hidden !important;
            pointer-events: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── Header ────────────────────────────────────────────────────────────────────

def render_header(estado: str) -> None:
    """RF-D02: Barra dark-navy con logo, titulo y tabs Dashboard/Alertas."""
    st.markdown(
        f"""
        <div style="
            background:{NAVY};
            padding:14px 28px;
            display:flex;
            align-items:center;
            justify-content:space-between;
            margin-bottom:20px;
        ">
          <div style="display:flex;align-items:center;gap:14px">
            <div style="
                width:42px;height:42px;border-radius:50%;
                background:linear-gradient(135deg,#7c3aed,#4f46e5);
                display:flex;align-items:center;justify-content:center;
                font-size:20px;flex-shrink:0">🛡️</div>
            <div>
              <div style="color:white;font-weight:700;font-size:1.1rem;
                          letter-spacing:0.05em">SAFE-PATH</div>
              <div style="color:#94a3b8;font-size:0.75rem">
                Panel de seguridad preventiva</div>
            </div>
          </div>
          <div style="display:flex;gap:8px;align-items:center">
            <div style="
                background:white;color:{NAVY};
                padding:6px 18px;border-radius:20px;
                font-size:0.82rem;font-weight:700">Dashboard</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Estado (pulsera + info) ───────────────────────────────────────────────────

def render_estado(
    estado: str, usuaria: str, gps_texto: str, contacto: str
) -> None:
    """RF-D02, D03, D10, D16: Pulsera card + estado + GPS + contacto."""
    color = COLORES.get(estado, "#888")
    emoji = EMOJIS.get(estado, "⚪")

    # Imagen de la pulsera en base64
    img_path = os.path.join("safepath_mvp", "assets", "pulsera.png")
    card_inner = ""
    if os.path.exists(img_path):
        with open(img_path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()
        card_inner = (
            f"<img src='data:image/png;base64,{b64}' "
            f"style='width:120px;display:block;margin:0 auto'/>"
        )
    else:
        card_inner = "<div style='height:80px'></div>"

    st.markdown(
        f"""
        <div style="
            background:white;border-radius:14px;padding:18px;
            text-align:center;position:relative;margin-bottom:10px;
            border:1px solid #e2e8f0;
            box-shadow:0 1px 4px rgba(0,0,0,0.06)">
          <div style="
              position:absolute;top:12px;right:12px;
              width:11px;height:11px;border-radius:50%;
              background:{color};
              box-shadow:0 0 6px {color}"></div>
          {card_inner}
          <div style="color:#94a3b8;font-size:0.74rem;margin-top:8px">
            Pulsera SafePath</div>
          <div style="color:#cbd5e1;font-size:0.7rem">ID: SP-AF-0042</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Seccion de estado
    gps_coords = gps_texto.replace("\U0001f4cd ", "").replace("GPS: ", "")
    contact_pill = ""
    if estado == "ALERTA":
        contact_pill = (
            f"<div style='"
            f"display:inline-block;background:rgba(255,255,255,0.2);"
            f"color:white;border:1px solid rgba(255,255,255,0.4);"
            f"padding:4px 12px;border-radius:20px;font-size:0.76rem;"
            f"font-weight:600;margin-top:8px'>"
            f"⚠️ Contacto: {contacto}</div>"
        )

    st.markdown(
        f"""
        <div style="
            background:{color};
            padding:16px 18px;border-radius:12px;
            text-align:center;margin-bottom:12px">
          <div style="color:white;font-size:1.6rem;font-weight:700;
                      line-height:1.2">{emoji} {estado}</div>
          <div style="color:rgba(255,255,255,0.75);font-size:0.74rem;
                      margin-bottom:6px">Estado actual</div>
          <div style="color:white;font-weight:600;font-size:0.92rem">
            {usuaria}</div>
          <div style="color:rgba(255,255,255,0.85);font-size:0.75rem;
                      margin-top:4px">📍 {gps_coords}</div>
          {contact_pill}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Aceleracion ───────────────────────────────────────────────────────────────

def render_aceleracion(accel: float, umbral: float) -> None:
    """RF-D04, D05: Valor grande coloreado + barra de progreso dinamica."""
    pct = min(accel / umbral, 1.0) if umbral else 0.0
    superado = accel >= umbral
    val_color = "#ef4444" if superado else "#1e293b"
    bar_color = "#ef4444" if superado else "#22c55e"
    nota = (
        f"↑ Umbral: {umbral:.1f} m/s² — SUPERADO"
        if superado
        else f"Umbral: {umbral:.1f} m/s²"
    )
    nota_color = "#ef4444" if superado else "#94a3b8"

    st.markdown(
        f"""
        <div style="margin-bottom:4px">
          <div style="color:#374151;font-size:0.82rem;font-weight:600">
            Aceleración detectada</div>
          <div style="color:#94a3b8;font-size:0.74rem;margin-bottom:2px">
            Aceleración actual</div>
          <div style="color:{val_color};font-size:2.6rem;font-weight:700;
                      line-height:1;margin:4px 0">
            {accel:.1f}
            <span style="font-size:1rem;font-weight:400;color:#94a3b8">m/s²</span>
          </div>
        </div>
        <style>
          [data-testid="stProgress"] > div > div {{
            background-color: {bar_color} !important;
          }}
          [data-testid="stProgress"] > div {{
            background-color: #e2e8f0 !important;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.progress(pct)
    st.markdown(
        f"<div style='color:{nota_color};font-size:0.76rem;margin-top:2px;"
        f"margin-bottom:14px'>{nota}</div>",
        unsafe_allow_html=True,
    )


# ── Flujo interno ─────────────────────────────────────────────────────────────

def render_flujo(estado: str) -> None:
    """RF-D06: Nodos DETECTAR -> VERIFICAR -> ESCALAR con color dinamico."""
    color = COLORES.get(estado, "#888")
    nodos = ["DETECTAR", "VERIFICAR", "ESCALAR"]
    activos: dict[str, list[bool]] = {
        "NORMAL":      [True, False, False],
        "VERIFICANDO": [False, True, False],
        "ALERTA":      [False, False, True],
        "RESUELTO":    [False, False, False],
    }
    estados_nodos = activos.get(estado, [False, False, False])

    pills_html = ""
    for nodo, activo in zip(nodos, estados_nodos):
        bg = color if activo else "#e2e8f0"
        txt = "white" if activo else "#6b7280"
        pills_html += (
            f"<div style='"
            f"background:{bg};color:{txt};"
            f"padding:7px 0;border-radius:8px;text-align:center;"
            f"font-size:0.75rem;font-weight:600;flex:1'>{nodo}</div>"
        )

    st.markdown(
        f"""
        <div style="margin-bottom:14px">
          <div style="color:#374151;font-size:0.82rem;font-weight:600;
                      margin-bottom:6px">Flujo interno de la pulsera</div>
          <div style="display:flex;gap:6px">{pills_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Countdown (VERIFICANDO) ───────────────────────────────────────────────────

def calcular_countdown(data: dict[str, Any]) -> int:
    """RF-D07: Calcula countdown real desde timestamp_inicio_verificando."""
    estado = data.get("estado", "NORMAL")
    if estado == "VERIFICANDO" and data.get("timestamp_inicio_verificando"):
        try:
            inicio = datetime.fromisoformat(data["timestamp_inicio_verificando"])
            ahora_dt = datetime.now(timezone.utc)
            elapsed = (ahora_dt - inicio).total_seconds()
            return max(0, int(TIEMPO_VERIFICACION - elapsed))
        except Exception:
            pass
    return data.get("countdown_restante", 0)


def render_countdown(data: dict[str, Any]) -> None:
    """RF-D07, D08, D09: Countdown grande + boton CANCELAR en VERIFICANDO."""
    countdown = calcular_countdown(data)
    st.markdown(
        f"""
        <div style="
            background:#fef3c7;border:1px solid #eab308;
            border-radius:12px;padding:14px;text-align:center;
            margin-bottom:8px">
          <div style="color:#92400e;font-size:0.88rem;font-weight:600">
            ⚠️ Verificando aceleración...</div>
          <div style="color:#ef4444;font-size:2.8rem;font-weight:700;
                      line-height:1.1">{countdown}s</div>
          <div style="color:#b45309;font-size:0.76rem">
            Si no cancela, se escalará la alerta</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("✅ CANCELAR ALERTA", type="secondary"):
        try:
            requests.get("http://localhost:5000/cancel", timeout=2)
        except Exception:
            pass


# ── Contactos de emergencia ───────────────────────────────────────────────────

def render_contactos_emergencia(contacto: str) -> None:
    """Contactos de emergencia — solo los definidos en config.py."""
    # Parsear "Maria Flores (mama)" → nombre, relación, iniciales
    partes = contacto.split("(")
    nombre = partes[0].strip()
    relacion = partes[1].rstrip(")").strip() if len(partes) > 1 else "contacto"
    iniciales = "".join(p[0].upper() for p in nombre.split()[:2])

    fila = (
        f"<div style='display:flex;align-items:center;gap:10px;"
        f"padding:9px 0'>"
        f"<div style='width:34px;height:34px;border-radius:50%;"
        f"background:#4f46e5;display:flex;align-items:center;"
        f"justify-content:center;color:white;font-size:0.72rem;"
        f"font-weight:700;flex-shrink:0'>{iniciales}</div>"
        f"<div style='flex:1'>"
        f"<div style='color:#1e293b;font-size:0.83rem;font-weight:500'>{nombre}</div>"
        f"<div style='color:#94a3b8;font-size:0.72rem'>{relacion}</div>"
        f"</div>"
        f"<div style='width:8px;height:8px;border-radius:50%;"
        f"background:#22c55e'></div>"
        f"</div>"
    )

    st.markdown(
        f"""
        <div style="background:white;border-radius:12px;
                    padding:12px 16px;margin-bottom:12px;
                    border:1px solid #e2e8f0;
                    box-shadow:0 1px 3px rgba(0,0,0,0.05)">
          <div style="color:#374151;font-size:0.82rem;font-weight:600;
                      margin-bottom:2px">Contactos de emergencia</div>
          {fila}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Semaforo ──────────────────────────────────────────────────────────────────

def render_semaforo_legend() -> None:
    """Leyenda semaforo al pie de la columna izquierda."""
    items = [
        ("#22c55e", "Normal"),
        ("#eab308", "Verificando"),
        ("#ef4444", "Alerta"),
        ("#6b7280", "Resuelto"),
    ]
    dots = "".join(
        f"<span style='display:inline-flex;align-items:center;gap:3px;"
        f"margin-right:8px;color:#6b7280;font-size:0.7rem;white-space:nowrap'>"
        f"<span style='width:8px;height:8px;border-radius:50%;"
        f"background:{c};display:inline-block;flex-shrink:0'></span>{lbl}</span>"
        for c, lbl in items
    )
    st.markdown(
        f"""
        <div style='margin-top:6px;margin-bottom:8px;
                    background:white;border-radius:10px;
                    padding:10px 12px;border:1px solid #e2e8f0'>
          <div style='color:#374151;font-size:0.74rem;font-weight:600;
                      margin-bottom:5px'>Semaforización de estados:</div>
          <div style='display:flex;flex-wrap:wrap;gap:4px 0'>{dots}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Banner de estado (sobre el mapa) ─────────────────────────────────────────

def render_state_banner(estado: str) -> None:
    """Banner VERIFICANDO/ALERTA sobre el mapa en columna derecha."""
    if estado == "VERIFICANDO":
        st.markdown(
            "<div style='"
            "background:#fef3c7;color:#92400e;padding:10px 16px;"
            "border-radius:8px;margin-bottom:8px;font-size:0.87rem;"
            "border:1px solid #eab308;font-weight:500'>"
            "⚠️ Verificando aceleración — en espera de confirmación"
            "</div>",
            unsafe_allow_html=True,
        )
    elif estado == "ALERTA":
        st.markdown(
            "<div style='"
            "background:#fef2f2;color:#991b1b;padding:10px 16px;"
            "border-radius:8px;margin-bottom:8px;font-size:0.87rem;"
            "border:1px solid #ef4444;font-weight:600'>"
            "⚠️ ALERTA ACTIVA — Contacto notificado"
            "</div>",
            unsafe_allow_html=True,
        )


# ── Mapa ──────────────────────────────────────────────────────────────────────

def construir_mapa(
    lat: float,
    lon: float,
    estado: str,
    usuaria: str,
    direccion_ref: str,
    gps_activo: bool,
) -> folium.Map:
    """RF-D11, D12: Construye mapa Folium con marcador coloreado por estado."""
    icon_color: dict[str, str] = {
        "NORMAL": "green",
        "VERIFICANDO": "orange",
        "ALERTA": "red",
        "RESUELTO": "gray",
    }

    m = folium.Map(
        location=[lat, lon],
        zoom_start=15,
        tiles="OpenStreetMap",
    )

    popup_text = f"{usuaria} — {estado}"
    if gps_activo:
        popup_text += f"\n{lat:.5f}, {lon:.5f}"

    folium.Marker(
        [lat, lon],
        popup=popup_text,
        tooltip=f"\U0001f4cd {'GPS activo' if gps_activo else direccion_ref}",
        icon=folium.Icon(
            color=icon_color.get(estado, "gray"), icon="user", prefix="fa"
        ),
    ).add_to(m)

    return m


def render_mapa(data: dict[str, Any], session_state: Any) -> None:
    """RF-D11, D12: Mapa con barra GPS debajo. Borde rojo en ALERTA."""
    gps_lat = data.get("lat", UBICACION_LAT)
    gps_lon = data.get("lon", UBICACION_LON)
    direccion_ref = data.get("direccion", DIRECCION)
    estado = data.get("estado", "NORMAL")
    usuaria = data.get("usuaria", USUARIA)
    gps_activo = gps_lat != UBICACION_LAT or gps_lon != UBICACION_LON

    gps_cambio = (
        abs(gps_lat - (session_state.ultimo_lat or gps_lat)) > UMBRAL_MOVIMIENTO_GPS
        or abs(gps_lon - (session_state.ultimo_lon or gps_lon))
        > UMBRAL_MOVIMIENTO_GPS
    )
    mapa_reconstruir = session_state.ultimo_estado != estado or gps_cambio

    if mapa_reconstruir:
        m = construir_mapa(
            gps_lat, gps_lon, estado, usuaria, direccion_ref, gps_activo
        )
        session_state.mapa_html = m._repr_html_()
        session_state.ultimo_estado = estado
        session_state.ultimo_lat = gps_lat
        session_state.ultimo_lon = gps_lon

    if session_state.mapa_html is not None:
        border_css = ""
        if estado == "ALERTA":
            border_css = (
                "<style>[data-testid='stIFrame']{"
                "border:2px solid #ef4444 !important;"
                "border-radius:8px !important;}</style>"
            )
            st.markdown(border_css, unsafe_allow_html=True)
        st.components.v1.html(session_state.mapa_html, height=330)

    # Barra GPS oscura debajo del mapa (igual que en Figma)
    coords_text = f"{gps_lat:.6f}, {gps_lon:.6f}"
    city_text = direccion_ref if not gps_activo else "GPS activo"
    st.markdown(
        f"""
        <div style="
            background:#1e293b;border-radius:8px;
            padding:8px 16px;margin-top:4px;margin-bottom:12px;
            display:flex;justify-content:space-between;align-items:center">
          <span style="color:#22c55e;font-size:0.8rem;font-family:monospace">
            📍 {coords_text}</span>
          <span style="color:#94a3b8;font-size:0.76rem">{city_text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Historial ─────────────────────────────────────────────────────────────────

def render_historial(data: dict[str, Any]) -> None:
    """RF-D14: Historial con badge coloreado y aceleracion a la derecha."""
    st.markdown(
        "<div style='color:#374151;font-size:0.88rem;font-weight:600;"
        "margin-bottom:8px'>Historial de eventos</div>",
        unsafe_allow_html=True,
    )
    historial = data.get("historial", [])
    if not historial:
        st.markdown(
            "<div style='background:white;border-radius:12px;"
            "padding:12px 16px;color:#94a3b8;font-size:0.82rem;"
            "font-style:italic;border:1px solid #e2e8f0'>"
            "Sin eventos registrados</div>",
            unsafe_allow_html=True,
        )
        return

    rows_html = ""
    for evento in reversed(historial):
        estado_ev = evento.get("estado", "?")
        ts = evento.get("timestamp", "")
        acc = evento.get("aceleracion", 0)
        cancelado = evento.get("cancelado", False)
        escalado = evento.get("escalado", False)
        forzado = evento.get("forzado", False)

        badge_color = COLORES.get(estado_ev, "#6b7280")
        ts_corto = ts.split("T")[1].split(".")[0][:8] if "T" in ts else ts[:8]

        if cancelado:
            desc = "Cancelado manualmente"
        elif escalado:
            desc = "Escalado automático"
        elif forzado:
            desc = "Forzado (debug)"
        else:
            desc = "Aceleración alta" if acc > 5 else "Aceleración normal"

        rows_html += (
            f"<div style='display:flex;align-items:center;gap:8px;"
            f"padding:8px 0;border-bottom:1px solid #f1f5f9'>"
            f"<span style='color:#94a3b8;font-size:0.72rem;"
            f"font-family:monospace;flex-shrink:0;min-width:48px'>{ts_corto}</span>"
            f"<span style='background:{badge_color};color:white;"
            f"padding:2px 7px;border-radius:10px;font-size:0.68rem;"
            f"font-weight:700;flex-shrink:0'>{estado_ev}</span>"
            f"<span style='color:#374151;font-size:0.78rem;flex:1'>{desc}</span>"
            f"<span style='color:#94a3b8;font-size:0.72rem;"
            f"font-family:monospace;flex-shrink:0'>{acc:.1f} m/s²</span>"
            f"</div>"
        )

    # Altura fija para ~5 filas (~45px c/u); scroll para ver el resto
    st.markdown(
        f"<div style='background:white;border-radius:12px;"
        f"padding:8px 16px;margin-bottom:12px;"
        f"border:1px solid #e2e8f0;"
        f"box-shadow:0 1px 3px rgba(0,0,0,0.05);"
        f"max-height:230px;overflow-y:auto'>{rows_html}</div>",
        unsafe_allow_html=True,
    )


# ── Panel de control demo ─────────────────────────────────────────────────────

def render_controles_demo(estado: str) -> None:
    """RF-09, RF-10: Panel de control manual para demostracion ante jurado."""
    # Título de la sección (sin abrir div que abarque widgets nativos de Streamlit)
    st.markdown(
        "<div style='color:#374151;font-size:0.85rem;font-weight:600;"
        "margin-bottom:8px;margin-top:4px'>🎛️ Panel de control — Demo</div>",
        unsafe_allow_html=True,
    )

    col_v, col_a, col_r, col_n = st.columns(4)

    with col_v:
        if st.button(
            "🟡 Forzar VERIF.",
            disabled=estado == "VERIFICANDO",
            use_container_width=True,
            help="Simula detección de movimiento anómalo e inicia el countdown",
        ):
            try:
                requests.get(
                    "http://localhost:5000/trigger?estado=VERIFICANDO", timeout=2
                )
            except Exception:
                pass

    with col_a:
        if st.button(
            "🔴 Forzar ALERTA",
            disabled=estado == "ALERTA",
            use_container_width=True,
            help="Escala directamente a estado de alerta y notifica al contacto",
        ):
            try:
                requests.get(
                    "http://localhost:5000/trigger?estado=ALERTA", timeout=2
                )
            except Exception:
                pass

    with col_r:
        if st.button(
            "🔵 Forzar RESOL.",
            disabled=estado == "RESUELTO",
            use_container_width=True,
            help="Marca el evento como resuelto",
        ):
            try:
                requests.get(
                    "http://localhost:5000/trigger?estado=RESUELTO", timeout=2
                )
            except Exception:
                pass

    with col_n:
        if st.button(
            "🟢 Forzar NORMAL",
            disabled=estado == "NORMAL",
            use_container_width=True,
            help="Regresa al monitoreo normal",
        ):
            try:
                requests.get(
                    "http://localhost:5000/trigger?estado=NORMAL", timeout=2
                )
            except Exception:
                pass

    if st.button(
        "🔄 Reiniciar sistema (limpiar historial)",
        type="secondary",
        use_container_width=True,
        help="Borra el historial, cancela todos los timers y vuelve a NORMAL.",
    ):
        try:
            requests.get("http://localhost:5000/reset", timeout=2)
        except Exception:
            pass


# ── Footer ────────────────────────────────────────────────────────────────────

def render_footer(estado: str) -> None:
    """Footer dark-navy con version, timestamp y dot indicador."""
    color = COLORES.get(estado, "#888")
    hora = datetime.now().strftime("%H:%M:%S")
    st.markdown(
        f"""
        <div style="
            background:{NAVY};
            margin-top:24px;
            padding:16px 32px;
            text-align:center;
            border-radius:10px">
          <div style="color:#94a3b8;font-size:0.82rem">
            SAFE-PATH — Sistema de seguridad preventiva con pulsera inteligente</div>
          <div style="color:#64748b;font-size:0.74rem;margin-top:4px">
            Lima, Perú · v1.0 · Última actualización: {hora}</div>
          <div style="margin-top:8px">
            <span style="
                display:inline-block;width:10px;height:10px;
                border-radius:50%;background:{color};
                box-shadow:0 0 8px {color}"></span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
