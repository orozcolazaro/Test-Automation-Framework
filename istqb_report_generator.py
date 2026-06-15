"""
Generador de Reportes de Bugs - Formato ISTQB Foundation Level
"""

from datetime import datetime
from typing import List, Dict

class ISTQBBugReport:
    """Formato estándar de reporte de bugs según ISTQB"""
    
    def __init__(self):
        self.bugs = []
    
    def add_bug(self, bug_data: Dict):
        """Agrega un bug en formato ISTQB"""
        bug = {
            "bug_id": bug_data.get("id", "BUG_001"),
            "title": bug_data.get("title", ""),
            "summary": bug_data.get("description", ""),
            "environment": {
                "browser": "N/A — análisis vía HTTP (sin navegador)",
                "os": "Servidor del framework (Linux/local)",
                "test_data": "URL de producción real",
                "network": "Internet"
            },
            "severity": bug_data.get("severity", "MEDIUM"),
            "priority": self._map_priority(bug_data.get("severity")),
            "type": bug_data.get("type", "Functional"),
            "status": "NEW",
            "steps_to_reproduce": bug_data.get("steps") or [
                "1. Navegar a la URL objetivo",
                "2. Inspeccionar el aspecto reportado",
                "3. Observar la diferencia con el resultado esperado"
            ],
            "expected_result": bug_data.get("expected", "Debe funcionar correctamente"),
            "actual_result": bug_data.get("actual", "Error encontrado"),
            "attachments": [
                {"type": "screenshot", "name": "Pendiente — requiere navegador (roadmap)"}
            ],
            "services_affected": bug_data.get("services", []),
            "root_cause": "",
            "impact": bug_data.get("impact", "Usuario no puede completar acción"),
            "workaround": "No disponible",
            "reported_by": "GREENSOFT Testing Framework",
            "reported_date": datetime.now().isoformat(),
            "assigned_to": "",
            "fixed_by": "",
            "fixed_date": "",
            "resolution": "",
            "comments": []
        }
        self.bugs.append(bug)
        return bug
    
    def _map_priority(self, severity: str) -> str:
        """Mapea severidad a prioridad ISTQB"""
        mapping = {
            "CRITICAL": "P1 - INMEDIATA",
            "HIGH": "P2 - URGENTE",
            "MEDIUM": "P3 - NORMAL",
            "LOW": "P4 - BAJA"
        }
        return mapping.get(severity, "P3 - NORMAL")
    
    def generate_html_report(self, session_id: str, target_url: str, mode: str, logs: list = None) -> str:
        """Genera reporte HTML en formato ISTQB"""
        logs = logs or []
        
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Reporte ISTQB - {target_url}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'DejaVu Sans', Arial, sans-serif; 
            background: #0a1428;
            color: #fff;
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{
            background: linear-gradient(135deg, #00ff99 0%, #00ffaa 100%);
            color: #0a1428;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 32px; margin-bottom: 10px; }}
        .header p {{ font-size: 14px; margin: 5px 0; }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: #1a2a40;
            border: 3px solid #00ff99;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .summary-card .number {{ font-size: 32px; font-weight: 900; color: #00ff99; }}
        .summary-card .label {{ font-size: 12px; color: #888; margin-top: 10px; }}
        
        .bug-section {{
            background: #1a2a40;
            border: 2px solid #00ff99;
            margin-bottom: 25px;
            border-radius: 10px;
            overflow: hidden;
        }}
        .bug-header {{
            background: #00ff99;
            color: #0a1428;
            padding: 20px;
            font-weight: 900;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .bug-id {{ font-size: 18px; }}
        .bug-severity {{
            padding: 8px 16px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 12px;
        }}
        .severity-critical {{ background: #ff1744; color: white; }}
        .severity-high {{ background: #ff6d00; color: white; }}
        .severity-medium {{ background: #ffc400; color: #000; }}
        .severity-low {{ background: #00c853; color: white; }}
        
        .bug-content {{ padding: 25px; }}
        .bug-field {{
            margin-bottom: 20px;
            display: grid;
            grid-template-columns: 200px 1fr;
            gap: 20px;
        }}
        .bug-field-label {{
            font-weight: 900;
            color: #00ff99;
            font-size: 14px;
        }}
        .bug-field-value {{
            padding: 12px;
            background: rgba(0, 255, 153, 0.1);
            border-left: 3px solid #00ff99;
            border-radius: 5px;
            color: #ccc;
        }}
        
        .steps {{
            background: rgba(0, 0, 0, 0.3);
            padding: 15px;
            border-left: 4px solid #ff6d00;
            border-radius: 5px;
            font-family: monospace;
            font-size: 13px;
            line-height: 1.8;
        }}
        
        .services {{
            background: rgba(255, 107, 0, 0.1);
            padding: 15px;
            border-left: 4px solid #ff6d00;
            border-radius: 5px;
        }}
        .service-item {{
            display: inline-block;
            background: #ff6d00;
            color: white;
            padding: 6px 12px;
            margin: 5px 5px 5px 0;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }}
        
        .attachments {{
            background: rgba(0, 255, 153, 0.1);
            padding: 15px;
            border-left: 4px solid #00ff99;
            border-radius: 5px;
        }}
        .attachment-item {{
            padding: 10px;
            background: rgba(0, 0, 0, 0.3);
            margin: 8px 0;
            border-radius: 5px;
            font-size: 13px;
        }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            border-top: 2px solid #00ff99;
            margin-top: 30px;
            color: #888;
        }}
        
        @media print {{
            body {{ background: white; color: black; }}
            .header {{ color: #0a1428; }}
            .bug-section {{ border: 1px solid #ccc; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 REPORTE DE DEFECTOS - ISTQB Foundation Level</h1>
            <p><strong>Proyecto:</strong> GREENSOFT Testing Framework</p>
            <p><strong>URL Testeada:</strong> {target_url}</p>
            <p><strong>Sesión:</strong> {session_id}</p>
            <p><strong>Modo:</strong> {mode.upper()}</p>
            <p><strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="number">{len(self.bugs)}</div>
                <div class="label">TOTAL BUGS</div>
            </div>
            <div class="summary-card">
                <div class="number">{sum(1 for b in self.bugs if b['severity'] == 'CRITICAL')}</div>
                <div class="label">CRÍTICOS</div>
            </div>
            <div class="summary-card">
                <div class="number">{sum(1 for b in self.bugs if b['severity'] == 'HIGH')}</div>
                <div class="label">ALTOS</div>
            </div>
            <div class="summary-card">
                <div class="number">{sum(1 for b in self.bugs if b['severity'] in ['MEDIUM', 'LOW'])}</div>
                <div class="label">MEDIOS/BAJOS</div>
            </div>
        </div>
"""
        
        # Agregar cada bug
        for i, bug in enumerate(self.bugs, 1):
            severity_class = f"severity-{bug['severity'].lower()}"
            
            html += f"""
        <div class="bug-section">
            <div class="bug-header">
                <span class="bug-id">{bug['bug_id']} - {bug['title']}</span>
                <span class="bug-severity {severity_class}">{bug['severity']}</span>
            </div>
            
            <div class="bug-content">
                <div class="bug-field">
                    <div class="bug-field-label">ID BUG:</div>
                    <div class="bug-field-value">{bug['bug_id']}</div>
                </div>
                
                <div class="bug-field">
                    <div class="bug-field-label">PRIORIDAD:</div>
                    <div class="bug-field-value">{bug['priority']}</div>
                </div>
                
                <div class="bug-field">
                    <div class="bug-field-label">TIPO:</div>
                    <div class="bug-field-value">{bug['type']}</div>
                </div>
                
                <div class="bug-field">
                    <div class="bug-field-label">RESUMEN:</div>
                    <div class="bug-field-value">{bug['summary']}</div>
                </div>
                
                <div class="bug-field">
                    <div class="bug-field-label">RESULTADO ESPERADO:</div>
                    <div class="bug-field-value">{bug['expected_result']}</div>
                </div>
                
                <div class="bug-field">
                    <div class="bug-field-label">RESULTADO ACTUAL:</div>
                    <div class="bug-field-value">{bug['actual_result']}</div>
                </div>
                
                <div class="bug-field">
                    <div class="bug-field-label">IMPACTO:</div>
                    <div class="bug-field-value">{bug['impact']}</div>
                </div>
                
                <div class="bug-field">
                    <div class="bug-field-label">PASOS PARA REPRODUCIR:</div>
                    <div class="steps">
{chr(10).join(bug['steps_to_reproduce'])}
                    </div>
                </div>
                
                <div class="bug-field">
                    <div class="bug-field-label">SERVICIOS AFECTADOS:</div>
                    <div class="services">
{chr(10).join(f'<span class="service-item">{s}</span>' for s in (bug.get('services_affected', []) or []))}
                    </div>
                </div>
                
                <div class="bug-field">
                    <div class="bug-field-label">ENTORNO:</div>
                    <div class="bug-field-value">
                        <strong>SO:</strong> {bug['environment']['os']}<br>
                        <strong>Navegador:</strong> {bug['environment']['browser']}<br>
                        <strong>Datos:</strong> {bug['environment']['test_data']}
                    </div>
                </div>
                
                <div class="bug-field">
                    <div class="bug-field-label">ADJUNTOS:</div>
                    <div class="attachments">
{chr(10).join(f'<div class="attachment-item">📎 {a["name"]} ({a["type"]})</div>' for a in bug.get('attachments', []))}
                    </div>
                </div>
                
                <div class="bug-field">
                    <div class="bug-field-label">REPORTADO POR:</div>
                    <div class="bug-field-value">{bug['reported_by']}</div>
                </div>
                
                <div class="bug-field">
                    <div class="bug-field-label">FECHA REPORTE:</div>
                    <div class="bug-field-value">{bug['reported_date']}</div>
                </div>
            </div>
        </div>
"""
        
        # Logs de ejecución (reales)
        if logs:
            import html as _html
            log_text = _html.escape("\n".join(logs))
            html += f"""
        <h2 style="color:#00ff99;margin:30px 0 15px;">📝 LOGS DE EJECUCIÓN</h2>
        <pre style="background:#0a1428;border:1px solid #00ff99;border-radius:8px;
                    padding:18px;overflow-x:auto;white-space:pre-wrap;word-break:break-word;
                    color:#c8e6d4;font-size:12px;line-height:1.6;">{log_text}</pre>
"""

        html += """
        <div class="footer">
            <p>Este reporte ha sido generado automáticamente por GREENSOFT Testing Framework</p>
            <p>Formato: ISTQB Foundation Level - Test Summary Report</p>
        </div>
    </div>
</body>
</html>
"""
        return html
