import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any
from .config import SMTP_SERVER, SMTP_PORT
from .settings import settings
from ..shared.utils import setup_logging

logger = setup_logging("safepath.notifications")


def _determinar_tipo_activacion(estado: dict[str, Any]) -> str:
    """Determina si la alerta fue activada automatica o manualmente."""
    historial = estado.get("historial", [])
    if historial:
        ultimo = historial[-1]
        if ultimo.get("forzado"):
            return "Manual (forzado por operador desde el dashboard)"
        if ultimo.get("escalado"):
            return "Automatica (temporizador de verificacion expirado)"
    return "Automatica (temporizador de verificacion expirado)"


def enviar_alerta_email(estado: dict[str, Any]) -> bool:
    """Envia notificacion de alerta al contacto via email SMTP."""
    if not settings.email_configured:
        logger.info("Configuracion incompleta - omitiendo notificacion")
        return False

    if estado.get("estado") != "ALERTA":
        return False

    lat = estado.get("lat", "?")
    lon = estado.get("lon", "?")
    enlace_mapa = (
        f"https://maps.google.com/?q={lat},{lon}"
        if lat != "?" and lon != "?"
        else "Coordenadas no disponibles"
    )
    tipo_activacion = _determinar_tipo_activacion(estado)

    asunto = f"[ALERTA SAFE-PATH] {estado.get('usuaria', 'Usuaria')} necesita ayuda"
    cuerpo = f"""ALERTA DE EMERGENCIA - SAFE-PATH
=====================================

{estado.get('usuaria', 'Usuaria')} activo una alerta de seguridad.

El sistema detecto una aceleracion anomala de {estado.get('aceleracion_actual', 0)} m/s2
y la usuaria no cancelo la verificacion a tiempo.

Ubicacion GPS: {lat}, {lon}
Ver en mapa:   {enlace_mapa}
Direccion de referencia: {estado.get('direccion', 'No disponible')}
Hora del evento: {estado.get('timestamp_cambio', '?')[:19]}
Tipo de activacion: {tipo_activacion}

---
Enviado automaticamente por SAFE-PATH
Contacto de emergencia: {estado.get('contacto', 'N/A')}
"""

    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_EMAIL
    msg["To"] = settings.CONTACTO_EMAIL
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("Notificacion enviada a %s", settings.CONTACTO_EMAIL)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("Credenciales invalidas. Verificar SAFEPATH_SMTP_PASSWORD en .env")
    except Exception as e:
        logger.error("Error al enviar email: %s", e)
    return False
