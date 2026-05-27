"""Componentes visuales del dashboard SAFE-PATH.

Cada funcion renderiza una seccion especifica de la UI.
Separado de dashboard.py para permitir desarrollo en paralelo.
"""

from __future__ import annotations

import streamlit as st
import folium
import requests
import os
from datetime import datetime, timezone
from typing import Any
from ..simulador.config import (
    USUARIA,
    CONTACTO,
    UBICACION_LAT,
    UBICACION_LON,
    UMBRAL_MOVIMIENTO_GPS,
    TIEMPO_VERIFICACION,
    DIRECCION,
    UMBRAL_ACELERACION,
)
from ..shared.schema import (
    COLOR_NORMAL,
    COLOR_VERIFICANDO,
    COLOR_ALERTA,
    COLOR_RESUELTO,
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


def render_header(estado: str) -> None:
    """RF-D02: Titulo del dashboard con color dinamico segun estado."""
    color = COLORES.get(estado, "#888")
    st.markdown(
        f"<h1 style='color:{color}'>\U0001f7e3 SAFE-PATH "
        f"<span style='font-size:0.6em'>Panel de seguridad preventiva</span></h1>",
        unsafe_allow_html=True,
    )


def render_estado(
    estado: str, usuaria: str, gps_texto: str, contacto: str
) -> None:
    """RF-D02, D03, D10: Indicador de estado + contacto notificado en ALERTA."""
    color = COLORES.get(estado, "#888")
    emoji = EMOJIS.get(estado, "\u26aa")

    # Imagen de la pulsera (RF-D16)
    img_path = os.path.join("safepath_mvp", "assets", "pulsera.png")
    if os.path.exists(img_path):
        _, img_col, _ = st.columns([1, 2, 1])
        with img_col:
            st.image(img_path, width=180)
    else:
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    st.markdown(
        f"<div style='background:{color};padding:20px;border-radius:12px;"
        f"text-align:center'>"
        f"<h2 style='color:white;margin:0'>{emoji} {estado}</h2>"
        f"<p style='color:white;margin:4px 0'>{usuaria}</p>"
        f"<p style='color:rgba(255,255,255,0.8);font-size:0.85em'>"
        f"{gps_texto}</p></div>",
        unsafe_allow_html=True,
    )

    if estado == "ALERTA":
        st.markdown(
            f"<div style='background:#FEE2E2;padding:12px;border-radius:8px;"
            f"text-align:center;border:2px solid #ef4444;margin-top:10px'>"
            f"<p style='color:#991B1B;margin:0'>"
            f"<b>\u26a0\ufe0f Contacto notificado:</b> {contacto}</p></div>",
            unsafe_allow_html=True,
        )


def render_aceleracion(accel: float, umbral: float) -> None:
    """RF-D04, D05: Barra de progreso + metrica numerica de aceleracion."""
    st.markdown("**Aceleracion detectada**")
    pct = min(accel / (umbral * 1.5), 1.0)
    st.metric(
        "Aceleracion actual",
        f"{accel:.1f} m/s\u00b2",
        delta=f"Umbral: {umbral} m/s\u00b2",
    )
    st.progress(pct)


def render_flujo(estado: str) -> None:
    """RF-D06: Nodos DETECTAR -> VERIFICAR -> ESCALAR con color dinamico."""
    st.markdown("**Flujo interno de la pulsera**")
    color = COLORES.get(estado, "#888")
    nodos = ["DETECTAR", "VERIFICAR", "ESCALAR"]
    activos: dict[str, list[bool]] = {
        "NORMAL": [False, False, False],
        "VERIFICANDO": [True, True, False],
        "ALERTA": [True, True, True],
        "RESUELTO": [True, True, True],
    }
    estados_nodos = activos.get(estado, [False, False, False])

    cols = st.columns(3)
    for i, (nodo, activo) in enumerate(zip(nodos, estados_nodos)):
        bg = color if activo else "#E0E0E0"
        txt = "white" if activo else "#888"
        cols[i].markdown(
            f"<div style='background:{bg};padding:8px;border-radius:8px;"
            f"text-align:center'><b style='color:{txt}'>{nodo}</b></div>",
            unsafe_allow_html=True,
        )


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
    st.markdown("---")
    countdown = calcular_countdown(data)
    st.markdown(
        f"<div style='background:#FEF3CD;padding:16px;border-radius:12px;"
        f"text-align:center;border:2px solid #eab308'>"
        f"<h2 style='color:#854F0B;margin:0'>\u26a0\ufe0f Verificando...</h2>"
        f"<h1 style='color:#ef4444;margin:8px 0'>{countdown}s</h1>"
        f"<p style='color:#666'>Si no cancela, se escalara la alerta</p>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if st.button("\u2705 CANCELAR ALERTA", type="secondary"):
        try:
            requests.get("http://localhost:5000/cancel", timeout=2)
        except Exception:
            pass


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
        tiles="CartoDB positron",
    )

    popup_text = f"{usuaria} \u2014 {estado}"
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
    """RF-D11, D12: Renderiza mapa; reconstruye solo si estado o GPS cambian."""
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
        st.components.v1.html(session_state.mapa_html, height=330)


def render_controles_demo(estado: str) -> None:
    """RF-09, RF-10: Panel de control manual para demostracion ante jurado.

    Permite al operador forzar cualquier estado del sistema y reiniciarlo
    sin necesidad de sacudir el dispositivo sensor ni reiniciar la aplicacion.
    """
    st.markdown("---")
    st.markdown("**🎛️ Panel de control — Demo**")

    col_v, col_a, col_r, col_n = st.columns(4)

    with col_v:
        disabled_v = estado == "VERIFICANDO"
        if st.button(
            "🟡 Forzar VERIFICANDO",
            disabled=disabled_v,
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
        disabled_a = estado == "ALERTA"
        if st.button(
            "🔴 Forzar ALERTA",
            disabled=disabled_a,
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
        disabled_r = estado == "RESUELTO"
        if st.button(
            "🔵 Forzar RESUELTO",
            disabled=disabled_r,
            use_container_width=True,
            help="Marca el evento como resuelto (espera automática de 5s antes de volver a NORMAL)",
        ):
            try:
                requests.get(
                    "http://localhost:5000/trigger?estado=RESUELTO", timeout=2
                )
            except Exception:
                pass

    with col_n:
        disabled_n = estado == "NORMAL"
        if st.button(
            "🟢 Forzar NORMAL",
            disabled=disabled_n,
            use_container_width=True,
            help="Regresa al monitoreo normal sin cancelar ni notificar",
        ):
            try:
                requests.get(
                    "http://localhost:5000/trigger?estado=NORMAL", timeout=2
                )
            except Exception:
                pass

    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
    if st.button(
        "🔄 Reiniciar sistema (limpiar historial)",
        type="secondary",
        use_container_width=True,
        help="Borra el historial, cancela todos los timers y vuelve a NORMAL. Úsalo entre demostraciones.",
    ):
        try:
            requests.get("http://localhost:5000/reset", timeout=2)
        except Exception:
            pass


def render_historial(data: dict[str, Any]) -> None:
    """RF-D14: Lista de ultimos eventos con timestamps formateados."""
    color = COLORES.get(data.get("estado", "NORMAL"), "#888")
    st.markdown("**Historial de eventos**")
    historial = data.get("historial", [])
    if historial:
        for evento in reversed(historial):
            estado_ev = evento.get("estado", "?")
            ts = evento.get("timestamp", "")
            acc = evento.get("aceleracion", 0)
            cancelado = evento.get("cancelado", False)
            escalado = evento.get("escalado", False)
            forzado = evento.get("forzado", False)

            tag = ""
            if cancelado:
                tag = " \u2705 Cancelado manualmente"
            elif escalado:
                tag = " \u26a0\ufe0f Escalado automatico"
            elif forzado:
                tag = " \U0001f527 Forzado (debug)"

            ts_corto = (
                ts.split("T")[1].split(".")[0][:8] if "T" in ts else ts[:8]
            )
            st.markdown(
                f"<div style='font-family:monospace;font-size:0.85em;"
                f"padding:4px 8px;border-left:3px solid {color};"
                f"margin:2px 0'>"
                f"{ts_corto}  \u2192 {estado_ev}{tag}"
                f"<span style='color:#888;margin-left:12px'>"
                f"({acc:.1f} m/s\u00b2)</span></div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown("*Sin eventos registrados*")
