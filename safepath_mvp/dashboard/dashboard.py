"""SAFE-PATH - Dashboard Streamlit (Dimension 2: Dashboard Web).

Lee state.json cada segundo y renderiza el estado del sistema
en tiempo real con mapa, indicadores y flujo visual.
"""

import streamlit as st
import json
import time
from .components import (
    COLORES,
    EMOJIS,
    render_header,
    render_estado,
    render_aceleracion,
    render_flujo,
    render_countdown,
    render_mapa,
    render_historial,
)
from ..simulador.config import USUARIA, CONTACTO, UBICACION_LAT, UBICACION_LON, DIRECCION, UMBRAL_ACELERACION
from ..shared.schema import ESTADO_INICIAL

st.set_page_config(
    page_title="SAFE-PATH - Panel de seguridad",
    page_icon="\U0001f7e3",
    layout="wide",
)


def load_state() -> dict:
    """RF-D17: Lee state.json con tolerancia a fallos."""
    try:
        with open("safepath_mvp/state.json", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dict(ESTADO_INICIAL)


def init_session() -> None:
    """Inicializa variables de session_state para el mapa."""
    if "ultimo_estado" not in st.session_state:
        st.session_state.ultimo_estado = None
    if "ultimo_lat" not in st.session_state:
        st.session_state.ultimo_lat = None
    if "ultimo_lon" not in st.session_state:
        st.session_state.ultimo_lon = None
    if "mapa_html" not in st.session_state:
        st.session_state.mapa_html = None


def render() -> None:
    """Orquestador principal: carga estado y renderiza todos los componentes."""
    data = load_state()
    estado = data.get("estado", "NORMAL")
    color = COLORES.get(estado, "#888")
    emoji = EMOJIS.get(estado, "\u26aa")
    usuaria = data.get("usuaria", USUARIA)
    contacto = data.get("contacto", CONTACTO)

    init_session()

    render_header(estado)

    col1, col2 = st.columns([1, 1.4])

    gps_lat = data.get("lat", UBICACION_LAT)
    gps_lon = data.get("lon", UBICACION_LON)
    gps_activo = gps_lat != UBICACION_LAT or gps_lon != UBICACION_LON
    gps_texto = (
        f"\U0001f4cd GPS: {gps_lat:.6f}, {gps_lon:.6f}"
        if gps_activo
        else f"\U0001f4cd GPS: usando ubicacion de referencia"
    )

    with col1:
        render_estado(estado, usuaria, gps_texto, contacto)
        st.markdown("---")
        render_aceleracion(
            data.get("aceleracion_actual", 0),
            data.get("umbral", UMBRAL_ACELERACION),
        )
        st.markdown("---")
        render_flujo(estado)
        if estado == "VERIFICANDO":
            render_countdown(data)

    with col2:
        render_mapa(data, st.session_state)
        render_historial(data)

    time.sleep(1)
    st.rerun()


render()
