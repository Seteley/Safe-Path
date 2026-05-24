import streamlit as st
import json, time, folium, requests
from streamlit_folium import st_folium
from config import *

st.set_page_config(
    page_title="SAFE-PATH — Panel de seguridad",
    page_icon="🟣",
    layout="wide"
)


def load_state():
    try:
        with open("state.json") as f:
            return json.load(f)
    except:
        return {
            "state": "NORMAL", "accel": 0,
            "countdown": 0, "historial": [],
            "umbral": UMBRAL_ACELERACION,
            "lat": UBICACION_LAT, "lon": UBICACION_LON,
            "gps_activo": False,
        }


COLORES = {
    "NORMAL":      "#1D9E75",
    "VERIFICANDO": "#DEB700",
    "ALERTA":      "#D85A30",
    "RESUELTO":    "#1A6B8A",
}

EMOJIS = {
    "NORMAL":      "🟢",
    "VERIFICANDO": "🟡",
    "ALERTA":      "🔴",
    "RESUELTO":    "🔵",
}


def render():
    data = load_state()
    state = data["state"]
    color = COLORES.get(state, "#888")
    emoji = EMOJIS.get(state, "⚪")

    st.markdown(
        f"<h1 style='color:{color}'>🟣 SAFE-PATH "
        f"<span style='font-size:0.6em'>Panel de seguridad preventiva</span></h1>",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([1, 1.4])

    with col1:
        gps_lat = data.get("lat", UBICACION_LAT)
        gps_lon = data.get("lon", UBICACION_LON)
        gps_activo = data.get("gps_activo", False)
        gps_texto = f"📍 GPS: {gps_lat:.6f}, {gps_lon:.6f}" if gps_activo else "📍 GPS: usando ubicación de referencia"

        st.markdown(
            f"<div style='background:{color};padding:20px;border-radius:12px;"
            f"text-align:center'>"
            f"<h2 style='color:white;margin:0'>{emoji} {state}</h2>"
            f"<p style='color:white;margin:4px 0'>{USUARIA}</p>"
            f"<p style='color:rgba(255,255,255,0.8);font-size:0.85em'>"
            f"{gps_texto}</p></div>",
            unsafe_allow_html=True
        )

        st.markdown("---")

        st.markdown("**Aceleración detectada**")
        accel = data["accel"]
        umbral = data["umbral"]
        pct = min(accel / (umbral * 1.5), 1.0)
        st.metric("Aceleración actual", f"{accel:.1f} m/s²",
                  delta=f"Umbral: {umbral} m/s²")
        st.progress(pct)

        st.markdown("---")

        st.markdown("**Flujo interno de la pulsera**")
        nodos = ["DETECTAR", "VERIFICAR", "ESCALAR"]
        activos = {
            "NORMAL":      [False, False, False],
            "VERIFICANDO": [True,  True,  False],
            "ALERTA":      [True,  True,  True],
            "RESUELTO":    [True,  True,  True],
        }.get(state, [False, False, False])

        cols = st.columns(3)
        for i, (nodo, activo) in enumerate(zip(nodos, activos)):
            bg = color if activo else "#E0E0E0"
            txt = "white" if activo else "#888"
            cols[i].markdown(
                f"<div style='background:{bg};padding:8px;border-radius:8px;"
                f"text-align:center'><b style='color:{txt}'>{nodo}</b></div>",
                unsafe_allow_html=True
            )

        if state == "VERIFICANDO":
            st.markdown("---")
            countdown = data["countdown"]
            st.markdown(
                f"<div style='background:#FEF3CD;padding:16px;border-radius:12px;"
                f"text-align:center;border:2px solid #DEB700'>"
                f"<h2 style='color:#854F0B;margin:0'>⚠️ Verificando...</h2>"
                f"<h1 style='color:#D85A30;margin:8px 0'>{countdown}s</h1>"
                f"<p style='color:#666'>Si no cancela, se escalará la alerta</p>"
                f"</div>",
                unsafe_allow_html=True
            )
            if st.button("✅ CANCELAR ALERTA", type="secondary"):
                try:
                    requests.post("http://localhost:5000/cancel")
                except:
                    pass

    with col2:
        gps_lat = data.get("lat", UBICACION_LAT)
        gps_lon = data.get("lon", UBICACION_LON)

        m = folium.Map(
            location=[gps_lat, gps_lon],
            zoom_start=15 if gps_activo else 15,
            tiles="CartoDB positron"
        )
        icon_color = {
            "NORMAL": "green",
            "VERIFICANDO": "orange",
            "ALERTA": "red",
            "RESUELTO": "blue",
        }.get(state, "gray")

        popup_text = f"{USUARIA} — {state}"
        if gps_activo:
            popup_text += f"\n{gps_lat:.5f}, {gps_lon:.5f}"

        folium.Marker(
            [gps_lat, gps_lon],
            popup=popup_text,
            tooltip=f"📍 {'GPS activo' if gps_activo else DIRECCION}",
            icon=folium.Icon(color=icon_color, icon="user", prefix="fa")
        ).add_to(m)

        st_folium(m, height=320, use_container_width=True)

        st.markdown("**Historial de eventos**")
        historial = data.get("historial", [])
        if historial:
            for evento in reversed(historial):
                st.markdown(
                    f"<div style='font-family:monospace;font-size:0.85em;"
                    f"padding:4px 8px;border-left:3px solid {color};"
                    f"margin:2px 0'>{evento}</div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown("*Sin eventos registrados*")

    time.sleep(1)
    st.rerun()


render()
