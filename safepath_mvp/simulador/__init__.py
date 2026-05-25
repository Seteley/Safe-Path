"""SAFE-PATH MVP - Simulador de pulsera (Dimensión 1).

Recibe datos del acelerometro via HTTP, procesa con maquina de estados,
y expone el estado para el dashboard.
"""

from safepath_mvp.simulador.logic import StateMachine
from safepath_mvp.simulador.server import app
