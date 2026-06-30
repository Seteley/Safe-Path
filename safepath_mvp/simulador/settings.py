"""Carga de configuracion sensible desde variables de entorno (.env).

Separado de config.py para evitar exponer secrets en imports accidentales.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Configuracion sensible cargada exclusivamente desde .env."""

    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER: str = os.getenv("TWILIO_FROM_NUMBER", "")
    TWILIO_TO_NUMBER: str = os.getenv("TWILIO_TO_NUMBER", "")

    # IP del celular con Phyphox activo (cambia segun la red de cada persona)
    PHYPHOX_IP: str = os.getenv("PHYPHOX_IP", "192.168.1.100")

    @property
    def sms_configured(self) -> bool:
        return all(
            [
                self.TWILIO_ACCOUNT_SID,
                self.TWILIO_AUTH_TOKEN,
                self.TWILIO_FROM_NUMBER,
                self.TWILIO_TO_NUMBER,
            ]
        )


settings = Settings()
