"""Carga de configuracion sensible desde variables de entorno (.env).

Separado de config.py para evitar exponer secrets en imports accidentales.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Configuracion sensible cargada exclusivamente desde .env."""

    SMTP_EMAIL: str = os.getenv("SAFEPATH_SMTP_EMAIL", "")
    SMTP_PASSWORD: str = os.getenv("SAFEPATH_SMTP_PASSWORD", "")
    CONTACTO_EMAIL: str = os.getenv("SAFEPATH_CONTACTO_EMAIL", "")

    @property
    def email_configured(self) -> bool:
        return all([self.SMTP_EMAIL, self.SMTP_PASSWORD, self.CONTACTO_EMAIL])


settings = Settings()
