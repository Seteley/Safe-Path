# SAFE-PATH -- MVP Demo

Sistema de seguridad preventiva para mujeres. Una pulsera inteligente (simulada con el celular) detecta sacudidas bruscas mediante el acelerometro, inicia un proceso de verificacion con cuenta regresiva, y escala la alerta automaticamente si la usuaria no cancela. Todo en tiempo real.

---

## Arquitectura

```
[ CELULAR (Sensor Logger) ]     HTTP POST cada 100ms     [ server.py (Flask)     ]
[ acelerometro + GPS       ] --------------------------> [ puerto 5000           ]
                                                          [ + logic.py            ]
                                                                  |
                                                          escritura atomica
                                                          (os.replace)
                                                                  v
[ dashboard.py (Streamlit)  ] <---- lee state.json ---- [ state.json            ]
[ panel visual en tiempo    ]      cada 1 segundo
[ real con mapa + estado    ]
```

- **Una sola laptop** ejecuta el servidor Flask y el dashboard Streamlit en paralelo
- **El celular** con Sensor Logger transmite acelerometro y GPS por WiFi a la laptop
- **`state.json`** es el archivo compartido que sincroniza ambos procesos -- se escribe atomicamente con `os.replace`
- **`schema.py`** define el contrato del JSON para que simulador y dashboard trabajen sin romperse
- Todo en **Python puro**, sin MQTT, sin broker externo, sin servidores en la nube

---

## Estructura del proyecto

```
prueba safepath/
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml
├── CONTRIBUTING.md
├── README.md
├── requirements.txt
├── venv/
├── tests/
│   ├── conftest.py
│   ├── test_logic.py
│   ├── test_parser.py
│   ├── test_server.py
│   ├── test_schema.py
│   └── test_components.py
│
└── safepath_mvp/
    ├── __init__.py
    │
    ├── simulador/
    │   ├── __init__.py
    │   ├── config.py          Constantes de negocio (umbrales, tiempos, textos)
    │   ├── settings.py        Carga de secrets desde .env
    │   ├── server.py          Servidor Flask con endpoints REST
    │   ├── parser.py          Extraccion de acelerometro/GPS desde payloads HTTP
    │   ├── logic.py           Maquina de estados con timers thread-safe
    │   └── notifications.py   Envio de email SMTP al contacto de confianza
    │
    ├── dashboard/
    │   ├── __init__.py
    │   ├── dashboard.py       Orquestador del panel Streamlit
    │   └── components.py      Componentes visuales (estado, mapa, historial, etc.)
    │
    ├── shared/
    │   ├── __init__.py
    │   ├── schema.py          Contrato de state.json compartido
    │   └── utils.py           Logging, IP local, escritura atomica
    │
    ├── state.json             Estado compartido (se regenera solo)
    ├── .env / .env.example
    └── assets/
        └── pulsera.png
```

### Descripcion de modulos

| Archivo | Proposito |
|---------|-----------|
| `config.py` | Contiene todas las constantes del sistema: umbral de aceleracion (15 m/s2), umbral de movimiento GPS (~4m), duracion de la verificacion (10s), duracion de la alerta (30s), host, puerto, datos de la usuaria de prueba y ubicacion de referencia. Cambiar cualquier valor aqui afecta a todo el sistema. |
| `settings.py` | Carga secrets desde `.env` (credenciales SMTP). Separado de `config.py` para no exponer secrets en imports. |
| `logic.py` | Maquina de estados con 4 estados: `NORMAL`, `VERIFICANDO`, `ALERTA`, `RESUELTO`. Thread-safe con `threading.Lock`. Maneja temporizadores trackeados para countdown y auto-escalamiento. Guarda el estado en `state.json` con escritura atomica. Historial de ultimos 10 eventos con timestamps ISO 8601. |
| `server.py` | Servidor HTTP Flask con 8 endpoints. Usa `parser.py` para extraer aceleracion y GPS de multiples formatos JSON. Logging estructurado para diagnostico en vivo. |
| `parser.py` | Funciones de parsing flexibles que extraen aceleracion (`ax,ay,az`) y coordenadas GPS (`lat,lon`) de multiples formatos JSON -- compatible con Sensor Logger, Phyphox y sensores nativos. |
| `notifications.py` | Envia email SMTP al contacto de confianza cuando el estado transiciona a ALERTA. Usa `settings.py` para credenciales. |
| `dashboard.py` | Orquestador Streamlit que lee `state.json` cada 1s y renderiza todos los componentes. Layout de 2 columnas estable en pantalla 15". |
| `components.py` | Componentes visuales individuales: indicador de estado con color SafeCorp, barra de aceleracion, flujo DETECTAR->VERIFICAR->ESCALAR, countdown, mapa Folium, historial de eventos. El mapa se reconstruye solo al cambiar de estado o detectar >4m de movimiento real. |
| `schema.py` | Define el contrato explicito del `state.json`: nombres de campos, tipos, valores por defecto, estados validos, paleta de colores. Ambos modulos importan desde aqui. |
| `utils.py` | Utilidades compartidas: configuracion de logging, deteccion de IP local, escritura atomica de JSON con archivo temporal + `os.replace`. |

---

## Maquina de estados

```
NORMAL --(aceleracion > 15 m/s2)--> VERIFICANDO --(10s sin cancelar)--> ALERTA
  ^                                      |                                  |
  |                              (usuario cancela)                   (30s o manual)
  |                                      |                                  |
  +--------------------------------------+                                  v
  ^                                                                   RESUELTO
  +-------------------------------------(5s)-----------------------------+
```

Los estados tambien pueden forzarse manualmente con `/trigger?estado=X` y reiniciarse con `/reset`.

| Transicion | Disparador | Endpoint |
|---|---|---|
| `NORMAL -> VERIFICANDO` | Aceleracion neta supera 15 m/s2 (sacudida del celular) | `POST /data` |
| `VERIFICANDO -> NORMAL` | Usuario presiona "CANCELAR ALERTA" antes de que termine el countdown | `GET /cancel` |
| `VERIFICANDO -> ALERTA` | El countdown de 10 segundos llega a 0 sin cancelacion | Automatico (threading.Timer) |
| `ALERTA -> RESUELTO` | 30 segundos transcurridos | Automatico (threading.Timer) |
| `RESUELTO -> NORMAL` | 5 segundos transcurridos | Automatico (threading.Timer) |
| `CUALQUIERA -> X` | Forzado manualmente (debug / Plan B) | `GET /trigger?estado=X` |
| `CUALQUIERA -> NORMAL` | Reinicio limpio para nueva demo | `GET /reset` |

---

## APIs del servidor Flask

| Metodo | Endpoint | Descripcion | Respuesta |
|---|---|---|---|
| `POST` | `/data` | Recibe datos del acelerometro y GPS desde Sensor Logger | `{"status": "ok", "accel": 0.23}` |
| `GET` | `/status` | Retorna el estado actual completo (contenido de state.json) | `{"estado": "NORMAL", ...}` |
| `GET` / `POST` | `/cancel` | Cancela una verificacion activa: `VERIFICANDO -> NORMAL` | `{"status": "cancelado"}` |
| `GET` | `/trigger?estado=X` | Fuerza cualquier estado (`NORMAL`, `VERIFICANDO`, `ALERTA`, `RESUELTO`). Usar para debug sin celular. | `{"status": "ok", "estado": "ALERTA"}` |
| `GET` | `/reset` | Reinicia el sistema a NORMAL para empezar una nueva demo. Cancela todos los timers activos y limpia el historial. | `{"status": "reseteado", "estado": "NORMAL"}` |
| `GET` | `/ping` | Health check simple -- verifica que el servidor esta vivo | `{"status": "alive", "state": "NORMAL"}` |
| `POST` | `/sensor` | **Alias** de `/data` -- compatibilidad con versiones anteriores | Igual que `/data` |
| `GET` | `/state` | **Alias** de `/status` -- compatibilidad con versiones anteriores | Igual que `/status` |

---

## Modelo de datos -- state.json

```json
{
  "estado": "NORMAL",
  "aceleracion_actual": 0.0,
  "countdown_restante": 0,
  "timestamp_cambio": "2026-05-24T23:31:00.237105+00:00",
  "timestamp_inicio_verificando": null,
  "historial": [
    {
      "estado": "NORMAL",
      "timestamp": "2026-05-24T23:31:00.237105+00:00",
      "aceleracion": 2.3,
      "cancelado": true,
      "escalado": false,
      "forzado": false
    }
  ],
  "usuaria": "Ana Flores",
  "contacto": "Maria Flores (mama)",
  "lat": -12.0833,
  "lon": -77.0500,
  "direccion": "Av. La Marina 1200, Jesus Maria",
  "umbral": 15.0
}
```

| Campo | Tipo | Descripcion |
|---|---|---|
| `estado` | `string` | Uno de: `NORMAL`, `VERIFICANDO`, `ALERTA`, `RESUELTO` |
| `aceleracion_actual` | `float` | Ultima aceleracion neta recibida (m/s2) |
| `countdown_restante` | `int` | Segundos restantes del countdown (0 fuera de VERIFICANDO) |
| `timestamp_cambio` | `string` | ISO 8601 UTC del ultimo cambio de estado |
| `timestamp_inicio_verificando` | `string` / `null` | ISO 8601 UTC de cuando entro a VERIFICANDO. `null` si no esta en ese estado |
| `historial` | `array` | Ultimos 10 eventos. Cada entrada tiene: `estado`, `timestamp`, `aceleracion`, y flags opcionales `cancelado`, `escalado`, `forzado` |
| `usuaria` | `string` | Nombre de la usuaria (desde config.py) |
| `contacto` | `string` | Nombre del contacto de emergencia (desde config.py) |
| `lat` | `float` | Latitud actual (GPS real del celular, o coordenada de referencia) |
| `lon` | `float` | Longitud actual |
| `direccion` | `string` | Direccion de referencia |
| `umbral` | `float` | Umbral de aceleracion configurado (m/s2) |

---

## Optimizacion del mapa (sin parpadeo)

El dashboard implementa 3 mecanismos para que el mapa Folium no parpadee:

1. **Pre-renderizado HTML** -- El mapa Folium se convierte a string HTML una sola vez y se guarda en `st.session_state`. Se usa `st.components.v1.html()` en lugar de `st_folium()`. Al ser un string identico entre ciclos, el navegador no recarga el iframe.

2. **Umbral de movimiento GPS** -- `UMBRAL_MOVIMIENTO_GPS = 0.00004` (~4 metros). El ruido del GPS (fluctuaciones de 0.000006 grados) se ignora. Solo se reconstruye el mapa cuando la persona realmente camina >4m.

3. **Reconstruccion por cambio de estado** -- El mapa siempre se reconstruye cuando cambia el estado, para reflejar el nuevo color del marcador. Esto ocurre solo 3-4 veces durante toda la demo.

**Resultado:** mapa estable sin parpadeo, se actualiza automaticamente al caminar o al cambiar de estado.

---

## Requisitos

- **Python 3.9+**
- **Celular** con iOS o Android y la app gratuita **Sensor Logger**
- **Misma red WiFi** entre la laptop y el celular (o hotspot del celular hacia la laptop)

### Dependencias Python

```
flask>=2.0           Servidor HTTP local
streamlit>=1.30      Dashboard interactivo
folium>=0.14         Mapa interactivo (renderizado de HTML)
requests>=2.25       Cliente HTTP (para el boton cancelar del dashboard)
python-dotenv>=1.0   Carga variables de entorno desde archivo .env
```

**Dependencias de desarrollo:**

```
pytest>=8.0          Framework de testing
pytest-cov>=5.0      Cobertura de tests
ruff>=0.8            Linter y formateador
pre-commit>=3.0      Hooks de pre-commit
```

---

## Instalacion

```bash
# 1. Clonar o copiar la carpeta del proyecto en la laptop
cd "prueba safepath"

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno virtual
# Windows:
venv\Scripts\Activate.ps1
# Mac/Linux:
source venv/bin/activate

# 4. Instalar dependencias (produccion + desarrollo)
pip install -e ".[dev]"

# 5. Instalar hooks de pre-commit
pre-commit install
```

---

## Configuracion del celular (Sensor Logger)

1. Instalar **Sensor Logger** desde Play Store (Android) o App Store (iOS) -- es gratuita
2. Conectar el celular a la **misma red WiFi** que la laptop
3. En Sensor Logger, ir a **Settings -> Streaming**:
   - Activar **HTTP Push**
   - **URL:** `http://<IP_DE_LA_LAPTOP>:5000/data` (ej: `http://192.168.1.44:5000/data`)
   - **Intervalo:** 100 ms
   - Activar los sensores: **acelerometro** y **ubicacion/GPS**
4. Para encontrar la IP de la laptop:
   - Windows: abrir `cmd`, ejecutar `ipconfig`, buscar `Direccion IPv4`
   - Mac/Linux: `ifconfig` o `ip a`
5. Opcional: desactivar el resto de sensores para no saturar la red local

El servidor Flask imprime la IP detectada y todos los endpoints al iniciar:
```
=======================================================
  SAFE-PATH SERVER (D1 - Simulador de Pulsera)
  IP detectada: 192.168.1.44
  POST /data       <- Sensor Logger (acelerometro)
  GET  /status     <- Estado completo
  GET  /cancel     <- Cancelar verificacion
  GET  /trigger?estado=X  <- Forzar estado (Plan B)
  GET  /reset      <- Reiniciar para nueva demo
  GET  /ping       <- Health check
=======================================================
```

---

## Como ejecutar

Abrir **dos terminales** en la laptop. En ambas, activar el entorno virtual desde la raiz del proyecto:

**Terminal 1 -- Servidor Flask (recibe datos del celular):**
```bash
python -m safepath_mvp.simulador.server
```

**Terminal 2 -- Dashboard Streamlit (panel visual):**
```bash
streamlit run safepath_mvp/dashboard/dashboard.py
```
Se abre automaticamente en el navegador en `http://localhost:8501`

**En el celular:** iniciar el streaming en Sensor Logger (boton Play).

**Verificar conexion:** abrir en el navegador del celular `http://<IP>:5000/ping` -- debe responder `{"status":"alive"...}`.

---

## Como probar la demo

### Variante A -- Cancelacion (manejo de falsos positivos)

1. Dashboard muestra estado **NORMAL** (fondo verde)
2. Sacudir el celular bruscamente
3. El sistema detecta la aceleracion anomala y entra en **VERIFICANDO**
4. Aparece cuenta regresiva de 10 segundos con boton "CANCELAR ALERTA"
5. **Presionar CANCELAR** -- la usuaria confirma que fue una falsa alarma
6. El sistema vuelve a **NORMAL** -- se registro como cancelacion manual en el historial

### Variante B -- Escalamiento (alerta real)

1. Sacudir el celular bruscamente de nuevo
2. Entra en **VERIFICANDO** con countdown
3. **No cancelar** -- dejar que el countdown llegue a 0
4. El sistema escala automaticamente a **ALERTA**
5. El dashboard cambia a fondo rojo, muestra "Contacto notificado: Maria Flores (mama)", registra el timestamp
6. A los 30 segundos se resuelve automaticamente -> **RESUELTO** -> vuelve a NORMAL

### Sin celular (debug con endpoints)

```bash
# Simular sacudida (inyecta aceleracion de 20 m/s2)
curl http://localhost:5000/trigger?estado=VERIFICANDO

# Cancelar verificacion
curl http://localhost:5000/cancel

# Forzar alerta directamente
curl http://localhost:5000/trigger?estado=ALERTA

# Reiniciar para siguiente demo
curl http://localhost:5000/reset
```

---

## Plan B -- si algo falla

| Problema | Solucion |
|---|---|
| Sensor Logger no conecta | Verificar que laptop y celular esten en la misma WiFi. Probar `http://<IP>:5000/ping` desde el navegador del celular |
| El dashboard no reacciona | Usar `/trigger?estado=VERIFICANDO` para disparar estados manualmente sin celular |
| Necesito reiniciar entre demos | Usar `/reset` para limpiar estado y empezar desde NORMAL |
| Dashboard va lento | Cambiar `time.sleep(1)` a `time.sleep(2)` en `dashboard.py` |
| Mapa parpadea | Bajar `UMBRAL_MOVIMIENTO_GPS` en `config.py` (ej: `0.00002` = ~2m) |
| Puerto 5000 ocupado | `netstat -ano | findstr :5000` para ver quien lo usa, cambiar `PORT` en `config.py` |
| Firewall bloquea | Ejecutar como administrador: `netsh advfirewall firewall add rule name="Flask 5000" dir=in action=allow protocol=TCP localport=5000` |
| state.json corrupto | Borrar el archivo; se regenera automaticamente al siguiente arranque del servidor |
| Todo falla | Tener un video grabado previamente del caso de uso funcionando |

---

## Parametros configurables

Todos en `simulador/config.py`:

```python
UMBRAL_ACELERACION = 15.0    # m/s2 -- aceleracion neta que dispara la deteccion
TIEMPO_VERIFICACION = 10     # segundos de countdown antes de escalar
DURACION_ALERTA = 30         # segundos que dura el estado de alerta
DURACION_RESUELTO = 5        # segundos que dura el estado resuelto
GRAVEDAD = 9.8               # m/s2
HOST = "0.0.0.0"             # escucha en todas las interfaces de red
PORT = 5000                  # puerto del servidor Flask
USUARIA = "Ana Flores"       # nombre mostrado en el dashboard
CONTACTO = "Maria Flores (mama)"  # contacto de emergencia
UBICACION_LAT = -12.0833     # latitud de referencia (Jesus Maria, Lima)
UBICACION_LON = -77.0500     # longitud de referencia
DIRECCION = "Av. La Marina 1200, Jesus Maria"  # direccion de referencia
UMBRAL_MOVIMIENTO_GPS = 0.00004  # grados (~4m) para ignorar ruido del sensor GPS
```

- **`UMBRAL_ACELERACION` (15 m/s2):** Caminar normal (2-4 m/s2) no activa. Una sacudida intencional (20-30 m/s2) si.
- **`UMBRAL_MOVIMIENTO_GPS` (0.00004 grados ~4m):** Ignora el ruido del GPS del celular. Solo reconstruye el mapa cuando la persona realmente se movio.

---

## Notificaciones por Email

Cuando el sistema escala a ALERTA, envia automaticamente un email al contacto de confianza con la ubicacion GPS, aceleracion detectada y hora del evento.

### Setup (2 minutos)

1. Crear una cuenta Gmail para el proyecto (ej: `safepath.demo@gmail.com`)
2. Activar verificacion en 2 pasos en https://myaccount.google.com/security
3. Generar App Password en https://myaccount.google.com/apppasswords
   - Nombre: "SafePath"
   - Copiar el codigo de 16 caracteres (sin espacios)
4. Copiar `.env.example` a `.env` y completar:
   ```
   SAFEPATH_SMTP_EMAIL=safepath.demo@gmail.com
   SAFEPATH_SMTP_PASSWORD=abcdefghijklmnop
   SAFEPATH_CONTACTO_EMAIL=maria.flores@gmail.com
   ```

### Como funciona

- Al transicionar a ALERTA (por escalamiento automatico o `/trigger`), el sistema lanza un hilo en segundo plano que envia el email
- El envio no bloquea la maquina de estados
- Si falta configuracion (`.env` incompleto), solo imprime un aviso en logs
- La notificacion se envia solo una vez por transicion a ALERTA

---

## Desarrollo

### Ejecutar tests

```bash
pytest tests/ -v                     # todos los tests
pytest tests/test_logic.py -v        # solo maquina de estados
pytest tests/ --cov=safepath_mvp     # con cobertura
```

Los tests no requieren celular ni conexion WiFi. Todo se ejecuta en memoria.

### Linter y formateador

```bash
ruff check .        # revisar errores de estilo
ruff format .       # formatear automaticamente
ruff check --fix .  # corregir errores automaticos
```

### Guia de contribucion

Ver [CONTRIBUTING.md](CONTRIBUTING.md) para el flujo de trabajo con ramas,
convenciones de codigo y reglas de imports entre modulos.

---

## Demo en vivo -- guion de 2 min 30 s

```
0:00-0:60   Narrativa: "Son las 11pm. Ana sale de la universidad y regresa
            sola a casa caminando. Antes de salir activo el Modo Trayecto
            Seguro en su pulsera Safe-Path. El sistema esta monitoreando."

0:60-1:30   Variante A -- Cancelacion:
            Sacudir celular -> VERIFICANDO -> CANCELAR -> NORMAL

1:30-2:30   Variante B -- Escalamiento:
            Sacudir celular -> VERIFICANDO -> (no cancelar) -> ALERTA

2:30+       Abrir preguntas del jurado
```

---

*SAFE-PATH MVP - SafeCorp - v1.0 - Mayo 2026*
