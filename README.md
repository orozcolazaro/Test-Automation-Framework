# 🟢 GREENSOFT Testing Framework

> Plataforma web para orquestar, monitorear en tiempo real y reportar pruebas automatizadas sobre aplicaciones web. Construida con **Flask** y una interfaz de una sola página, con generación de reportes de defectos en **formato ISTQB** (JSON y PDF).

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0+-000000?logo=flask&logoColor=white)
![Deploy](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render&logoColor=white)
![Status](https://img.shields.io/badge/status-MVP%20%2F%20demo-yellow)

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

## ⚠️ Estado actual (importante)

Esto es un **MVP / demo funcional del flujo end-to-end**. Para ser transparente sobre qué hace hoy:

| Componente | Estado |
|---|---|
| Interfaz web, API REST, monitoreo en vivo, descarga de PDF | ✅ **Real y funcional** |
| Generación de reportes ISTQB (JSON + PDF con `reportlab`) | ✅ **Real y funcional** |
| Modos `quick` / `standard` / `deep` y sistema de fases | ✅ **Real** (orquestación) |
| **Motor de pruebas** (`TestRunner._phase_*`) | 🟡 **Simulado** — usa `time.sleep()` y logs/bugs de ejemplo |
| Bugs devueltos por `/api/test-report` | 🟡 **Datos de ejemplo** (hardcoded) |
| Integración con JIRA, Selenium, etc. | 🔴 **No implementado** (visión documentada en `PROJECT_PROMPT.md`) |

👉 La arquitectura está lista para reemplazar la simulación por pruebas reales. Mira [cómo extenderlo](docs/ARCHITECTURE.md#puntos-de-extensión) en la documentación técnica.

---

## ✨ Características

- 🎨 **Dashboard de una sola página** (HTML/CSS/JS, sin frameworks pesados).
- ⚡ **Ejecución asíncrona**: cada test corre en un hilo en segundo plano; la UI hace *polling* de estado y logs.
- 📊 **8 áreas de testing** declaradas: UI, Lógica, Performance, Seguridad, API, Integridad de Datos, Manejo de Estado y Edge Cases.
- 📄 **Reportes ISTQB**: estructura estándar de defectos en JSON y export a **PDF** con marca Greensoft.
- 🧰 **Herramientas CLI** incluidas: monitoreo en vivo (`monitor.py`), pruebas por lote (`batch_test.py`) y verificación de salud (`check_server.py`).
- ☁️ **Listo para desplegar** en Render con un solo `render.yaml`.

---

## 🌐 Demo en vivo

> Tras desplegar en Render, coloca aquí tu URL pública:

```
https://greensoft-testing.onrender.com
```

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

# 4. Ejecutar
python app.py
```

Abre **http://localhost:5000** 🟢

En Windows también puedes usar el script `run.bat`.

---

## ☁️ Despliegue en Render

El repo incluye un `render.yaml` (Blueprint), así que el despliegue es prácticamente automático:

1. Entra a [render.com](https://render.com) e inicia sesión con GitHub.
2. **New +** → **Blueprint**.
3. Conecta este repositorio. Render detectará `render.yaml`.
4. Pulsa **Apply** y espera el primer build (~2–3 min).

Cada `git push` a la rama por defecto dispara un **redeploy automático**.

### ¿Por qué un solo worker?

El servidor de producción se arranca con:

```bash
gunicorn app:app --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:$PORT
```

`--workers 1` es **obligatorio**: el estado de las sesiones (`test_sessions`, `test_logs`) y los hilos de los tests viven **en memoria dentro de un único proceso**. Con varios workers, `/start-test` y `/test-status` podrían caer en procesos distintos y la sesión "desaparecería". `--threads 8` permite atender el *polling* mientras el test corre. Detalles en la [documentación técnica](docs/ARCHITECTURE.md#modelo-de-concurrencia).

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
| `GET`  | `/api/test-report/<session_id>` | Reporte de defectos en JSON. |
| `GET`  | `/api/test-report-pdf/<session_id>` | Descarga el reporte en PDF (ISTQB). |
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

- [ ] Reemplazar el motor simulado por pruebas reales (Selenium / Playwright / `requests` + `beautifulsoup4`).
- [ ] Detección real de vulnerabilidades (SQLi, XSS, headers de seguridad).
- [ ] Persistir sesiones y reportes (SQLite / Redis) para que sobrevivan a reinicios.
- [ ] Integración real con JIRA (creación automática de issues).
- [ ] Exportar reportes también en HTML y CSV.
- [ ] Autenticación de usuarios y multi-proyecto.

---

## 📄 Licencia

Pendiente de definir. Si quieres que sea de uso abierto, se recomienda **MIT**.

---

<p align="center">Hecho con 💚 por <a href="https://github.com/orozcolazaro">orozcolazaro</a> · GREENSOFT Testing Framework</p>
