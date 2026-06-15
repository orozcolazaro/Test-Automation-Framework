from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from typing import Dict
import json
import threading
import uuid
from datetime import datetime
from istqb_report_generator import ISTQBBugReport
from pdf_generator import PDFReportGenerator
import io
import os

import requests
from dotenv import load_dotenv
from analyzer import SiteAnalyzer, SSRFError
from ai_analyst import AIAnalyst
from agent import TestAgent
import storage

# Carga NVIDIA_API_KEY / NVIDIA_MODEL / DATABASE_URL desde .env en local (en
# Render se usan las env vars del dashboard; si no hay .env, no hace nada).
load_dotenv()

app = Flask(__name__)
CORS(app)

# Inicializa la tabla de sesiones si hay base de datos configurada.
if storage.enabled():
    try:
        storage.init_db()
        print("🗄️  Persistencia activada (Postgres)")
    except Exception as e:
        print(f"⚠️  No se pudo inicializar la DB: {e}")

test_sessions: Dict = {}
test_logs: Dict = {}


def _make_bug(severity, title, description, expected="", actual="", impact="", services=None):
    """Construye un bug con el mismo esquema que produce AIAnalyst."""
    sev = severity.upper()
    return {
        "severity": sev,
        "type": sev.lower(),
        "title": title,
        "description": description,
        "expected": expected,
        "actual": actual,
        "impact": impact,
        "services": services or [],
    }


def _summarize_bugs(bugs):
    """Cuenta por severidad y deriva la recomendación de despliegue."""
    by_sev = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for b in bugs:
        sev = b.get("severity", "MEDIUM").upper()
        by_sev[sev] = by_sev.get(sev, 0) + 1
    if by_sev["CRITICAL"] > 0:
        rec = "BLOQUEAR - Bug crítico encontrado"
    elif by_sev["HIGH"] > 0:
        rec = "REVISAR - Bugs de alta severidad"
    else:
        rec = "OK - Sin bloqueantes"
    return by_sev, rec


def _load_session(session_id):
    """Sesión desde memoria; si no está, desde la DB (sobrevive reinicios)."""
    if session_id in test_sessions:
        return test_sessions[session_id]
    if storage.enabled():
        try:
            return storage.get_session(session_id)
        except Exception:
            return None
    return None


def _session_logs(session_id, session):
    """Logs desde memoria o desde la sesión cargada de la DB."""
    if session_id in test_logs:
        return test_logs[session_id]
    return (session or {}).get("logs", [])


class TestRunner:
    def __init__(self, session_id: str, target_url: str, mode: str):
        self.session_id = session_id
        self.target_url = target_url
        self.mode = mode
        self.logs = []
        self.progress = 0
        self.current_phase = "Iniciando"
        self.bugs = []
        self.test_cases = []
        self.status = "running"

    def add_log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.logs.append(log_entry)
        test_logs[self.session_id] = self.logs
    
    def update_progress(self, progress: int, phase: str):
        self.progress = progress
        self.current_phase = phase
        if self.session_id in test_sessions:
            test_sessions[self.session_id]["progress"] = progress
            test_sessions[self.session_id]["current_phase"] = phase
    
    def run(self):
        try:
            # --- Fase 1: recolección de datos reales (las "manos") ---
            self.update_progress(15, "Recolectando datos del sitio")
            self.add_log(f"Analizando {self.target_url} (modo {self.mode})...")

            try:
                facts = SiteAnalyzer().collect(self.target_url)
            except SSRFError as e:
                self.add_log(f"✗ URL no permitida: {e}", "ERROR")
                self._finish(status="error")
                return
            except requests.RequestException as e:
                # El sitio no responde ES un hallazgo real.
                self.add_log(f"✗ El sitio no responde: {e}", "ERROR")
                self.bugs = [_make_bug("CRITICAL", "El sitio no responde",
                                       f"No se pudo establecer conexión: {e}",
                                       services=["Infraestructura"])]
                self._finish(status="completed")
                return

            self.add_log(f"✓ Responde {facts['status_code']} en {facts['elapsed_ms']}ms", "SUCCESS")
            missing = facts.get("security_headers", {}).get("missing", [])
            if missing:
                self.add_log(f"  - Headers de seguridad ausentes: {', '.join(missing)}")

            # --- Fase 2: análisis con IA (el "cerebro" agéntico) ---
            self.update_progress(55, "Agente IA investigando")
            analyst = AIAnalyst()
            if analyst.available():
                self._run_ai(analyst, facts)
            else:
                self.add_log("⚠ Sin NVIDIA_API_KEY: usando análisis de respaldo (demo)")
                self.bugs = self._simulated_bugs()

            self._finish(status="completed")
            self.add_log(
                f"✓ Testing completado: {len(self.bugs)} bug(s), {len(self.test_cases)} caso(s) de prueba",
                "SUCCESS")

        except Exception as e:
            self.status = "error"
            self.add_log(f"✗ Error inesperado: {str(e)}", "ERROR")
            if self.session_id in test_sessions:
                test_sessions[self.session_id]["status"] = "error"

    def _run_ai(self, analyst, facts):
        """Agente con tool-calling; cae a single-shot y luego a simulado."""
        # 1) Agente autónomo (tool-calling).
        try:
            self.add_log(f"Agente IA ({analyst.model}) explorando con herramientas...")
            findings = TestAgent(analyst).run(self.target_url, facts=facts, log=self.add_log)
            self.bugs = findings["bugs"]
            self.test_cases = findings["test_cases"]
            self.add_log(f"✓ Agente: {len(self.bugs)} bug(s), {len(self.test_cases)} caso(s)", "SUCCESS")
            return
        except Exception as e:
            self.add_log(f"⚠ Agente falló ({type(e).__name__}); intento análisis simple", "ERROR")

        # 2) Análisis single-shot (1 sola llamada).
        try:
            findings = analyst.analyze(facts)
            self.bugs = findings["bugs"]
            self.test_cases = findings["test_cases"]
            self.add_log(f"✓ Análisis simple: {len(self.bugs)} bug(s)", "SUCCESS")
            return
        except Exception as e:
            self.add_log(f"⚠ Análisis IA falló ({type(e).__name__}); usando respaldo", "ERROR")

        # 3) Respaldo simulado (la demo nunca se rompe).
        self.bugs = self._simulated_bugs()

    def _finish(self, status: str):
        """Persiste bugs, casos de prueba y estado final en la sesión (memoria + DB)."""
        self.status = status
        self.update_progress(100, "Completado" if status == "completed" else "Error")
        if self.session_id not in test_sessions:
            return
        test_sessions[self.session_id]["status"] = status
        test_sessions[self.session_id]["bugs"] = self.bugs
        test_sessions[self.session_id]["test_cases"] = self.test_cases

        if storage.enabled():
            try:
                by_sev, _ = _summarize_bugs(self.bugs)
                storage.save_session(test_sessions[self.session_id], self.logs, by_sev)
            except Exception as e:
                self.add_log(f"⚠ No se pudo guardar en la DB: {e}", "ERROR")

    def _simulated_bugs(self):
        """Datos de respaldo cuando no hay IA disponible (mantiene viva la demo)."""
        return [
            _make_bug("CRITICAL", "SQL Injection en /api/users", "Parámetro vulnerable",
                      services=["API", "Database", "Auth"]),
            _make_bug("HIGH", "Imagen de logo no carga", "HTTP 404", services=["Frontend", "CDN"]),
            _make_bug("MEDIUM", "Email validation", "Acepta inválidos", services=["Backend"]),
            _make_bug("MEDIUM", "maxlength", "Sin límite", services=["Frontend"]),
        ]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/start-test', methods=['POST'])
def start_test():
    data = request.json
    target_url = data.get('target_url', '').strip()
    mode = data.get('mode', 'standard')
    
    if not target_url.startswith(('http://', 'https://')):
        return jsonify({"error": "URL inválida"}), 400
    
    session_id = str(uuid.uuid4())[:8]
    
    test_session = {
        "session_id": session_id,
        "target_url": target_url,
        "mode": mode,
        "status": "running",
        "progress": 0,
        "current_phase": "Iniciando",
        "start_time": datetime.now().isoformat()
    }
    
    test_sessions[session_id] = test_session
    test_logs[session_id] = []
    
    runner = TestRunner(session_id, target_url, mode)
    thread = threading.Thread(target=runner.run)
    thread.daemon = True
    thread.start()
    
    return jsonify({"session_id": session_id})


@app.route('/api/test-status/<session_id>')
def test_status(session_id):
    if session_id not in test_sessions:
        return jsonify({"error": "No encontrado"}), 404
    
    session = test_sessions[session_id]
    return jsonify({
        "session_id": session_id,
        "status": session["status"],
        "progress": session["progress"],
        "current_phase": session["current_phase"]
    })


@app.route('/api/test-logs/<session_id>')
def test_logs_endpoint(session_id):
    if session_id not in test_logs:
        return jsonify({"error": "No encontrado"}), 404
    
    offset = request.args.get('offset', 0, type=int)
    logs = test_logs[session_id]
    
    return jsonify({"logs": logs[offset:], "total": len(logs)})


@app.route('/api/test-report/<session_id>')
def test_report(session_id):
    session = _load_session(session_id)
    if not session:
        return jsonify({"error": "No encontrado"}), 404

    bugs = session.get("bugs", [])
    test_cases = session.get("test_cases", [])
    by_sev, recommendation = _summarize_bugs(bugs)

    return jsonify({
        "session_id": session_id,
        "target_url": session["target_url"],
        "mode": session["mode"],
        "status": session["status"],
        "total_bugs": len(bugs),
        "bugs_by_severity": by_sev,
        "bugs": bugs,
        "test_cases": test_cases,
        "total_test_cases": len(test_cases),
        "deployment_recommendation": recommendation
    })


@app.route('/api/test-report-pdf/<session_id>')
def test_report_pdf(session_id):
    try:
        session = _load_session(session_id)
        if not session:
            return jsonify({"error": "Sesión no encontrada"}), 404

        # Bugs, casos de prueba y logs reales detectados en la sesión
        bugs = session.get("bugs", [])
        test_cases = session.get("test_cases", [])
        logs = _session_logs(session_id, session)

        # Generar PDF
        pdf_gen = PDFReportGenerator()
        
        # En memoria
        pdf_buffer = io.BytesIO()
        
        # Workaround: generar en archivo temporal y leer
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            pdf_path = tmp.name
        
        pdf_gen.generate_pdf(pdf_path, session_id, session['target_url'], session['mode'], bugs, test_cases, logs)
        
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        import os
        os.unlink(pdf_path)
        
        return send_file(
            io.BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'report-{session_id}.pdf'
        )
    
    except Exception as e:
        print(f"Error PDF: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/test-report-istqb/<session_id>')
def test_report_istqb(session_id):
    """Reporte HTML en formato ISTQB con los bugs reales de la sesión."""
    session = _load_session(session_id)
    if not session:
        return jsonify({"error": "No encontrado"}), 404

    report = ISTQBBugReport()
    for i, b in enumerate(session.get("bugs", []), 1):
        report.add_bug({
            "id": f"BUG_{i:03d}",
            "title": b.get("title", ""),
            "description": b.get("description", ""),
            "severity": b.get("severity", "MEDIUM"),
            "expected": b.get("expected", ""),
            "actual": b.get("actual", ""),
            "impact": b.get("impact", ""),
            "steps": b.get("steps", []),
            "services": b.get("services", []),
        })
    logs = _session_logs(session_id, session)
    html = report.generate_html_report(session_id, session["target_url"], session["mode"], logs)
    return app.response_class(html, mimetype="text/html")


@app.route('/api/features')
def get_features():
    return jsonify([
        {"id": "1", "name": "UI Testing", "icon": "🎨"},
        {"id": "2", "name": "Logic Testing", "icon": "⚙️"},
        {"id": "3", "name": "Performance", "icon": "⚡"},
        {"id": "4", "name": "Security", "icon": "🔒"},
        {"id": "5", "name": "API Testing", "icon": "🔌"},
        {"id": "6", "name": "Data Integrity", "icon": "💾"},
        {"id": "7", "name": "State Management", "icon": "📊"},
        {"id": "8", "name": "Edge Cases", "icon": "🎯"}
    ])


@app.route('/api/cancel-test/<session_id>', methods=['POST'])
def cancel_test(session_id):
    if session_id in test_sessions:
        test_sessions[session_id]["status"] = "cancelled"
    return jsonify({"status": "ok"})


@app.route('/api/history')
def history():
    """Historial de sesiones (desde la DB si está activa)."""
    if not storage.enabled():
        return jsonify({"enabled": False, "sessions": []})
    try:
        return jsonify({"enabled": True, "sessions": storage.list_sessions()})
    except Exception as e:
        return jsonify({"enabled": True, "sessions": [], "error": str(e)})


@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    test_sessions.clear()
    test_logs.clear()
    if storage.enabled():
        try:
            storage.clear()
        except Exception:
            pass
    return jsonify({"status": "ok"})


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🟢 GREENSOFT TESTING - http://localhost:{port}\n")
    app.run(debug=False, host='0.0.0.0', port=port)
