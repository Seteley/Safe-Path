import os
from dotenv import load_dotenv
load_dotenv()

UMBRAL_ACELERACION = 15.0   # m/s²
TIEMPO_VERIFICACION = 10    # segundos
DURACION_ALERTA = 30        # segundos
HOST = "0.0.0.0"
PORT = 5000
USUARIA = "Ana Flores"
CONTACTO = "María Flores (mamá)"
UBICACION_LAT = -12.0833    # Jesús María, Lima
UBICACION_LON = -77.0500
DIRECCION = "Av. La Marina 1200, Jesús María"
UMBRAL_MOVIMIENTO_GPS = 0.00004  # grados (~4m) para ignorar ruido del sensor

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_EMAIL = os.getenv("SAFEPATH_SMTP_EMAIL", "")
CONTACTO_EMAIL = os.getenv("SAFEPATH_CONTACTO_EMAIL", "")
SMTP_PASSWORD = os.getenv("SAFEPATH_SMTP_PASSWORD", "")
