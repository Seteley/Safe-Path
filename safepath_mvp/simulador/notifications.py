"""Notificaciones SMS via Twilio para alertas SAFE-PATH.

Requiere configurar las variables de entorno en .env (ver .env.example).
La funcion se llama desde logic.py en un hilo daemon para no bloquear
la maquina de estados.
"""

from typing import Any
from .settings import settings
from ..shared.utils import setup_logging

logger = setup_logging("safepath.notifications")


def _determinar_tipo_activacion(estado: dict[str, Any]) -> str:
    """Determina si la alerta fue activada automatica o manualmente."""
    historial = estado.get("historial", [])
    if historial:
        ultimo = historial[-1]
        if ultimo.get("forzado"):
            return "Manual (operador)"
        if ultimo.get("escalado"):
            return "Automatica (temporizador)"
    return "Automatica (temporizador)"


def enviar_alerta_sms(estado: dict[str, Any]) -> bool:
    """Envia SMS de alerta al contacto de confianza via Twilio.

    El mensaje incluye: nombre de usuaria, ubicacion GPS, enlace de mapa,
    hora del evento y tipo de activacion (automatica o manual).

    Returns:
        True si el SMS fue enviado exitosamente, False en caso contrario.
    """
    if not settings.sms_configured:
        logger.info("Credenciales Twilio no configuradas - omitiendo SMS")
        return False

    if estado.get("estado") != "ALERTA":
        return False

    lat = estado.get("lat", "")
    lon = estado.get("lon", "")
    enlace_mapa = (
        f"https://maps.google.com/?q={lat},{lon}"
        if lat and lon
        else "ubicacion no disponible"
    )
    tipo_activacion = _determinar_tipo_activacion(estado)
    hora = estado.get("timestamp_cambio", "")[:19].replace("T", " ")

    cuerpo = (
        f"[SAFE-PATH] ALERTA DE EMERGENCIA\n"
        f"Usuaria: {estado.get('usuaria', 'Desconocida')}\n"
        f"Hora: {hora}\n"
        f"Ubicacion: {enlace_mapa}\n"
        f"Activacion: {tipo_activacion}"
    )

    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=cuerpo,
            from_=settings.TWILIO_FROM_NUMBER,
            to=settings.TWILIO_TO_NUMBER,
        )
        logger.info("SMS enviado a %s (SID: %s)", settings.TWILIO_TO_NUMBER, message.sid)
        return True
    except ImportError:
        logger.error("Libreria 'twilio' no instalada. Ejecutar: pip install twilio>=8.0")
    except Exception as e:
        logger.error("Error al enviar SMS: %s", e)
    return False
