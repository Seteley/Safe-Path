"""Tests para el parser de payloads HTTP.

Cubre: RF-S01, S02, S15, RNF-S03.
"""

import pytest

from safepath_mvp.simulador.parser import (
    extraer_aceleracion,
    extraer_gps,
    calcular_aceleracion_neta,
)


class TestExtraerAceleracion:
    """RF-S01: Recibir y parsear datos de acelerometro."""

    def test_extrae_ax_ay_az_directos(self):
        data = {"ax": 1.0, "ay": 2.0, "az": 3.0}
        result = extraer_aceleracion(data)
        assert result == (1.0, 2.0, 3.0)

    def test_extrae_x_y_z(self):
        data = {"x": 0.5, "y": 1.5, "z": 9.8}
        result = extraer_aceleracion(data)
        assert result == (0.5, 1.5, 9.8)

    def test_extrae_desde_lista(self):
        data = [{"other": 1}, {"ax": 1.0, "ay": 2.0, "az": 3.0}]
        result = extraer_aceleracion(data)
        assert result == (1.0, 2.0, 3.0)

    def test_extrae_desde_payload_anidado(self):
        data = {"payload": {"ax": 0.1, "ay": 0.2, "az": 9.9}}
        result = extraer_aceleracion(data)
        assert result == (0.1, 0.2, 9.9)

    def test_formato_sensor_logger_android(self):
        data = [
            {
                "accelerometerAccelerationX": 0.1,
                "accelerometerAccelerationY": 0.2,
                "accelerometerAccelerationZ": 9.8,
            }
        ]
        result = extraer_aceleracion(data)
        assert result == (0.1, 0.2, 9.8)

    def test_formato_accel_con_mayusculas(self):
        data = {"ACCX": 1.0, "ACCY": 2.0, "ACCZ": 3.0}
        result = extraer_aceleracion(data)
        assert result == (1.0, 2.0, 3.0)


class TestToleranciaFallos:
    """RF-S15, RNF-S03: Tolerar payloads malformados sin crashear."""

    def test_retorna_none_si_no_hay_datos(self):
        assert extraer_aceleracion({}) is None

    def test_retorna_none_con_none(self):
        assert extraer_aceleracion(None) is None

    def test_retorna_none_con_datos_irrelevantes(self):
        assert extraer_aceleracion({"foo": "bar"}) is None

    def test_no_crashea_con_valores_no_numericos(self):
        result = extraer_aceleracion({"ax": "no_es_numero", "ay": 2, "az": 3})
        assert result is None

    def test_no_crashea_con_lista_plana(self):
        result = extraer_aceleracion([1, 2, 3])
        assert result is None


class TestExtraerGPS:
    def test_extrae_lat_lon_directos(self):
        data = {"latitude": -12.08, "longitude": -77.05}
        result = extraer_gps(data)
        assert result == (-12.08, -77.05)

    def test_extrae_lat_lon_cortos(self):
        data = {"lat": -12.08, "lon": -77.05}
        result = extraer_gps(data)
        assert result == (-12.08, -77.05)

    def test_rechaza_coordenadas_fuera_de_rango(self):
        assert extraer_gps({"lat": 999, "lon": 999}) is None

    def test_rechaza_lat_0_lon_0(self):
        assert extraer_gps({"lat": 0, "lon": 0}) is None

    def test_retorna_none_sin_gps(self):
        assert extraer_gps({"ax": 1, "ay": 2, "az": 3}) is None


class TestCalcularAceleracionNeta:
    """RF-S02: magnitud neta = |sqrt(ax^2+ay^2+az^2) - 9.8|."""

    def test_reposo_da_net_cercana_a_cero(self):
        net = calcular_aceleracion_neta(0, 0, 9.8)
        assert net == pytest.approx(0.0, abs=0.01)

    def test_aceleracion_horizontal(self):
        net = calcular_aceleracion_neta(10, 0, 9.8)
        expected = abs((100 + 0 + 96.04) ** 0.5 - 9.8)
        assert net == pytest.approx(expected, abs=0.01)

    def test_caida_libre(self):
        net = calcular_aceleracion_neta(0, 0, 0)
        assert net == pytest.approx(9.8, abs=0.01)

    def test_con_gravedad_personalizada(self):
        net = calcular_aceleracion_neta(0, 0, 3.7, gravedad=3.7)
        assert net == pytest.approx(0.0, abs=0.01)
