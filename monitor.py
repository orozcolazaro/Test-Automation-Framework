#!/usr/bin/env python3
"""
Testing Framework - Log Monitor
Monitorea los logs en tiempo real de una sesión de testing
"""

import requests
import time
import json
import sys
from datetime import datetime

API_URL = "http://localhost:5000"

class TestMonitor:
    def __init__(self, target_url, mode="standard"):
        self.target_url = target_url
        self.mode = mode
        self.session_id = None
        self.last_log_index = 0
    
    def start_test(self):
        """Inicia el testing"""
        print("\n" + "="*70)
        print("🚀 INICIANDO TEST")
        print("="*70)
        print(f"URL: {self.target_url}")
        print(f"Modo: {self.mode}")
        print("="*70 + "\n")
        
        try:
            response = requests.post(
                f"{API_URL}/api/start-test",
                json={"target_url": self.target_url, "mode": self.mode},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                self.session_id = data.get('session_id')
                print(f"✓ Session ID: {self.session_id}\n")
                return True
            else:
                print(f"✗ Error: {response.json().get('error')}")
                return False
        
        except Exception as e:
            print(f"✗ Error conectando: {e}")
            return False
    
    def monitor_logs(self):
        """Monitorea logs en tiempo real"""
        if not self.session_id:
            return
        
        while True:
            try:
                # Obtener status
                status_resp = requests.get(
                    f"{API_URL}/api/test-status/{self.session_id}",
                    timeout=5
                )
                
                if status_resp.status_code == 200:
                    status = status_resp.json()
                    
                    # Mostrar progreso
                    print(f"\r[{status['progress']:3d}%] {status['current_phase']:<40}", end="", flush=True)
                    
                    # Obtener nuevos logs
                    logs_resp = requests.get(
                        f"{API_URL}/api/test-logs/{self.session_id}?offset={self.last_log_index}",
                        timeout=5
                    )
                    
                    if logs_resp.status_code == 200:
                        logs_data = logs_resp.json()
                        new_logs = logs_data['logs'][self.last_log_index:]
                        
                        if new_logs:
                            print()  # Nueva línea para los logs
                            for log in new_logs:
                                self._print_log(log)
                            self.last_log_index = logs_data['total']
                    
                    # ¿Terminó?
                    if status['status'] != 'running':
                        print("\n")
                        self.show_results()
                        break
                    
                    time.sleep(0.5)
                else:
                    print("\n✗ Error obteniendo status")
                    break
            
            except KeyboardInterrupt:
                print("\n\n✗ Testing cancelado por usuario")
                break
            except Exception as e:
                print(f"\n✗ Error: {e}")
                time.sleep(1)
    
    def _print_log(self, log_entry):
        """Imprime log con colores"""
        if "ERROR" in log_entry or "✗" in log_entry:
            print(f"  🔴 {log_entry}")
        elif "SUCCESS" in log_entry or "✓" in log_entry:
            print(f"  🟢 {log_entry}")
        elif "CRITICAL" in log_entry:
            print(f"  🔴 {log_entry}")
        elif "HIGH" in log_entry or "[HIGH]" in log_entry:
            print(f"  🟠 {log_entry}")
        elif "MEDIUM" in log_entry or "[MEDIUM]" in log_entry:
            print(f"  🟡 {log_entry}")
        else:
            print(f"  ⚪ {log_entry}")
    
    def show_results(self):
        """Muestra resultados finales"""
        try:
            response = requests.get(
                f"{API_URL}/api/test-report/{self.session_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                report = response.json()
                
                print("\n" + "="*70)
                print("📊 RESULTADOS")
                print("="*70)
                print(f"Total Bugs: {report['total_bugs']}")
                print(f"  Critical: {report['bugs_by_severity'].get('CRITICAL', 0)}")
                print(f"  High:     {report['bugs_by_severity'].get('HIGH', 0)}")
                print(f"  Medium:   {report['bugs_by_severity'].get('MEDIUM', 0)}")
                print(f"  Low:      {report['bugs_by_severity'].get('LOW', 0)}")
                
                print(f"\nDeployment: {report['deployment_recommendation']}")
                
                if report['bugs']:
                    print("\n🐛 Bugs encontrados:")
                    for bug in report['bugs']:
                        severity_icon = {
                            'critical': '🔴',
                            'high': '🟠',
                            'medium': '🟡',
                            'low': '🟢'
                        }.get(bug['type'], '⚪')
                        
                        print(f"  {severity_icon} [{bug['type'].upper()}] {bug['title']}")
                        print(f"     └─ {bug['description']}")
                
                print("\n" + "="*70)
        
        except Exception as e:
            print(f"Error obteniendo resultados: {e}")


def main():
    if len(sys.argv) < 2:
        print("Uso: python monitor.py <url> [modo]")
        print("Ejemplo: python monitor.py https://the-internet.herokuapp.com/ standard")
        print("\nModos: quick, standard, deep")
        sys.exit(1)
    
    target_url = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "standard"
    
    monitor = TestMonitor(target_url, mode)
    
    if monitor.start_test():
        monitor.monitor_logs()
    else:
        print("✗ No se pudo iniciar el testing")


if __name__ == "__main__":
    main()
