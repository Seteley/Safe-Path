# Guia de contribucion - SAFE-PATH MVP

## Configuracion inicial

```bash
git clone <repo>
cd "prueba safepath"
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Mac/Linux
pip install -e ".[dev]"
pre-commit install
```

## Flujo de trabajo

1. Crear rama desde `main`:

   ```
   git checkout -b feature/nombre-corto
   ```

   Tipos de rama:
   - `feature/*` - nueva funcionalidad
   - `fix/*` - correccion de bug
   - `docs/*` - solo documentacion

2. Hacer cambios. Ejecutar antes de commit:

   ```
   ruff check .
   ruff format .
   pytest tests/ -v
   ```

3. Commit con mensaje claro:

   ```
   feat(parser): agregar soporte para formato Phyphox
   fix(logic): cancelar timers huerfanos en reset()
   ```

4. Push y crear Pull Request.

## Organizacion del codigo

| Directorio/Package | Contenido |
|-------------------|-----------|
| `simulador/` | Servidor Flask, maquina de estados, parser, notificaciones, config |
| `dashboard/` | Panel Streamlit y componentes visuales |
| `shared/` | Contrato state.json (`schema.py`) y utilidades (`utils.py`) |

### Reglas de imports

| Desde | Puede importar de |
|-------|-------------------|
| `simulador/*` | `shared/*`, otros `simulador/*` |
| `dashboard/*` | `shared/*` |
| `shared/*` | Ningun otro modulo interno |

`shared/` es el contrato compartido. Cambios en `schema.py` afectan a ambos
modulos y deben coordinarse.

## Pruebas

```bash
pytest tests/ -v                      # todos los tests
pytest tests/test_logic.py -v         # solo maquina de estados
pytest tests/test_parser.py -v        # solo parser
pytest tests/test_server.py -v        # solo endpoints
pytest tests/ -x --pdb                # parar en primer fallo con debugger
pytest tests/ --cov=safepath_mvp --cov-report=term-missing
```

Los tests no requieren celular ni conexion WiFi. Todo se ejecuta en memoria.

## Estilo

- Ruff formatea automaticamente (pre-commit hook)
- Type hints en funciones publicas y metodos de clase
- Nombres en espanol para dominio de negocio (estado, usuaria, umbral)
- Nombres en ingles para terminos tecnicos (callback, timer, parser)
- Lineas de maximo 100 caracteres
