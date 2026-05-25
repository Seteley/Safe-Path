# Constantes de calibracion y negocio (no secrets)
UMBRAL_ACELERACION: float = 15.0   # m/s2
TIEMPO_VERIFICACION: int = 10      # segundos
DURACION_ALERTA: int = 30          # segundos
DURACION_RESUELTO: int = 5         # segundos
GRAVEDAD: float = 9.8              # m/s2
HOST: str = "0.0.0.0"
PORT: int = 5000
USUARIA: str = "Ana Flores"
CONTACTO: str = "Maria Flores (mama)"
UBICACION_LAT: float = -12.0833    # Jesus Maria, Lima
UBICACION_LON: float = -77.0500
DIRECCION: str = "Av. La Marina 1200, Jesus Maria"
UMBRAL_MOVIMIENTO_GPS: float = 0.00004  # grados (~4m) para ignorar ruido del sensor

SMTP_SERVER: str = "smtp.gmail.com"
SMTP_PORT: int = 465
