#!/usr/bin/env python3
"""
Verifica estado del servidor Flask
"""

import requests
import time

API_URL = "http://localhost:5000"

print("🔍 Verificando servidor Flask...\n")

for i in range(5):
    try:
        response = requests.get(API_URL, timeout=2)
        print(f"✓ Servidor activo!")
        print(f"  URL: {API_URL}")
        print(f"  Status: {response.status_code}")
        
        # Probar API
        features = requests.get(f"{API_URL}/api/features", timeout=2)
        if features.status_code == 200:
            print(f"✓ API funcionando")
            print(f"  Features: {len(features.json())} funcionalidades")
        break
    
    except Exception as e:
        print(f"✗ Intento {i+1}/5: No conecta")
        print(f"  Error: {str(e)[:60]}")
        if i < 4:
            print("  Esperando 2s...\n")
            time.sleep(2)

print("\n⚠️  Si el servidor no responde:")
print("  1. Verifica que app.py esté ejecutándose")
print("  2. Intenta: python app.py")
print("  3. Luego: python batch_test.py")
