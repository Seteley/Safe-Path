# 🟣 SAFE-PATH — MVP Demo

Sistema de seguridad preventiva para mujeres. Una pulsera inteligente (simulada con el celular) detecta sacudidas bruscas mediante el acelerómetro, inicia un proceso de verificación con cuenta regresiva, y escala la alerta automáticamente si la usuaria no cancela. Todo en tiempo real.

---

## Arquitectura

```
┌──────────────────────────┐     HTTP POST cada 100ms     ┌──────────────────────┐
│  CELULAR (Sensor Logger) │ ──────────────────────────►  │  server.py (Flask)   │
│  acelerómetro + GPS      │    JSON payload con          │  puerto 5000          │
│                           │    ax,ay,az,lat,lon          │  + logic.py          │
└──────────────────────────┘                               └──────┬───────────────┘
                                                                  │ state.json
                                                          escritura atómica
                                                          (os.replace)
                                                                  ▼
┌──────────────────────────┐                               ┌──────────────────────┐
│  dashboard.py (Streamlit)│ ◄──── lee state.json ──────── │  logic.py            │
│  panel visual en tiempo  │    cada 1 segundo             │  detectar→verificar  │
│  real con mapa + estado  │                               │  →escalar→resolver   │
└──────────────────────────┘                               └──────────────────────┘
```

- **Una sola laptop** ejecuta el servidor Flask y el dashboard Streamlit en paralelo
- **El celular** con Sensor Logger transmite acelerómetro y GPS por WiFi a la laptop
- **`state.json`** es el archivo compartido que sincroniza ambos procesos — se escribe atómicamente con `os.replace`
- **`schema.py`** define el contrato del JSON para que backend y dashboard trabajen sin romperse
- Todo en **Python puro**, sin MQTT, sin broker externo, sin servidores en la nube

---

## Estructura del proyecto

```
safepath_mvp/
├── config.py          Parámetros configurables (umbrales, tiempos, IP, puerto)
├── schema.py          Contrato del state.json compartido entre backend y dashboard
├── logic.py           Máquina de estados D→V→E (detectar, verificar, escalar)
├── server.py          Servidor Flask que recibe datos del celular vía HTTP POST
├── dashboard.py       Panel visual Streamlit con mapa, estado y cuenta regresiva
├── state.json         Estado compartido entre Flask y Streamlit (se regenera solo)
├── assets/
│   └── pulsera.png    Imagen del mockup de la pulsera Safe-Path (generada con IA)
└── README.md          Este archivo
```

| Archivo | Lenguaje | Propósito |
|---|---|---|
| `config.py` | Python | Contiene todas las constantes del sistema: umbral de aceleración (15 m/s²), umbral de movimiento GPS (~4m), duración de la verificación (10 s), duración de la alerta (30 s), host, puerto, datos de la usuaria de prueba y ubicación de referencia. Cambiar cualquier valor aquí afecta a todo el sistema. |
| `schema.py` | Python | Define el contrato explícito del `state.json` que comparten backend y dashboard: nombres exactos de los campos, tipos, valores por defecto, estados válidos, y los campos que componen cada entrada del historial. Ambos equipos importan desde aquí para no romperse mutuamente. |
| `logic.py` | Python | Implementa la máquina de estados con 5 estados: `NORMAL`, `VERIFICANDO`, `ALERTA`, `RESUELTO`. Maneja temporizadores en hilos separados para el countdown y auto-escalamiento. Contiene `force_state()` (forzar cualquier estado vía `/trigger`), `reset()` (reinicio limpio para cada demo vía `/reset`), `update_location()` (GPS). Guarda el estado en `state.json` con escritura atómica (`os.replace`) para evitar corrupción. Historial de últimos 10 eventos con timestamps ISO 8601, flags de cancelado/escalado/forzado. |
| `server.py` | Python + Flask | Servidor HTTP que expone 7 endpoints (ver tabla abajo). Incluye funciones de parsing flexibles que extraen aceleración y coordenadas GPS de múltiples formatos JSON — compatible con cualquier versión de Sensor Logger. Los sensores no reconocidos reciben 400 con las claves detectadas para facilitar el debug. Soporta aliases `/sensor` y `/state` para compatibilidad con versiones anteriores. |
| `dashboard.py` | Python + Streamlit + Folium | Interfaz visual de 2 columnas. Columna izquierda: imagen de la pulsera, indicador de estado con color SafeCorp (#22c55e/#eab308/#ef4444/#6b7280), nombre de usuaria, ubicación GPS, aceleración con barra de progreso, flujo D→V→E con nodos iluminados, cuenta regresiva calculada localmente desde `timestamp_inicio_verificando`, botón de cancelación y "Contacto notificado" en ALERTA. Columna derecha: mapa Folium pre-renderizado como HTML estático (se reconstruye solo al cambiar de estado o al detectar >4m de movimiento real), y panel de historial. Se auto-refresca cada 1 segundo. |
| `state.json` | JSON | Archivo de intercambio. `logic.py` lo escribe atómicamente en cada cambio de estado o actualización de sensor. `dashboard.py` lo lee constantemente. Contiene: estado, aceleración actual, countdown, timestamps ISO 8601, historial de objetos, datos de usuaria, coordenadas GPS, dirección y umbral. No se edita a mano — se regenera automáticamente. |

---

## Máquina de estados

```
NORMAL ──(aceleración > 15 m/s²)──► VERIFICANDO ──(10s sin cancelar)──► ALERTA
  ▲                                      │                                  │
  │                              (usuario cancela)                   (30s o manual)
  │                                      │                                  │
  └──────────────────────────────────────┘                                  ▼
  ▲                                                                   RESUELTO
  └────────────────────────────────────(5s)──────────────────────────────┘
```

Los estados también pueden forzarse manualmente con `/trigger?estado=X` y reiniciarse con `/reset`.

| Transición | Disparador | Endpoint |
|---|---|---|
| `NORMAL → VERIFICANDO` | Aceleración neta supera 15 m/s² (sacudida del celular) | `POST /data` |
| `VERIFICANDO → NORMAL` | Usuario presiona "CANCELAR ALERTA" antes de que termine el countdown | `GET /cancel` |
| `VERIFICANDO → ALERTA` | El countdown de 10 segundos llega a 0 sin cancelación | Automático (threading.Timer) |
| `ALERTA → RESUELTO` | 30 segundos transcurridos | Automático (threading.Timer) |
| `RESUELTO → NORMAL` | 5 segundos transcurridos | Automático (threading.Timer) |
| `CUALQUIERA → X` | Forzado manualmente (debug / Plan B) | `GET /trigger?estado=X` |
| `CUALQUIERA → NORMAL` | Reinicio limpio para nueva demo | `GET /reset` |

---

## APIs del servidor Flask

| Método | Endpoint | Descripción | Respuesta |
|---|---|---|---|
| `POST` | `/data` | Recibe datos del acelerómetro y GPS desde Sensor Logger | `{"status": "ok", "accel": 0.23}` |
| `GET` | `/status` | Retorna el estado actual completo (contenido de state.json) | `{"estado": "NORMAL", ...}` |
| `GET` / `POST` | `/cancel` | Cancela una verificación activa: `VERIFICANDO → NORMAL` | `{"status": "cancelado"}` |
| `GET` | `/trigger?estado=X` | Fuerza cualquier estado (`NORMAL`, `VERIFICANDO`, `ALERTA`, `RESUELTO`). Usar para debug sin celular. | `{"status": "ok", "estado": "ALERTA"}` |
| `GET` | `/reset` | Reinicia el sistema a NORMAL para empezar una nueva demo. Cancela todos los timers activos y limpia el historial. | `{"status": "reseteado", "estado": "NORMAL"}` |
| `GET` | `/ping` | Health check simple — verifica que el servidor está vivo | `{"status": "alive", "state": "NORMAL"}` |
| `POST` | `/sensor` | **Alias** de `/data` — compatibilidad con versiones anteriores | Igual que `/data` |
| `GET` | `/state` | **Alias** de `/status` — compatibilidad con versiones anteriores | Igual que `/status` |

---

## Modelo de datos — state.json

Especificación exacta del JSON compartido. Este formato está definido en `schema.py` y es el contrato entre backend y dashboard.

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
  "contacto": "María Flores (mamá)",
  "lat": -12.0833,
  "lon": -77.0500,
  "direccion": "Av. La Marina 1200, Jesús María",
  "umbral": 15.0
}
```

| Campo | Tipo | Descripción |
|---|---|---|
| `estado` | `string` | Uno de: `NORMAL`, `VERIFICANDO`, `ALERTA`, `RESUELTO` |
| `aceleracion_actual` | `float` | Última aceleración neta recibida (m/s²) |
| `countdown_restante` | `int` | Segundos restantes del countdown (0 fuera de VERIFICANDO) |
| `timestamp_cambio` | `string` | ISO 8601 UTC del último cambio de estado |
| `timestamp_inicio_verificando` | `string` / `null` | ISO 8601 UTC de cuándo entró a VERIFICANDO. `null` si no está en ese estado |
| `historial` | `array` | Últimos 10 eventos. Cada entrada tiene: `estado`, `timestamp`, `aceleracion`, y flags opcionales `cancelado`, `escalado`, `forzado` |
| `usuaria` | `string` | Nombre de la usuaria (desde config.py) |
| `contacto` | `string` | Nombre del contacto de emergencia (desde config.py) |
| `lat` | `float` | Latitud actual (GPS real del celular, o coordenada de referencia) |
| `lon` | `float` | Longitud actual |
| `direccion` | `string` | Dirección de referencia |
| `umbral` | `float` | Umbral de aceleración configurado (m/s²) |

---

## Optimización del mapa (sin parpadeo)

El dashboard implementa 3 mecanismos para que el mapa Folium no parpadee:

1. **Pre-renderizado HTML** — El mapa Folium se convierte a string HTML una sola vez y se guarda en `st.session_state`. Se usa `st.components.v1.html()` en lugar de `st_folium()`. Al ser un string idéntico entre ciclos, el navegador no recarga el iframe.

2. **Umbral de movimiento GPS** — `UMBRAL_MOVIMIENTO_GPS = 0.00004` (~4 metros). El ruido del GPS (fluctuaciones de 0.000006°) se ignora. Solo se reconstruye el mapa cuando la persona realmente camina >4m.

3. **Reconstrucción por cambio de estado** — El mapa siempre se reconstruye cuando cambia el estado, para reflejar el nuevo color del marcador. Esto ocurre solo 3-4 veces durante toda la demo.

**Resultado:** mapa estable sin parpadeo, se actualiza automáticamente al caminar o al cambiar de estado.

---

## Requisitos

- **Python 3.9+**
- **Celular** con iOS o Android y la app gratuita **Sensor Logger**
- **Misma red WiFi** entre la laptop y el celular (o hotspot del celular hacia la laptop)

### Dependencias Python

```
flask               Servidor HTTP local
streamlit           Dashboard interactivo
folium              Mapa interactivo (renderizado de HTML)
requests            Cliente HTTP (para el botón cancelar del dashboard)
```

Ya no se requiere `streamlit-folium`: el mapa se renderiza como HTML estático con `st.components.v1.html()`.

---

## Instalación

```bash
# 1. Clonar o copiar la carpeta safepath_mvp en la laptop
cd "safepath_mvp"

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno virtual
# Windows:
venv\Scripts\Activate.ps1
# Mac/Linux:
source venv/bin/activate

# 4. Instalar dependencias
pip install flask streamlit folium requests
```

---

## Configuración del celular (Sensor Logger)

1. Instalar **Sensor Logger** desde Play Store (Android) o App Store (iOS) — es gratuita
2. Conectar el celular a la **misma red WiFi** que la laptop
3. En Sensor Logger, ir a **Settings → Streaming**:
   - Activar **HTTP Push**
   - **URL:** `http://<IP_DE_LA_LAPTOP>:5000/data` (ej: `http://192.168.1.44:5000/data`)
   - **Intervalo:** 100 ms
   - Activar los sensores: **acelerómetro** y **ubicación/GPS**
4. Para encontrar la IP de la laptop:
   - Windows: abrir `cmd`, ejecutar `ipconfig`, buscar `Dirección IPv4`
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

## Cómo ejecutar

Abrir **dos terminales** en la laptop. En ambas, activar el entorno virtual y navegar a `safepath_mvp`:

**Terminal 1 — Servidor Flask (recibe datos del celular):**
```bash
python server.py
```
Debe mostrar: `Running on http://192.168.x.x:5000`

**Terminal 2 — Dashboard Streamlit (panel visual):**
```bash
streamlit run dashboard.py
```
Se abre automáticamente en el navegador en `http://localhost:8501`

**En el celular:** iniciar el streaming en Sensor Logger (botón ▶ Play).

**Verificar conexión:** abrir en el navegador del celular `http://<IP>:5000/ping` — debe responder `{"status":"alive"...}`.

---

## Cómo probar la demo

### Variante A — Cancelación (manejo de falsos positivos)

1. Dashboard muestra estado **🟢 NORMAL** (fondo verde)
2. Sacudir el celular bruscamente
3. El sistema detecta la aceleración anómala y entra en **🟡 VERIFICANDO**
4. Aparece cuenta regresiva de 10 segundos con botón "CANCELAR ALERTA"
5. **Presionar CANCELAR** — la usuaria confirma que fue una falsa alarma
6. El sistema vuelve a **🟢 NORMAL** — se registró como cancelación manual en el historial

### Variante B — Escalamiento (alerta real)

1. Sacudir el celular bruscamente de nuevo
2. Entra en **🟡 VERIFICANDO** con countdown
3. **No cancelar** — dejar que el countdown llegue a 0
4. El sistema escala automáticamente a **🔴 ALERTA**
5. El dashboard cambia a fondo rojo, muestra "Contacto notificado: María Flores (mamá)", registra el timestamp
6. A los 30 segundos se resuelve automáticamente → **🔵 RESUELTO** → vuelve a NORMAL

### Sin celular (debug con endpoints)

```bash
# Simular sacudida (inyecta aceleración de 20 m/s²)
curl http://localhost:5000/trigger?estado=VERIFICANDO

# Cancelar verificación
curl http://localhost:5000/cancel

# Forzar alerta directamente
curl http://localhost:5000/trigger?estado=ALERTA

# Reiniciar para siguiente demo
curl http://localhost:5000/reset
```

O abrir estas URLs directamente en el navegador de la laptop.

---

## Plan B — si algo falla

| Problema | Solución |
|---|---|
| Sensor Logger no conecta | Verificar que laptop y celular estén en la misma WiFi. Probar `http://<IP>:5000/ping` desde el navegador del celular |
| El dashboard no reacciona | Usar `/trigger?estado=VERIFICANDO` para disparar estados manualmente sin celular |
| Necesito reiniciar entre demos | Usar `/reset` para limpiar estado y empezar desde NORMAL |
| Dashboard va lento | Cambiar `time.sleep(1)` a `time.sleep(2)` en `dashboard.py:277` |
| Mapa parpadea | Bajar `UMBRAL_MOVIMIENTO_GPS` en `config.py` (ej: `0.00002` = ~2m) |
| Puerto 5000 ocupado | `netstat -ano | findstr :5000` para ver quién lo usa, cambiar `PORT` en `config.py` |
| Firewall bloquea | Ejecutar como administrador: `netsh advfirewall firewall add rule name="Flask 5000" dir=in action=allow protocol=TCP localport=5000` |
| state.json corrupto | Borrar el archivo; se regenera automáticamente al siguiente arranque del servidor |
| Todo falla | Tener un video grabado previamente del caso de uso funcionando |

---

## Parámetros configurables

Todos en `config.py`:

```python
UMBRAL_ACELERACION = 15.0    # m/s² — aceleración neta que dispara la detección
TIEMPO_VERIFICACION = 10     # segundos de countdown antes de escalar
DURACION_ALERTA = 30         # segundos que dura el estado de alerta
HOST = "0.0.0.0"             # escucha en todas las interfaces de red
PORT = 5000                  # puerto del servidor Flask
USUARIA = "Ana Flores"       # nombre mostrado en el dashboard
CONTACTO = "María Flores (mamá)"  # contacto de emergencia
UBICACION_LAT = -12.0833     # latitud de referencia (Jesús María, Lima)
UBICACION_LON = -77.0500     # longitud de referencia
DIRECCION = "Av. La Marina 1200, Jesús María"  # dirección de referencia
UMBRAL_MOVIMIENTO_GPS = 0.00004  # grados (~4m) para ignorar ruido del sensor GPS
```

- **`UMBRAL_ACELERACION` (15 m/s²):** Caminar normal (2-4 m/s²) no activa. Una sacudida intencional (20-30 m/s²) sí.
- **`UMBRAL_MOVIMIENTO_GPS` (0.00004° ≈ 4m):** Ignora el ruido del GPS del celular. Solo reconstruye el mapa cuando la persona realmente se movió. Reducir a `0.00002` (~2m) si el GPS es muy preciso, o subir a `0.0001` (~11m) si fluctúa mucho.

---

## Demo en vivo — guion de 2 min 30 s

```
0:00-0:60   Narrativa: "Son las 11pm. Ana sale de la universidad y regresa
            sola a casa caminando. Antes de salir activó el Modo Trayecto
            Seguro en su pulsera Safe-Path. El sistema está monitoreando."

0:60-1:30   Variante A — Cancelación:
            Sacudir celular → VERIFICANDO → CANCELAR → NORMAL

1:30-2:30   Variante B — Escalamiento:
            Sacudir celular → VERIFICANDO → (no cancelar) → ALERTA

2:30+       Abrir preguntas del jurado
```
