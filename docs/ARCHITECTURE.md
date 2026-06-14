# Documentación técnica — GREENSOFT Testing Framework

Este documento describe la arquitectura interna, el modelo de concurrencia, el flujo de datos, el contrato de la API y los puntos de extensión del proyecto.

> Para instalación y uso, consulta el [README](../README.md).

---

## Tabla de contenidos

- [Visión general](#visión-general)
- [Componentes](#componentes)
- [Flujo de datos](#flujo-de-datos)
- [Modelo de concurrencia](#modelo-de-concurrencia)
- [Modelo de datos](#modelo-de-datos)
- [Contrato de la API](#contrato-de-la-api)
- [Generación de reportes](#generación-de-reportes)
- [Herramientas CLI](#herramientas-cli)
- [Despliegue](#despliegue)
- [Puntos de extensión](#puntos-de-extensión)
- [Limitaciones conocidas](#limitaciones-conocidas)

---

## Visión general

La aplicación es un **monolito Flask** que sirve tanto la interfaz (una SPA ligera en `templates/index.html` + `static/`) como una **API REST** que orquesta sesiones de testing.

El patrón central es **lanzar-y-sondear** (*fire-and-poll*):

1. El cliente hace `POST /api/start-test` y recibe un `session_id`.
2. El servidor lanza el trabajo en un **hilo en segundo plano** y responde de inmediato.
3. El cliente **sondea** (`polling`) `GET /api/test-status/<id>` y `GET /api/test-logs/<id>` para mostrar progreso y logs en vivo.
4. Al terminar, el cliente pide el reporte (`/api/test-report/<id>`) y, opcionalmente, el PDF.

```mermaid
graph TD
    Browser["🖥️ Navegador<br/>(index.html + main.js)"]
    CLI["⌨️ CLIs<br/>(monitor / batch / check)"]

    subgraph Flask["Proceso Flask (1 worker gunicorn)"]
        API["API REST<br/>(rutas en app.py)"]
        Runner["TestRunner<br/>(hilo daemon por sesión)"]
        Store["Estado en memoria<br/>test_sessions / test_logs"]
        ISTQB["ISTQBBugReport"]
        PDF["PDFReportGenerator<br/>(reportlab)"]
    end

    Browser -->|HTTP/JSON| API
    CLI -->|HTTP/JSON| API
    API -->|crea/lee| Store
    API -->|lanza| Runner
    Runner -->|escribe progreso y logs| Store
    API --> ISTQB
    API --> PDF
```

---

## Componentes

| Archivo | Responsabilidad | Notas |
|---|---|---|
| `app.py` | Servidor Flask, rutas de la API, clase `TestRunner` y almacén en memoria | Punto de entrada. |
| `istqb_report_generator.py` | Clase `ISTQBBugReport`: normaliza un bug al esquema ISTQB (severidad→prioridad, entorno, pasos, adjuntos…). | Modelo de datos de defectos. |
| `pdf_generator.py` | Clase `PDFReportGenerator`: arma el PDF con `reportlab` (portada, resumen, tabla por bug). | Estilo de marca Greensoft (`#00ff99`). |
| `templates/index.html` | Dashboard de una sola página. | Servida por la ruta `/`. |
| `static/js/main.js` | Lógica de cliente: inicia tests, hace polling, renderiza progreso/logs/reporte. | |
| `static/css/style.css` | Estilos del dashboard. | |
| `monitor.py`, `batch_test.py`, `check_server.py` | Clientes de línea de comandos sobre la misma API. | Útiles para automatización/CI. |

### Anatomía de `TestRunner` (`app.py`)

Cada sesión instancia un `TestRunner(session_id, target_url, mode)` que se ejecuta en su propio hilo. Su método `run()` ejecuta fases según el modo:

| Modo | Fases ejecutadas | Progreso |
|---|---|---|
| `quick` | `_phase_basic` | 20% → 100% |
| `standard` | `_phase_basic` → `_phase_iterative` → `_phase_api` | 20% → 60% → 100% |
| `deep` | las 3 anteriores + `_phase_advanced` | 20% → 80% → 100% |

Métodos auxiliares:
- `add_log(message, level)` — agrega una línea con timestamp y la sincroniza con `test_logs[session_id]`.
- `update_progress(progress, phase)` — actualiza `test_sessions[session_id]`.

> ⚠️ Hoy las fases `_phase_*` **simulan** trabajo con `time.sleep()` y emiten logs/bugs de ejemplo. Aquí es donde se conecta la lógica de pruebas real (ver [Puntos de extensión](#puntos-de-extensión)).

---

## Flujo de datos

```mermaid
sequenceDiagram
    participant C as Cliente (navegador/CLI)
    participant A as API Flask
    participant S as Estado en memoria
    participant T as TestRunner (hilo)

    C->>A: POST /api/start-test {target_url, mode}
    A->>S: crea test_sessions[id], test_logs[id]
    A->>T: Thread(target=runner.run).start()
    A-->>C: 200 {session_id}

    loop polling hasta status != "running"
        C->>A: GET /api/test-status/{id}
        A->>S: lee progreso/fase
        A-->>C: {status, progress, current_phase}
        C->>A: GET /api/test-logs/{id}?offset=N
        A->>S: lee logs[N:]
        A-->>C: {logs, total}
        T->>S: actualiza progreso y agrega logs
    end

    C->>A: GET /api/test-report/{id}
    A-->>C: {bugs, bugs_by_severity, ...}
    C->>A: GET /api/test-report-pdf/{id}
    A->>A: PDFReportGenerator.generate_pdf(...)
    A-->>C: application/pdf (descarga)
```

El parámetro `offset` en `/api/test-logs` permite **streaming incremental**: el cliente solo pide las líneas nuevas desde la última que ya tiene.

---

## Modelo de concurrencia

Este es el aspecto más delicado del sistema y condiciona el despliegue.

- **Estado compartido en memoria.** `test_sessions` y `test_logs` son diccionarios globales del proceso. No hay base de datos.
- **Un hilo por sesión.** `POST /api/start-test` lanza un `threading.Thread(daemon=True)`. Como es *daemon*, no bloquea el cierre del proceso.
- **El servidor de producción DEBE correr con un solo worker.**

```bash
gunicorn app:app --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:$PORT
```

¿Por qué?

```mermaid
graph LR
    subgraph Mal["❌ --workers 2 (procesos separados)"]
        W1["Worker A<br/>test_sessions = {id: ...}"]
        W2["Worker B<br/>test_sessions = {}"]
    end
    C1["POST /start-test"] --> W1
    C2["GET /status/id"] --> W2
    W2 -.->|404 No encontrado| X["💥"]
```

Con varios *workers*, cada proceso tiene **su propia copia** de los diccionarios. La petición de inicio podría atender el Worker A (que guarda la sesión) y el sondeo de estado podría caer en el Worker B (que no la tiene) → `404`.

La solución correcta es **1 worker + varios hilos**:
- `--workers 1`: un único proceso, un único almacén en memoria coherente.
- `--threads 8`: el worker atiende varias peticiones HTTP concurrentes (el sondeo de status/logs no se bloquea mientras el hilo del test trabaja).

> Si en el futuro necesitas escalar horizontalmente (varios workers o varias instancias), primero hay que **externalizar el estado** a Redis o una base de datos. Ver [Roadmap](../README.md#-roadmap).

---

## Modelo de datos

### Sesión (`test_sessions[session_id]`)

```json
{
  "session_id": "a1b2c3d4",
  "target_url": "https://example.com",
  "mode": "standard",
  "status": "running",          // running | completed | cancelled | error
  "progress": 60,                // 0–100
  "current_phase": "Análisis de APIs",
  "start_time": "2026-06-14T17:00:00"
}
```

El `session_id` es los primeros 8 caracteres de un `uuid4`.

### Logs (`test_logs[session_id]`)

Lista de cadenas con formato `[HH:MM:SS] NIVEL: mensaje` (niveles: `INFO`, `SUCCESS`, `ERROR`).

### Defecto en formato ISTQB (`ISTQBBugReport`)

`ISTQBBugReport.add_bug()` normaliza cada bug a un esquema completo: `bug_id`, `title`, `summary`, `environment` (browser/os/test_data/network), `severity`, `priority` (mapeada desde la severidad), `type`, `status`, `steps_to_reproduce`, `expected_result`, `actual_result`, `attachments`, `services_affected`, `impact`, etc.

Mapeo severidad → prioridad:

| Severidad | Prioridad |
|---|---|
| `CRITICAL` | P1 - INMEDIATA |
| `HIGH` | P2 - URGENTE |
| `MEDIUM` | P3 - NORMAL |
| `LOW` | P4 - BAJA |

---

## Contrato de la API

Todas las respuestas son JSON salvo el PDF. Errores devuelven `{ "error": "mensaje" }` con el código HTTP correspondiente.

### `POST /api/start-test`
- **Body:** `{ "target_url": "http(s)://...", "mode": "quick" | "standard" | "deep" }`
- **200:** `{ "session_id": "a1b2c3d4" }`
- **400:** la URL no empieza por `http://` o `https://` → `{ "error": "URL inválida" }`

### `GET /api/test-status/<session_id>`
- **200:** `{ session_id, status, progress, current_phase }`
- **404:** sesión inexistente.

### `GET /api/test-logs/<session_id>?offset=N`
- **200:** `{ "logs": [...], "total": N }` — `logs` contiene las líneas desde `offset`.
- **404:** sesión inexistente.

### `GET /api/test-report/<session_id>`
- **200:** `{ session_id, target_url, mode, status, total_bugs, bugs_by_severity, bugs[], deployment_recommendation }`
- **404:** sesión inexistente.

### `GET /api/test-report-pdf/<session_id>`
- **200:** `application/pdf` como adjunto (`report-<id>.pdf`).
- **404 / 500:** sesión inexistente o error generando el PDF.

### `GET /api/features`
- **200:** lista de las 8 áreas: `[{ id, name, icon }, ...]`.

### `POST /api/cancel-test/<session_id>`
- **200:** `{ "status": "ok" }` — marca la sesión como `cancelled`.

### `POST /api/clear-history`
- **200:** `{ "status": "ok" }` — vacía `test_sessions` y `test_logs`.

---

## Generación de reportes

`PDFReportGenerator.generate_pdf(filename, session_id, target_url, mode, bugs)` produce un PDF A4 con `reportlab`:

1. **Portada / header** con título e identidad Greensoft.
2. **Tabla de sesión** (proyecto, URL, session_id, modo, fecha).
3. **Resumen ejecutivo** con conteo por severidad.
4. **Una sección por bug**: encabezado coloreado por severidad + tabla de detalle (descripción, esperado, actual, impacto, servicios).

> Nota de implementación: la ruta `/api/test-report-pdf` genera el PDF en un archivo temporal, lo lee a memoria (`BytesIO`) y borra el temporal antes de responder. Es un *workaround* funcional; una mejora futura es que `generate_pdf` escriba directamente a un buffer en memoria.

---

## Herramientas CLI

Las tres son clientes HTTP de la misma API (`API_URL = http://localhost:5000`):

- **`check_server.py`** — verifica salud: hace `GET /` y `GET /api/features`, reintenta hasta 5 veces.
- **`monitor.py <url> [modo]`** — inicia una sesión y muestra progreso + logs en vivo con códigos de color por severidad, luego imprime el reporte.
- **`batch_test.py`** — recorre una lista de URLs (`URLS`), ejecuta cada una, agrega resultados en una tabla resumen y guarda `batch_report_<timestamp>.json`.

Estas herramientas son la base natural para integrar el framework en **CI** (por ejemplo, fallar el build si aparecen bugs `CRITICAL`).

---

## Despliegue

Definido como código en [`render.yaml`](../render.yaml):

```yaml
services:
  - type: web
    name: greensoft-testing
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:$PORT
```

- El puerto se lee de la variable de entorno `PORT` (inyectada por Render) tanto en `app.run` (desarrollo) como vía `--bind` en gunicorn (producción).
- Redeploy automático en cada push a la rama por defecto.
- **Plan free:** el servicio se suspende tras ~15 min sin tráfico (arranque en frío al volver) y, al reiniciarse, **se pierde el estado en memoria**.

---

## Puntos de extensión

El lugar para convertir la demo en un framework de pruebas real es la clase **`TestRunner`** en `app.py`. Cada método `_phase_*` debe:

1. Ejecutar pruebas reales contra `self.target_url`.
2. Emitir logs con `self.add_log(...)`.
3. Acumular defectos en `self.bugs` (en el esquema que consume `ISTQBBugReport`).

Ejemplo de dirección para `_phase_basic` usando peticiones reales:

```python
import requests

def _phase_basic(self):
    self.add_log("✓ Verificando disponibilidad")
    try:
        resp = requests.get(self.target_url, timeout=10)
        if resp.status_code >= 400:
            self.bugs.append({
                "severity": "HIGH",
                "title": f"La URL responde {resp.status_code}",
                "description": "El recurso principal no está disponible.",
                "services": ["Frontend"],
            })
    except requests.RequestException as e:
        self.bugs.append({
            "severity": "CRITICAL",
            "title": "El sitio no responde",
            "description": str(e),
            "services": ["Infra"],
        })
```

Después, ajusta `/api/test-report` para que devuelva `runner.bugs` reales (hoy devuelve datos de ejemplo). Para pruebas de navegador (UI real), integra **Selenium** o **Playwright**; para análisis de HTML/endpoints, `requests` + `beautifulsoup4`.

Otros puntos de extensión:
- **Persistencia:** sustituir los diccionarios en memoria por Redis/SQLite para sobrevivir reinicios y habilitar múltiples workers.
- **JIRA:** en `ISTQBBugReport`, añadir un método que cree issues vía la API de JIRA.
- **Formatos de reporte:** añadir export HTML/CSV junto al PDF existente.

---

## Limitaciones conocidas

1. **Motor de pruebas simulado** — las fases no ejecutan pruebas reales todavía.
2. **Estado volátil** — todo vive en memoria; un reinicio borra sesiones y reportes.
3. **Un solo worker** — no escala horizontalmente hasta externalizar el estado.
4. **Sin autenticación** — cualquiera con la URL puede lanzar tests; no exponer públicamente sin proteger.
5. **PDF vía archivo temporal** — funciona, pero conviene migrar a buffer en memoria.
