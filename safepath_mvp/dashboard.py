import streamlit as st
import json, time, folium, requests, os
from datetime import datetime, timezone
from config import *
from schema import ESTADO_INICIAL, COLOR_NORMAL, COLOR_VERIFICANDO, COLOR_ALERTA, COLOR_RESUELTO


st.set_page_config(
    page_title="SAFE-PATH — Panel de seguridad",
    page_icon="🟣",
    layout="wide"
)


def load_state():
    try:
        with open("state.json", encoding="utf-8") as f:
            return json.load(f)
    except:
        return dict(ESTADO_INICIAL)


# ── Paleta SafeCorp (desde schema.py) ──────────────────────────
COLORES = {
    "NORMAL":      COLOR_NORMAL,
    "VERIFICANDO": COLOR_VERIFICANDO,
    "ALERTA":      COLOR_ALERTA,
    "RESUELTO":    COLOR_RESUELTO,
}

EMOJIS = {
    "NORMAL":      "🟢",
    "VERIFICANDO": "🟡",
    "ALERTA":      "🔴",
    "RESUELTO":    "🔵",
}


def init_session():
    if "ultimo_estado" not in st.session_state:
        st.session_state.ultimo_estado = None
    if "ultimo_lat" not in st.session_state:
        st.session_state.ultimo_lat = None
    if "ultimo_lon" not in st.session_state:
        st.session_state.ultimo_lon = None
    if "mapa_html" not in st.session_state:
        st.session_state.mapa_html = None


def calcular_countdown(data):
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


def construir_mapa(lat, lon, estado, usuaria, direccion_ref, gps_activo):
    icon_color = {
        "NORMAL": "green",
        "VERIFICANDO": "orange",
        "ALERTA": "red",
        "RESUELTO": "gray",
    }.get(estado, "gray")

    m = folium.Map(
        location=[lat, lon],
        zoom_start=15,
        tiles="CartoDB positron"
    )

    popup_text = f"{usuaria} — {estado}"
    if gps_activo:
        popup_text += f"\n{lat:.5f}, {lon:.5f}"

    folium.Marker(
        [lat, lon],
        popup=popup_text,
        tooltip=f"📍 {'GPS activo' if gps_activo else direccion_ref}",
        icon=folium.Icon(color=icon_color, icon="user", prefix="fa")
    ).add_to(m)

    return m


def render():
    data = load_state()
    estado = data.get("estado", "NORMAL")
    color = COLORES.get(estado, "#888")
    emoji = EMOJIS.get(estado, "⚪")
    usuaria = data.get("usuaria", USUARIA)
    contacto = data.get("contacto", CONTACTO)

    init_session()

    # ── Header ────────────────────────────────────────────────
    st.markdown(
        f"<h1 style='color:{color}'>🟣 SAFE-PATH "
        f"<span style='font-size:0.6em'>Panel de seguridad preventiva</span></h1>",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([1, 1.4])

    gps_lat = data.get("lat", UBICACION_LAT)
    gps_lon = data.get("lon", UBICACION_LON)
    direccion_ref = data.get("direccion", DIRECCION)
    gps_activo = (gps_lat != UBICACION_LAT or gps_lon != UBICACION_LON)
    gps_texto = f"📍 GPS: {gps_lat:.6f}, {gps_lon:.6f}" if gps_activo else f"📍 GPS: usando ubicación de referencia"

    # ── Columna izquierda ─────────────────────────────────────
    with col1:
        # Imagen de la pulsera (RF-D16)
        img_path = os.path.join("assets", "pulsera.png")
        if os.path.exists(img_path):
            _, img_col, _ = st.columns([1, 2, 1])
            with img_col:
                st.image(img_path, width=180)
        else:
            st.markdown(
                "<div style='height:20px'></div>",
                unsafe_allow_html=True
            )

        # Indicador de estado
        st.markdown(
            f"<div style='background:{color};padding:20px;border-radius:12px;"
            f"text-align:center'>"
            f"<h2 style='color:white;margin:0'>{emoji} {estado}</h2>"
            f"<p style='color:white;margin:4px 0'>{usuaria}</p>"
            f"<p style='color:rgba(255,255,255,0.8);font-size:0.85em'>"
            f"{gps_texto}</p></div>",
            unsafe_allow_html=True
        )

        # Contacto notificado en ALERTA (RF-D10)
        if estado == "ALERTA":
            st.markdown(
                f"<div style='background:#FEE2E2;padding:12px;border-radius:8px;"
                f"text-align:center;border:2px solid #ef4444;margin-top:10px'>"
                f"<p style='color:#991B1B;margin:0'>"
                f"<b>⚠️ Contacto notificado:</b> {contacto}</p></div>",
                unsafe_allow_html=True
            )

        st.markdown("---")

        # Aceleración
        st.markdown("**Aceleración detectada**")
        accel = data.get("aceleracion_actual", 0)
        umbral = data.get("umbral", UMBRAL_ACELERACION)
        pct = min(accel / (umbral * 1.5), 1.0)
        st.metric("Aceleración actual", f"{accel:.1f} m/s²",
                  delta=f"Umbral: {umbral} m/s²")
        st.progress(pct)

        st.markdown("---")

        # Flujo D→V→E
        st.markdown("**Flujo interno de la pulsera**")
        nodos = ["DETECTAR", "VERIFICAR", "ESCALAR"]
        activos = {
            "NORMAL":      [False, False, False],
            "VERIFICANDO": [True,  True,  False],
            "ALERTA":      [True,  True,  True],
            "RESUELTO":    [True,  True,  True],
        }.get(estado, [False, False, False])

        cols = st.columns(3)
        for i, (nodo, activo) in enumerate(zip(nodos, activos)):
            bg = color if activo else "#E0E0E0"
            txt = "white" if activo else "#888"
            cols[i].markdown(
                f"<div style='background:{bg};padding:8px;border-radius:8px;"
                f"text-align:center'><b style='color:{txt}'>{nodo}</b></div>",
                unsafe_allow_html=True
            )

        # Countdown + botón cancelar (VERIFICANDO)
        if estado == "VERIFICANDO":
            st.markdown("---")
            countdown = calcular_countdown(data)
            st.markdown(
                f"<div style='background:#FEF3CD;padding:16px;border-radius:12px;"
                f"text-align:center;border:2px solid #eab308'>"
                f"<h2 style='color:#854F0B;margin:0'>⚠️ Verificando...</h2>"
                f"<h1 style='color:#ef4444;margin:8px 0'>{countdown}s</h1>"
                f"<p style='color:#666'>Si no cancela, se escalará la alerta</p>"
                f"</div>",
                unsafe_allow_html=True
            )
            if st.button("✅ CANCELAR ALERTA", type="secondary"):
                try:
                    requests.get("http://localhost:5000/cancel", timeout=2)
                except Exception:
                    pass

    # ── Columna derecha ────────────────────────────────────────
    with col2:
        # Mapa: pre-renderizar HTML solo al cambiar estado o moverme (RD01)
        gps_cambio = (
            abs(gps_lat - (st.session_state.ultimo_lat or gps_lat)) > UMBRAL_MOVIMIENTO_GPS
            or abs(gps_lon - (st.session_state.ultimo_lon or gps_lon)) > UMBRAL_MOVIMIENTO_GPS
        )
        mapa_reconstruir = (
            st.session_state.ultimo_estado != estado
            or gps_cambio
        )

        if mapa_reconstruir:
            m = construir_mapa(gps_lat, gps_lon, estado, usuaria, direccion_ref, gps_activo)
            st.session_state.mapa_html = m._repr_html_()
            st.session_state.ultimo_estado = estado
            st.session_state.ultimo_lat = gps_lat
            st.session_state.ultimo_lon = gps_lon

        if st.session_state.mapa_html is not None:
            st.components.v1.html(st.session_state.mapa_html, height=330)

        # Historial (RF-D14)
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
                    tag = " ✅ Cancelado manualmente"
                elif escalado:
                    tag = " ⚠️ Escalado automático"
                elif forzado:
                    tag = " 🔧 Forzado (debug)"

                ts_corto = ts.split("T")[1].split(".")[0][:8] if "T" in ts else ts[:8]
                st.markdown(
                    f"<div style='font-family:monospace;font-size:0.85em;"
                    f"padding:4px 8px;border-left:3px solid {color};"
                    f"margin:2px 0'>"
                    f"{ts_corto}  → {estado_ev}{tag}"
                    f"<span style='color:#888;margin-left:12px'>"
                    f"({acc:.1f} m/s²)</span></div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown("*Sin eventos registrados*")

    time.sleep(1)
    st.rerun()


render()
