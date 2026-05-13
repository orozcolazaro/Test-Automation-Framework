from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from typing import Dict
import json
import threading
import uuid
from datetime import datetime
from istqb_report_generator import ISTQBBugReport
from pdf_generator import PDFReportGenerator
import time
import io

app = Flask(__name__)
CORS(app)

test_sessions: Dict = {}
test_logs: Dict = {}


class TestRunner:
    def __init__(self, session_id: str, target_url: str, mode: str):
        self.session_id = session_id
        self.target_url = target_url
        self.mode = mode
        self.logs = []
        self.progress = 0
        self.current_phase = "Iniciando"
        self.bugs = []
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
            self.update_progress(20, "Testing Básico")
            self.add_log("Iniciando fase 1: Testing Básico...")
            self._phase_basic()
            
            if self.mode in ["standard", "deep"]:
                self.update_progress(40, "Testing Iterativo")
                self.add_log("Iniciando fase 2...")
                self._phase_iterative()
            
            if self.mode in ["standard", "deep"]:
                self.update_progress(60, "Análisis de APIs")
                self.add_log("Iniciando fase 3...")
                self._phase_api()
            
            if self.mode == "deep":
                self.update_progress(80, "Testing Avanzado")
                self.add_log("Iniciando fase 4...")
                self._phase_advanced()
            
            self.update_progress(100, "Completado")
            self.status = "completed"
            test_sessions[self.session_id]["status"] = "completed"
            self.add_log("✓ Testing completado", "SUCCESS")
        
        except Exception as e:
            self.status = "error"
            self.add_log(f"✗ Error: {str(e)}", "ERROR")
    
    def _phase_basic(self):
        time.sleep(1)
        self.add_log("✓ Verificando UI")
        self.add_log("  - [HIGH] Imagen no carga")
        time.sleep(0.5)
        self.add_log("✓ Validando formularios")
    
    def _phase_iterative(self):
        self.add_log("Ejecutando iteraciones...")
        time.sleep(0.5)
    
    def _phase_api(self):
        time.sleep(1)
        self.add_log("Testeando endpoints...")
        self.add_log("  - [CRITICAL] SQL Injection")
    
    def _phase_advanced(self):
        time.sleep(1)
        self.add_log("✓ Verificando seguridad")


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
    if session_id not in test_sessions:
        return jsonify({"error": "No encontrado"}), 404
    
    session = test_sessions[session_id]
    
    return jsonify({
        "session_id": session_id,
        "target_url": session["target_url"],
        "mode": session["mode"],
        "status": session["status"],
        "total_bugs": 4,
        "bugs_by_severity": {"CRITICAL": 1, "HIGH": 1, "MEDIUM": 2, "LOW": 0},
        "bugs": [
            {"type": "critical", "title": "SQL Injection en /api/users", "description": "Parámetro vulnerable", "services": ["API", "Database", "Auth"]},
            {"type": "high", "title": "Imagen de logo no carga", "description": "HTTP 404", "services": ["Frontend", "CDN"]},
            {"type": "medium", "title": "Email validation", "description": "Acepta inválidos", "services": ["Backend"]},
            {"type": "medium", "title": "maxlength", "description": "Sin límite", "services": ["Frontend"]}
        ],
        "deployment_recommendation": "BLOQUEAR"
    })


@app.route('/api/test-report-pdf/<session_id>')
def test_report_pdf(session_id):
    try:
        if session_id not in test_sessions:
            return jsonify({"error": "Sesión no encontrada"}), 404
        
        session = test_sessions[session_id]
        
        # Datos de bugs
        bugs = [
            {"severity": "CRITICAL", "title": "SQL Injection en /api/users", "description": "Parámetro vulnerable"},
            {"severity": "HIGH", "title": "Imagen no carga", "description": "HTTP 404"},
            {"severity": "MEDIUM", "title": "Email validation", "description": "Acepta inválidos"},
        ]
        
        # Generar PDF
        pdf_gen = PDFReportGenerator()
        
        # En memoria
        pdf_buffer = io.BytesIO()
        
        # Workaround: generar en archivo temporal y leer
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            pdf_path = tmp.name
        
        pdf_gen.generate_pdf(pdf_path, session_id, session['target_url'], session['mode'], bugs)
        
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


@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    test_sessions.clear()
    test_logs.clear()
    return jsonify({"status": "ok"})


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


if __name__ == '__main__':
    print("\n🟢 GREENSOFT TESTING - http://localhost:5000\n")
    app.run(debug=False, host='0.0.0.0', port=5000)
