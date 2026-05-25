"""SAFE-PATH MVP - Utilidades y contratos compartidos.

Define el schema de state.json y funciones de utilidad
usadas tanto por el simulador como por el dashboard.
"""

from safepath_mvp.shared.schema import (
    ESTADO_INICIAL,
    ESTADOS_VALIDOS,
    CAMPOS_HISTORIAL,
    FLAGS_HISTORIAL,
    COLOR_NORMAL,
    COLOR_VERIFICANDO,
    COLOR_ALERTA,
    COLOR_RESUELTO,
)

from safepath_mvp.shared.utils import (
    get_local_ip,
    setup_logging,
    atomic_write_json,
)
