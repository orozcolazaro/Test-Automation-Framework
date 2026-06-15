# 🟢 GREENSOFT Testing Framework

> Plataforma web para orquestar, monitorear en tiempo real y reportar pruebas automatizadas sobre aplicaciones web. Construida con **Flask** y una interfaz de una sola página, con generación de reportes de defectos en **formato ISTQB** (JSON y PDF).

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0+-000000?logo=flask&logoColor=white)
![Deploy](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render&logoColor=white)
![Status](https://img.shields.io/badge/status-MVP%20%2F%20demo-yellow)
[![Demo en vivo](https://img.shields.io/badge/🟢_Demo_en_vivo-online-46E3B7)](https://greensoft-testing.onrender.com/)

---

## 📑 Tabla de contenidos

- [¿Qué es?](#-qué-es)
- [Estado actual (importante)](#-estado-actual-importante)
- [Características](#-características)
- [Demo en vivo](#-demo-en-vivo)
- [Arranque rápido (local)](#-arranque-rápido-local)
- [Despliegue en Render](#-despliegue-en-render)
- [Uso desde la terminal (CLI)](#-uso-desde-la-terminal-cli)
- [Referencia de la API](#-referencia-de-la-api)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Documentación técnica](#-documentación-técnica)
- [Roadmap](#-roadmap)
- [Licencia](#-licencia)

---

## 🎯 ¿Qué es?

GREENSOFT Testing Framework es una aplicación web que te permite:

1. **Lanzar** una sesión de testing contra una URL objetivo eligiendo un modo (`quick`, `standard`, `deep`).
2. **Seguir el progreso en tiempo real** mediante una barra de avance, fases y un log en vivo.
3. **Obtener un reporte de defectos** clasificado por severidad (CRITICAL / HIGH / MEDIUM / LOW) y descargarlo en **PDF con formato ISTQB**.

Está pensado como base para un asistente de QA: define el *flujo* completo (orquestación → monitoreo → reporte) sobre el cual conectar motores de pruebas reales.

---

## ⚠️ Estado actual

| Componente | Estado |
|---|---|
| Interfaz web, API REST, monitoreo en vivo, descarga de PDF/HTML | ✅ **Real y funcional** |
| Generación de reportes ISTQB (JSON + PDF con `reportlab`) | ✅ **Real y funcional** |
| **Recolección de datos del sitio** (`analyzer.py`) | ✅ **Real** — status, headers de seguridad, formularios, accesibilidad, mixed-content + guard anti-SSRF |
| **Agente autónomo con tool-calling** (`agent.py` → NVIDIA NIM) | ✅ **Real** — el LLM decide qué herramientas usar en un loop y razona como QA senior |
| **Casos de prueba** generados por IA (`TC_001`, pasos, esperado, status) | ✅ **Reales** — en JSON, PDF y dashboard |
| Bugs y casos en `/api/test-report`, PDF y HTML | ✅ **Reales** (con fallback a datos de ejemplo si no hay API key) |
| **Persistencia + historial** (Postgres) | ✅ **Real** — las sesiones sobreviven reinicios y se ven en un historial (degrada a solo-memoria sin DB) |
| Integración con JIRA, navegador real (Selenium/Playwright), screenshots | 🔴 **No implementado** (en el [roadmap](#-roadmap)) |

> 🧠 **Sin `NVIDIA_API_KEY` configurada, la app funciona igual en modo demo** (usa bugs de ejemplo), así que el despliegue nunca se rompe. Con la key activa, el análisis es real e inteligente.

---

## ✨ Características

- 🤖 **Agente autónomo (tool-calling)**: el LLM (vía NVIDIA NIM) decide qué herramientas usar en un loop —headers, formularios, accesibilidad, descubrimiento de endpoints— y razona como QA senior.
- 🧪 **Casos de prueba generados por IA**: además de bugs, produce un plan de pruebas (`TC_001`: pasos, esperado, status, severidad).
- 🗂️ **Persistencia + historial**: las sesiones se guardan en Postgres y se consultan desde un historial; los reportes sobreviven a reinicios.
- 🛡️ **Recolección real + guard anti-SSRF**: inspecciona headers de seguridad, formularios, accesibilidad y mixed-content; bloquea URLs internas (incluso en redirects y en las rutas que elige el agente).
- 🎨 **Dashboard de una sola página** (HTML/CSS/JS, sin frameworks pesados).
- ⚡ **Ejecución asíncrona**: cada test corre en un hilo en segundo plano; la UI hace *polling* de estado y logs.
- 📊 **8 áreas de testing** declaradas: UI, Lógica, Performance, Seguridad, API, Integridad de Datos, Manejo de Estado y Edge Cases.
- 📄 **Reportes ISTQB**: estructura estándar de defectos en JSON y export a **PDF** con marca Greensoft.
- 🧰 **Herramientas CLI** incluidas: monitoreo en vivo (`monitor.py`), pruebas por lote (`batch_test.py`) y verificación de salud (`check_server.py`).
- ☁️ **Listo para desplegar** en Render con un solo `render.yaml`.

---

## 🌐 Demo en vivo

### 👉 **[greensoft-testing.onrender.com](https://greensoft-testing.onrender.com/)**

[![Abrir demo](https://img.shields.io/badge/▶_Abrir_demo-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://greensoft-testing.onrender.com/)

> ℹ️ En el plan gratuito de Render el servicio "duerme" tras ~15 min de inactividad; la primera visita puede tardar 30–60 s en despertar.

---

## 🚀 Arranque rápido (local)

**Requisitos:** Python 3.10 o superior.

```bash
# 1. Clonar
git clone https://github.com/orozcolazaro/Test-Automation-Framework.git
cd Test-Automation-Framework

# 2. (Recomendado) Entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. (Opcional) Activar el análisis con IA
#    Copia .env.example a .env y pon tu NVIDIA_API_KEY.
#    Sin esto, la app corre en modo demo (bugs de ejemplo).

# 5. Ejecutar
python app.py
```

Abre **http://localhost:5000** 🟢

En Windows también puedes usar el script `run.bat`.

### Activar el análisis con IA

```bash
cp .env.example .env      # Windows: copy .env.example .env
# edita .env y pon tu key real:  NVIDIA_API_KEY=nvapi-...
```

La key se obtiene gratis en [build.nvidia.com](https://build.nvidia.com) → **API Keys** (tier gratuito: 40 req/min). El modelo por defecto es `z-ai/glm-5.1` y se puede cambiar con `NVIDIA_MODEL`. Detalles en [Análisis con IA](#-análisis-con-ia-nvidia).

---

## ☁️ Despliegue en Render

El repo incluye un `render.yaml` (Blueprint), así que el despliegue es prácticamente automático:

1. Entra a [render.com](https://render.com) e inicia sesión con GitHub.
2. **New +** → **Blueprint**.
3. Conecta este repositorio. Render detectará `render.yaml`.
4. Pulsa **Apply** y espera el primer build (~2–3 min).
5. **Para activar la IA y el historial:** en el servicio → **Environment** → añade:
   - `NVIDIA_API_KEY` (márcala como *secret*) — y opcionalmente `NVIDIA_MODEL`.
   - `DATABASE_URL` (secret) — para el historial persistente.
   Sin estas variables, el servicio corre en modo demo / solo-memoria (no se rompe).

Cada `git push` a la rama por defecto dispara un **redeploy automático**.

### ¿Por qué un solo worker?

El servidor de producción se arranca con:

```bash
gunicorn app:app --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:$PORT
```

`--workers 1` es **obligatorio**: el estado de las sesiones (`test_sessions`, `test_logs`) y los hilos de los tests viven **en memoria dentro de un único proceso**. Con varios workers, `/start-test` y `/test-status` podrían caer en procesos distintos y la sesión "desaparecería". `--threads 8` permite atender el *polling* mientras el test corre. Detalles en la [documentación técnica](docs/ARCHITECTURE.md#modelo-de-concurrencia).

---

## 🤖 Agente autónomo con IA (NVIDIA)

El corazón del framework. El flujo separa **"manos"** y **"cerebro"**:

```
analyzer.py (manos)            agent.py (cerebro agéntico)
expone herramientas   ◄──────► el LLM DECIDE qué tools usar
sobre el sitio        ──────►  en un loop y devuelve bugs +
                               casos de prueba (JSON)
```

1. **`analyzer.py`** hace fetch de la URL y extrae hechos verificables: status HTTP, **headers de seguridad** (CSP, HSTS, X-Frame-Options…), formularios, accesibilidad, mixed-content. Incluye un **guard anti-SSRF** que bloquea IPs privadas/loopback/metadata (y revalida cada redirección).
2. **`agent.py`** corre un **loop de tool-calling**: el LLM elige qué investigar usando herramientas (`get_security_headers`, `get_forms`, `get_page_meta`, `discover_endpoints`, `fetch_path`) hasta tener evidencia suficiente, y produce `{bugs, test_cases}`. Toda tool que hace fetch pasa por el guard anti-SSRF y queda **fijada al host original**.
3. **`ai_analyst.py`** es el **fallback** de una sola llamada (sin tools) si el agente falla o se topa con el rate limit; y aporta el parseo defensivo del JSON. Si no hay API key, se usan datos de ejemplo: la demo nunca se rompe.

**Cadena de resiliencia:** agente (tool-calling) → análisis simple (1 llamada) → datos de ejemplo.

**Configuración** (variables de entorno / `.env`):

| Variable | Requerida | Por defecto | Descripción |
|---|---|---|---|
| `NVIDIA_API_KEY` | Para la IA | — | Tu key de build.nvidia.com (`nvapi-...`). |
| `NVIDIA_MODEL` | No | `z-ai/glm-5.1` | Modelo a usar. Alternativas: `meta/llama-3.3-70b-instruct`, `nvidia/nemotron-3-nano-30b-a3b`. |
| `DATABASE_URL` | Para historial | — | Connection string de Postgres (Neon/Supabase). Sin esto, la app corre solo en memoria. |

> 🔒 El `.env` está en `.gitignore`: la key y el `DATABASE_URL` **nunca** se suben al repo.

---

## 🖥️ Uso desde la terminal (CLI)

Con el servidor corriendo (`python app.py`) en otra terminal:

```bash
# Verificar que el servidor responde
python check_server.py

# Monitorear una sesión en vivo
python monitor.py https://the-internet.herokuapp.com/ standard

# Ejecutar un lote de URLs y generar un reporte JSON
python batch_test.py
```

---

## 🔌 Referencia de la API

Base URL: `http://localhost:5000` (o tu dominio de Render).

| Método | Endpoint | Descripción |
|---|---|---|
| `GET`  | `/` | Sirve el dashboard (`index.html`). |
| `POST` | `/api/start-test` | Inicia una sesión. Body: `{ "target_url": "...", "mode": "quick\|standard\|deep" }`. Devuelve `{ "session_id": "..." }`. |
| `GET`  | `/api/test-status/<session_id>` | Estado y progreso de la sesión. |
| `GET`  | `/api/test-logs/<session_id>?offset=N` | Logs de la sesión desde `offset`. |
| `GET`  | `/api/test-report/<session_id>` | Reporte en JSON: `bugs`, `test_cases`, conteos y recomendación. |
| `GET`  | `/api/test-report-pdf/<session_id>` | Descarga el reporte en PDF (ISTQB, con casos de prueba). |
| `GET`  | `/api/test-report-istqb/<session_id>` | Reporte ISTQB en HTML. |
| `GET`  | `/api/history` | Historial de sesiones guardadas (si hay DB). |
| `GET`  | `/api/features` | Lista las 8 áreas de testing. |
| `POST` | `/api/cancel-test/<session_id>` | Marca la sesión como cancelada. |
| `POST` | `/api/clear-history` | Limpia todas las sesiones y logs en memoria. |

**Ejemplo:**

```bash
curl -X POST http://localhost:5000/api/start-test \
  -H "Content-Type: application/json" \
  -d '{"target_url": "https://example.com", "mode": "standard"}'
```

La especificación detallada (request/response, códigos de error) está en [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#contrato-de-la-api).

---

## 📁 Estructura del proyecto

```
Test-Automation-Framework/
├── app.py                      # Servidor Flask + API + TestRunner (orquestación)
├── analyzer.py                 # "Manos": recoge datos del sitio + guard anti-SSRF
├── agent.py                    # Agente: loop de tool-calling (el LLM decide)
├── ai_analyst.py               # Fallback single-shot + parseo/normalización
├── storage.py                  # Persistencia de sesiones en Postgres
├── istqb_report_generator.py   # Modelo de defectos en formato ISTQB
├── pdf_generator.py            # Exporta el reporte a PDF (reportlab)
├── monitor.py                  # CLI: monitoreo de una sesión en vivo
├── batch_test.py               # CLI: testing por lote de varias URLs
├── check_server.py             # CLI: verificación de salud del servidor
├── templates/
│   └── index.html              # Dashboard (UI principal)
├── static/
│   ├── css/style.css           # Estilos
│   └── js/main.js              # Lógica de cliente (polling, render)
├── test_urls.txt               # Sitios públicos de práctica para testing
├── requirements.txt            # Dependencias Python
├── .env.example                # Plantilla de configuración (copiar a .env)
├── render.yaml                 # Blueprint de despliegue en Render
├── run.bat                     # Arranque rápido en Windows
├── PROJECT_PROMPT.md           # Visión / especificación del producto
└── docs/
    └── ARCHITECTURE.md         # Documentación técnica
```

---

## 📚 Documentación técnica

La documentación técnica completa (arquitectura, modelo de concurrencia, flujo de datos, contrato de la API y puntos de extensión) está en:

➡️ **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)**

---

## 🗺️ Roadmap

- [x] **Análisis real con IA** (NVIDIA NIM) sobre datos recogidos del sitio.
- [x] Recolección real: headers de seguridad, formularios, accesibilidad, mixed-content.
- [x] Guard anti-SSRF (incluye redirects y rutas que elige el agente).
- [x] **Tool-calling agéntico**: el LLM decide qué investigar en un loop autónomo.
- [x] **Generación de casos de prueba** por IA (ISTQB) + export HTML.
- [x] **Persistencia en Postgres** + vista de historial (sobrevive reinicios).
- [ ] Navegador real (Selenium / Playwright) para sitios con JS pesado, pruebas de UI y **screenshots**.
- [ ] Pruebas activas de seguridad (SQLi, XSS) — con autorización del objetivo.
- [ ] Integración real con JIRA (creación automática de issues).
- [ ] Exportar reportes también en CSV.
- [ ] Autenticación de usuarios y multi-proyecto.

---

## 📄 Licencia

Pendiente de definir. Si quieres que sea de uso abierto, se recomienda **MIT**.

---

<p align="center">Hecho con 💚 por <a href="https://github.com/orozcolazaro">orozcolazaro</a> · GREENSOFT Testing Framework</p>
