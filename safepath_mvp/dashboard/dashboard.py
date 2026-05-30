"""SAFE-PATH - Dashboard Streamlit (Dimension 2: Dashboard Web).

Lee state.json cada segundo y renderiza el estado del sistema
en tiempo real con mapa, indicadores y flujo visual.
"""

import json
import time

import streamlit as st

from safepath_mvp.dashboard.components import (
    inject_global_css,
    render_aceleracion,
    render_contactos_emergencia,
    render_controles_demo,
    render_countdown,
    render_estado,
    render_flujo,
    render_header,
    render_historial,
    render_mapa,
    render_semaforo_legend,
    render_state_banner,
)
from safepath_mvp.shared.schema import ESTADO_INICIAL
from safepath_mvp.simulador.config import (
    CONTACTO,
    UBICACION_LAT,
    UBICACION_LON,
    UMBRAL_ACELERACION,
    USUARIA,
)

st.set_page_config(
    page_title="SAFE-PATH - Panel de seguridad",
    page_icon="\U0001f7e3",
    layout="wide",
    menu_items={},
)


def load_state() -> dict:
    """RF-D17: Lee state.json con tolerancia a fallos."""
    try:
        with open("safepath_mvp/state.json", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.session_state["_state_error"] = "state.json no encontrado. Mostrando valores por defecto."
        return dict(ESTADO_INICIAL)
    except Exception as exc:
        st.session_state["_state_error"] = f"state.json corrupto o ilegible: {exc}. Mostrando valores por defecto."
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
    err = st.session_state.pop("_state_error", None)
    if err:
        st.error(err)
    estado = data.get("estado", "NORMAL")
    usuaria = data.get("usuaria", USUARIA)
    contacto = data.get("contacto", CONTACTO)

    init_session()

    # 1. CSS global y header dark-navy
    inject_global_css()
    render_header(estado)

    # 2. GPS texto para render_estado
    gps_lat = data.get("lat", UBICACION_LAT)
    gps_lon = data.get("lon", UBICACION_LON)
    gps_activo = gps_lat != UBICACION_LAT or gps_lon != UBICACION_LON
    gps_texto = (
        f"GPS: {gps_lat:.6f}, {gps_lon:.6f}"
        if gps_activo
        else "GPS: usando ubicacion de referencia"
    )

    # 3. Layout de 2 columnas (~35 / 65)
    col1, col2 = st.columns([1, 1.8])

    with col1:
        render_estado(estado, usuaria, gps_texto, contacto)
        render_aceleracion(
            data.get("aceleracion_actual", 0),
            data.get("umbral", UMBRAL_ACELERACION),
        )
        render_flujo(estado)
        # RD02: st.empty() fija una posicion estable en el arbol de widgets,
        # evitando que el diff de Streamlit duplique render_flujo al
        # agregar/quitar render_countdown en cada ciclo de rerun.
        _countdown_slot = st.empty()
        if estado == "VERIFICANDO":
            with _countdown_slot.container():
                render_countdown(data)
        else:
            _countdown_slot.empty()
        render_contactos_emergencia(contacto)
        render_semaforo_legend()

    with col2:
        render_state_banner(estado)
        render_mapa(data, st.session_state)
        render_historial(data)
        render_controles_demo(estado)

    time.sleep(1)
    st.rerun()


render()
