"""
AIAnalyst — "el cerebro" del framework.

Toma los hechos recogidos por SiteAnalyzer y le pide a un LLM de NVIDIA
(compatible con OpenAI) que actúe como QA senior y devuelva una lista de
bugs en JSON. El parseo es defensivo: si el modelo envuelve el JSON en
texto/razonamiento, igual lo extraemos; si falla, el caller hace fallback.
"""

import json
import os
import re

from openai import OpenAI

BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "z-ai/glm-5.1"

SYSTEM_PROMPT = """Eres un QA Senior con más de 10 años de experiencia en testing web,
seguridad y accesibilidad. Recibes HECHOS verificados sobre un sitio web (recogidos
automáticamente) y debes identificar defectos REALES basándote SOLO en esos hechos.

No inventes bugs que los datos no respalden. Clasifica cada defecto por severidad:
- CRITICAL: riesgo de seguridad grave o sitio caído.
- HIGH: falla funcional importante o seguridad relevante (p.ej. falta HSTS en login).
- MEDIUM: problema de accesibilidad, performance o buenas prácticas.
- LOW: detalle menor.

Devuelve EXCLUSIVAMENTE un array JSON (sin texto adicional, sin markdown) con esta forma:
[
  {
    "severity": "HIGH",
    "title": "Título corto y claro",
    "description": "Qué encontraste y por qué es un problema.",
    "expected": "Comportamiento esperado.",
    "actual": "Comportamiento observado según los hechos.",
    "impact": "Impacto en usuario o negocio.",
    "services": ["Frontend"]
  }
]
Si no hay defectos, devuelve []."""


class AIAnalyst:
    def __init__(self):
        self.api_key = os.getenv("NVIDIA_API_KEY")
        self.model = os.getenv("NVIDIA_MODEL", DEFAULT_MODEL)
        self._client = OpenAI(base_url=BASE_URL, api_key=self.api_key) if self.api_key else None

    def available(self) -> bool:
        """True si hay API key configurada."""
        return self._client is not None

    def analyze(self, facts: dict) -> list:
        """Devuelve una lista de bugs (dicts). Lanza si el LLM o el parseo fallan."""
        if not self._client:
            raise RuntimeError("NVIDIA_API_KEY no configurada.")

        user_prompt = (
            "Analiza estos hechos del sitio y reporta los defectos en el JSON pedido.\n\n"
            f"```json\n{json.dumps(facts, ensure_ascii=False, indent=2)}\n```"
        )

        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )

        content = resp.choices[0].message.content or ""
        bugs = _extract_json_array(content)
        return [_normalize_bug(b) for b in bugs if isinstance(b, dict)]


def _extract_json_array(text: str) -> list:
    """Extrae el primer array JSON del texto, tolerando ```json fences y ruido."""
    # 1) Intento directo.
    try:
        data = json.loads(text.strip())
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # 2) Buscar dentro de un bloque ```...```
    fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    # 3) Primer '[' hasta el último ']' del texto.
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError("No se pudo extraer un array JSON de la respuesta del LLM.")


_VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


def _normalize_bug(bug: dict) -> dict:
    sev = str(bug.get("severity", "MEDIUM")).upper()
    if sev not in _VALID_SEVERITIES:
        sev = "MEDIUM"
    services = bug.get("services") or []
    if isinstance(services, str):
        services = [services]
    return {
        "severity": sev,
        "type": sev.lower(),  # compat con el formato del reporte JSON existente
        "title": str(bug.get("title", "Sin título")),
        "description": str(bug.get("description", "")),
        "expected": str(bug.get("expected", "")),
        "actual": str(bug.get("actual", "")),
        "impact": str(bug.get("impact", "")),
        "services": [str(s) for s in services],
    }
