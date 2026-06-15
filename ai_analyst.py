"""
AIAnalyst — análisis de respaldo en UNA sola llamada (sin tool-calling).

El modo principal es el agente con tool-calling (ver agent.py). Este módulo
queda como FALLBACK: si el agente falla o se topa con el rate limit, se hace
un único análisis sobre los hechos ya recogidos.

También expone utilidades compartidas (parseo defensivo y normalizadores)
que reutiliza el agente.
"""

import json
import os
import re

from openai import OpenAI

BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "z-ai/glm-5.1"

# Esquema de salida que pedimos al LLM (tanto en single-shot como en el agente).
OUTPUT_CONTRACT = """Devuelve EXCLUSIVAMENTE un objeto JSON (sin texto extra, sin markdown) así:
{
  "bugs": [
    {
      "severity": "HIGH",
      "title": "Título corto y claro",
      "description": "Qué encontraste y por qué es un problema.",
      "expected": "Comportamiento esperado.",
      "actual": "Comportamiento observado según los hechos.",
      "impact": "Impacto en usuario o negocio.",
      "steps": ["1. ...", "2. ...", "3. ..."],
      "services": ["Frontend"]
    }
  ],
  "test_cases": [
    {
      "id": "TC_001",
      "description": "Qué valida el caso de prueba.",
      "steps": ["1. ...", "2. ...", "3. ..."],
      "expected": "Resultado esperado.",
      "actual": "Resultado observado.",
      "status": "PASS",
      "severity": "MEDIUM"
    }
  ]
}
Clasifica la severidad como CRITICAL, HIGH, MEDIUM o LOW. El status de un caso
de prueba es PASS, FAIL o BLOCKED. Si no hay defectos, "bugs" es []. Genera
al menos 3 casos de prueba relevantes para lo que observaste."""

SYSTEM_PROMPT = (
    "Eres un QA Senior con más de 10 años de experiencia en testing web, seguridad "
    "y accesibilidad. Analizas HECHOS verificados sobre un sitio (recogidos "
    "automáticamente) e identificas defectos REALES basándote SOLO en esos hechos. "
    "No inventes nada que los datos no respalden.\n\n" + OUTPUT_CONTRACT
)


class AIAnalyst:
    def __init__(self):
        self.api_key = os.getenv("NVIDIA_API_KEY")
        self.model = os.getenv("NVIDIA_MODEL", DEFAULT_MODEL)
        self._client = OpenAI(base_url=BASE_URL, api_key=self.api_key) if self.api_key else None

    def available(self) -> bool:
        return self._client is not None

    @property
    def client(self):
        return self._client

    def analyze(self, facts: dict) -> dict:
        """Análisis single-shot. Devuelve {'bugs': [...], 'test_cases': [...]}."""
        if not self._client:
            raise RuntimeError("NVIDIA_API_KEY no configurada.")

        user_prompt = (
            "Analiza estos hechos del sitio y devuelve el JSON pedido.\n\n"
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
        return parse_findings(resp.choices[0].message.content or "")


# ----------------------------- utilidades compartidas -----------------------------

_VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
_VALID_STATUSES = {"PASS", "FAIL", "BLOCKED"}


def parse_findings(text: str) -> dict:
    """Extrae y normaliza {'bugs': [...], 'test_cases': [...]} del texto del LLM."""
    obj = _extract_json_object(text)
    bugs = [normalize_bug(b) for b in obj.get("bugs", []) if isinstance(b, dict)]
    cases = [normalize_test_case(t, i + 1)
             for i, t in enumerate(obj.get("test_cases", [])) if isinstance(t, dict)]
    return {"bugs": bugs, "test_cases": cases}


def _extract_json_object(text: str) -> dict:
    """Extrae el primer objeto JSON del texto, tolerando fences y ruido/razonamiento."""
    # 1) Intento directo.
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict):
            return data
        if isinstance(data, list):  # por si devuelve solo el array de bugs
            return {"bugs": data, "test_cases": []}
    except json.JSONDecodeError:
        pass

    # 2) Bloque ```json ... ```
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    # 3) Del primer '{' al último '}'.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError("No se pudo extraer un objeto JSON de la respuesta del LLM.")


def normalize_bug(bug: dict) -> dict:
    sev = str(bug.get("severity", "MEDIUM")).upper()
    if sev not in _VALID_SEVERITIES:
        sev = "MEDIUM"
    services = bug.get("services") or []
    if isinstance(services, str):
        services = [services]
    steps = bug.get("steps") or []
    if isinstance(steps, str):
        steps = [steps]
    return {
        "severity": sev,
        "type": sev.lower(),  # compat con el formato del reporte/UI existente
        "title": str(bug.get("title", "Sin título")),
        "description": str(bug.get("description", "")),
        "expected": str(bug.get("expected", "")),
        "actual": str(bug.get("actual", "")),
        "impact": str(bug.get("impact", "")),
        "steps": [str(s) for s in steps],
        "services": [str(s) for s in services],
    }


def normalize_test_case(tc: dict, index: int) -> dict:
    sev = str(tc.get("severity", "MEDIUM")).upper()
    if sev not in _VALID_SEVERITIES:
        sev = "MEDIUM"
    status = str(tc.get("status", "PASS")).upper()
    if status not in _VALID_STATUSES:
        status = "PASS"
    steps = tc.get("steps") or []
    if isinstance(steps, str):
        steps = [steps]
    return {
        "id": str(tc.get("id") or f"TC_{index:03d}"),
        "description": str(tc.get("description", "")),
        "steps": [str(s) for s in steps],
        "expected": str(tc.get("expected", "")),
        "actual": str(tc.get("actual", "")),
        "status": status,
        "severity": sev,
    }
