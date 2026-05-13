#!/usr/bin/env python3
"""
Batch Testing - Testea múltiples URLs secuencialmente
"""

import requests
import time
import json
import sys
from datetime import datetime

API_URL = "http://localhost:5000"

URLS = [
    ("https://the-internet.herokuapp.com/", "quick"),
    ("https://demoqa.com/", "quick"),
    ("https://www.demoblaze.com/", "standard"),
    ("https://automationpractice.com/", "standard"),
    ("https://practice.automationbro.com/", "quick"),
]

class BatchTester:
    def __init__(self):
        self.results = []
    
    def test_url(self, target_url, mode):
        """Testea una URL"""
        print(f"\n{'='*70}")
        print(f"Testeando: {target_url}")
        print(f"Modo: {mode}")
        print(f"{'='*70}")
        
        try:
            # Iniciar test
            response = requests.post(
                f"{API_URL}/api/start-test",
                json={"target_url": target_url, "mode": mode},
                timeout=5
            )
            
            if response.status_code != 200:
                print(f"✗ Error iniciando: {response.json()}")
                return None
            
            session_id = response.json()['session_id']
            print(f"Session: {session_id}")
            
            # Monitorear progreso
            start_time = time.time()
            while True:
                status = requests.get(
                    f"{API_URL}/api/test-status/{session_id}",
                    timeout=5
                ).json()
                
                print(f"\r[{status['progress']:3d}%] {status['current_phase']:<40}", 
                      end="", flush=True)
                
                if status['status'] != 'running':
                    print("\n")
                    break
                
                time.sleep(1)
            
            duration = time.time() - start_time
            
            # Obtener reporte
            report = requests.get(
                f"{API_URL}/api/test-report/{session_id}",
                timeout=5
            ).json()
            
            result = {
                "url": target_url[:40] + "..." if len(target_url) > 40 else target_url,
                "modo": mode,
                "total": report['total_bugs'],
                "critical": report['bugs_by_severity'].get('CRITICAL', 0),
                "high": report['bugs_by_severity'].get('HIGH', 0),
                "medium": report['bugs_by_severity'].get('MEDIUM', 0),
                "tiempo": f"{duration:.1f}s",
                "status": "✓" if report['total_bugs'] < 3 else "⚠️"
            }
            
            self.results.append(result)
            
            # Mostrar bugs
            if report['bugs']:
                print("\n🐛 Bugs encontrados:")
                for bug in report['bugs'][:3]:
                    print(f"  [{bug['type'].upper()}] {bug['title']}")
                if len(report['bugs']) > 3:
                    print(f"  ... y {len(report['bugs']) - 3} más")
            
            return result
        
        except Exception as e:
            print(f"✗ Error: {e}")
            return None
    
    def run_batch(self):
        """Ejecuta todos los tests"""
        print("\n" + "="*70)
        print("🚀 BATCH TESTING - MÚLTIPLES URLs")
        print("="*70)
        
        for url, mode in URLS:
            self.test_url(url, mode)
            time.sleep(2)
        
        self.show_summary()
    
    def show_summary(self):
        """Muestra resumen final"""
        if not self.results:
            print("Sin resultados")
            return
        
        print("\n" + "="*70)
        print("📊 RESUMEN EJECUTIVO")
        print("="*70)
        
        # Tabla manual
        headers = ["URL", "Modo", "Total", "Critical", "High", "Med", "Tiempo", "Status"]
        print(f"\n{headers[0]:<45} {headers[1]:<10} {headers[2]:<6} {headers[3]:<8} {headers[4]:<6} {headers[5]:<4} {headers[6]:<8} {headers[7]:<6}")
        print("-" * 95)
        
        for r in self.results:
            print(f"{r['url']:<45} {r['modo']:<10} {r['total']:<6} {r['critical']:<8} {r['high']:<6} {r['medium']:<4} {r['tiempo']:<8} {r['status']:<6}")
        
        # Estadísticas
        total_bugs = sum(r['total'] for r in self.results)
        total_critical = sum(r['critical'] for r in self.results)
        avg_time = sum(float(r['tiempo'].replace('s','')) for r in self.results) / len(self.results)
        worst_url = max(self.results, key=lambda x: x['total'])
        
        print("\n" + "="*70)
        print(f"📈 Estadísticas:")
        print(f"  Total URLs testeadas: {len(self.results)}")
        print(f"  Total Bugs: {total_bugs}")
        print(f"  Bugs Críticos: {total_critical}")
        print(f"  Tiempo Promedio: {avg_time:.1f}s")
        print(f"  URL más problemática: {worst_url['url']}")
        print("="*70)
        
        # Guardar reporte
        self._save_report()
    
    def _save_report(self):
        """Guarda reporte JSON"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "results": self.results,
            "summary": {
                "total_urls": len(self.results),
                "total_bugs": sum(r['total'] for r in self.results),
                "total_critical": sum(r['critical'] for r in self.results)
            }
        }
        
        filename = f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✓ Reporte guardado: {filename}")


def main():
    tester = BatchTester()
    tester.run_batch()


if __name__ == "__main__":
    main()
