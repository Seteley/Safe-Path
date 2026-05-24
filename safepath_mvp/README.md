# 🟣 SAFE-PATH — MVP Demo

Sistema de seguridad preventiva para mujeres. Una pulsera inteligente (simulada con el celular) detecta sacudidas bruscas mediante el acelerómetro, inicia un proceso de verificación con cuenta regresiva, y escala la alerta automáticamente si la usuaria no cancela. Todo en tiempo real.

---

## Arquitectura

```
┌──────────────────────────┐     HTTP POST cada 100ms     ┌──────────────────────┐
│  CELULAR (Sensor Logger) │ ──────────────────────────►  │  server.py (Flask)   │
│  acelerómetro + GPS      │    JSON: ax, ay, az, lat,    │  puerto 5000          │
│                           │           lon                │  máquina de estados  │
└──────────────────────────┘                               └──────┬───────────────┘
                                                                  │ state.json
                                                                  ▼
┌──────────────────────────┐                               ┌──────────────────────┐
│  dashboard.py (Streamlit)│ ◄──── lee state.json ──────── │  logic.py            │
│  panel visual en tiempo  │    cada 1 segundo             │  detectar→verificar  │
│  real con mapa + estado  │                               │  →escalar→resolver   │
└──────────────────────────┘                               └──────────────────────┘
```

- **Una sola laptop** ejecuta el servidor Flask y el dashboard Streamlit en paralelo
- **El celular** con Sensor Logger transmite acelerómetro y GPS por WiFi a la laptop
- **state.json** es el archivo compartido que sincroniza ambos procesos
- Todo en **Python puro**, sin MQTT, sin broker externo, sin servidores en la nube

---

## Estructura del proyecto

```
safepath_mvp/
├── config.py          Parámetros configurables (umbrales, tiempos, IP, puerto)
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
| `config.py` | Python | Contiene todas las constantes del sistema: umbral de aceleración (15 m/s²), duración de la verificación (10 s), duración de la alerta (30 s), host, puerto, datos de la usuaria de prueba y ubicación de referencia. Cambiar cualquier valor aquí afecta a todo el sistema. |
| `logic.py` | Python | Implementa la máquina de estados con 5 estados posibles: `NORMAL`, `VERIFICANDO`, `ALERTA`, `RESUELTO`. Maneja temporizadores en hilos separados para el countdown y el auto-escalamiento. Contiene el historial de eventos (últimos 8). Guarda el estado completo en `state.json` en cada cambio. También almacena las coordenadas GPS recibidas del celular. |
| `server.py` | Python + Flask | Servidor HTTP que expone 4 endpoints: `POST /sensor` (recibe JSON del celular con acelerómetro y GPS), `POST /cancel` (cancela manualmente una verificación activa), `GET /state` (devuelve el estado actual), `GET /ping` (health check). Incluye funciones de parsing flexibles que extraen aceleración y coordenadas de múltiples formatos JSON distintos — compatible con cualquier versión de Sensor Logger. |
| `dashboard.py` | Python + Streamlit + Folium | Interfaz visual de 2 columnas. Columna izquierda: indicador de estado con color, nombre de usuaria, ubicación GPS en vivo, aceleración actual con barra de progreso, flujo D→V→E como tres nodos iluminados, y cuenta regresiva con botón de cancelación durante `VERIFICANDO`. Columna derecha: mapa interactivo con Folium centrado en las coordenadas reales del celular (marcador que cambia de color según el estado), y panel de historial con los últimos 8 eventos. Se auto-refresca cada 1 segundo. |
| `state.json` | JSON | Archivo de intercambio. `logic.py` lo escribe en cada cambio de estado o actualización de sensor. `dashboard.py` lo lee constantemente. Contiene: estado actual, aceleración, countdown, coordenadas GPS, historial y umbral. No se edita a mano — se regenera automáticamente. |

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

| Transición | Disparador |
|---|---|
| `NORMAL → VERIFICANDO` | Aceleración neta supera 15 m/s² (sacudida del celular) |
| `VERIFICANDO → NORMAL` | Usuario presiona "CANCELAR ALERTA" antes de que termine el countdown |
| `VERIFICANDO → ALERTA` | El countdown de 10 segundos llega a 0 sin cancelación |
| `ALERTA → RESUELTO` | Manual o automático a los 30 segundos |
| `RESUELTO → NORMAL` | Automático después de 5 segundos |

---

## Requisitos

- **Python 3.9+**
- **Celular** con iOS o Android y la app gratuita **Sensor Logger**
- **Misma red WiFi** entre la laptop y el celular (o hotspot del celular hacia la laptop)

### Dependencias Python

```
flask               Servidor HTTP local
streamlit           Dashboard interactivo
folium              Mapa interactivo
streamlit-folium    Integración Streamlit + Folium
requests            Cliente HTTP (para el botón cancelar del dashboard)
```

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
pip install flask streamlit folium streamlit-folium requests
```

---

## Configuración del celular (Sensor Logger)

1. Instalar **Sensor Logger** desde Play Store (Android) o App Store (iOS) — es gratuita
2. Conectar el celular a la **misma red WiFi** que la laptop
3. En Sensor Logger, ir a **Settings → Streaming**:
   - Activar **HTTP Push**
   - **URL:** `http://<IP_DE_LA_LAPTOP>:5000/sensor` (ej: `http://192.168.1.44:5000/sensor`)
   - **Intervalo:** 100 ms
   - Activar solo los sensores: **acelerómetro** y **ubicación/GPS**
4. Para encontrar la IP de la laptop:
   - Windows: abrir `cmd`, ejecutar `ipconfig`, buscar `Dirección IPv4`
   - Mac/Linux: `ifconfig` o `ip a`
5. Opcional: desactivar el resto de sensores para no saturar la red local

El servidor Flask imprime la IP detectada al iniciar:
```
IP local detectada: 192.168.1.44
Sensor endpoint:  http://192.168.1.44:5000/sensor
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
5. **Presionar CANCELAR** — la usuaría confirma que fue una falsa alarma
6. El sistema vuelve a **🟢 NORMAL** — se registró como cancelación manual

### Variante B — Escalamiento (alerta real)

1. Sacudir el celular bruscamente de nuevo
2. Entra en **🟡 VERIFICANDO** con countdown
3. **No cancelar** — dejar que el countdown llegue a 0
4. El sistema escala automáticamente a **🔴 ALERTA**
5. El dashboard cambia a fondo rojo, muestra "ALERTA ACTIVA", registra el timestamp
6. A los 30 segundos se resuelve automáticamente → **🔵 RESUELTO** → vuelve a NORMAL

### Sin celular (debug)

Si no hay celular disponible, abrir en el navegador de la laptop:
```
http://localhost:5000/debug/trigger
```
Esto inyecta una aceleración de 20 m/s² directamente, disparando todo el flujo.

---

## Plan B — si algo falla

| Problema | Solución |
|---|---|
| Sensor Logger no conecta | Verificar que laptop y celular estén en la misma WiFi. Probar `http://<IP>:5000/ping` desde el navegador del celular |
| El dashboard no reacciona | Usar `http://localhost:5000/debug/trigger` para disparar estados manualmente |
| Dashboard va lento | Cambiar `time.sleep(1)` a `time.sleep(2)` en `dashboard.py:149` |
| Puerto 5000 ocupado | `netstat -ano | findstr :5000` para ver quién lo usa, cambiar `PORT` en `config.py` |
| Firewall bloquea | Ejecutar como administrador: `netsh advfirewall firewall add rule name="Flask 5000" dir=in action=allow protocol=TCP localport=5000` |
| Todo falla | Tener un video grabado previamente del caso de uso funcionando |

---

## Parámetros configurables

Todos en `config.py`:

```python
UMBRAL_ACELERACION = 15.0   # m/s² — aceleración neta que dispara la detección
TIEMPO_VERIFICACION = 10    # segundos de countdown antes de escalar
DURACION_ALERTA = 30        # segundos que dura el estado de alerta
HOST = "0.0.0.0"            # escucha en todas las interfaces de red
PORT = 5000                 # puerto del servidor Flask
USUARIA = "Ana Flores"      # nombre mostrado en el dashboard
CONTACTO = "María Flores (mamá)"  # contacto de emergencia
UBICACION_LAT = -12.0833    # latitud de referencia (Jesús María, Lima)
UBICACION_LON = -77.0500    # longitud de referencia
DIRECCION = "Av. La Marina 1200, Jesús María"  # dirección de referencia
```

El umbral de **15 m/s²** está calibrado para que:
- Caminar normal (2-4 m/s²) **no** active el sistema
- Una sacudida intencional (20-30 m/s²) **sí** lo active
- Ajustar este valor según el caso de uso y el dispositivo

---

## Demo en vivo — guion de 2 min 30 s

```
0:00-0:60   Narrativa: "Son las 11pm. Ana sale de la universidad y regresa
            sola a casa caminando. Antes de salir activó el Modo Trayecto
            Seguro en su pulsera Safe-Path."

0:60-1:30   Variante A — Cancelación:
            Sacudir celular → VERIFICANDO → CANCELAR → NORMAL

1:30-2:30   Variante B — Escalamiento:
            Sacudir celular → VERIFICANDO → (no cancelar) → ALERTA

2:30+       Abrir preguntas del jurado
```
