import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import SMTP_EMAIL, SMTP_PASSWORD, SMTP_SERVER, SMTP_PORT, CONTACTO_EMAIL


def enviar_alerta_email(estado):
    """Envia notificacion de alerta al contacto via email SMTP."""
    if not all([SMTP_EMAIL, SMTP_PASSWORD, CONTACTO_EMAIL]):
        print("[EMAIL] Configuracion incompleta — omitiendo notificacion")
        return False

    if estado.get("estado") != "ALERTA":
        return False

    asunto = f"[ALERTA SAFE-PATH] {estado.get('usuaria', 'Usuaria')} necesita ayuda"
    cuerpo = f"""ALERTA DE EMERGENCIA — SAFE-PATH
=====================================

{estado.get('usuaria', 'Usuaria')} activo una alerta de seguridad.

El sistema detecto una aceleracion anomala de {estado.get('aceleracion_actual', 0)} m/s2
y la usuaria no cancelo la verificacion a tiempo.

Ubicacion GPS: {estado.get('lat', '?')}, {estado.get('lon', '?')}
Direccion de referencia: {estado.get('direccion', 'No disponible')}
Hora del evento: {estado.get('timestamp_cambio', '?')[:19]}

---
Enviado automaticamente por SAFE-PATH
Contacto de emergencia: {estado.get('contacto', 'N/A')}
"""

    msg = MIMEMultipart()
    msg["From"] = SMTP_EMAIL
    msg["To"] = CONTACTO_EMAIL
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"[EMAIL] Notificacion enviada a {CONTACTO_EMAIL}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("[EMAIL] Error: credenciales invalidas. Verificar SAFEPATH_SMTP_PASSWORD en .env")
    except Exception as e:
        print(f"[EMAIL] Error al enviar: {e}")
    return False
