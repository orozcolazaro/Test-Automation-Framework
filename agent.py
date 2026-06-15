"""
TestAgent — el agente autónomo con tool-calling.

El LLM decide qué herramientas usar (headers, forms, meta, endpoints, fetch)
en un loop hasta concluir. Las herramientas son "las manos" del framework y
TODAS las que hacen fetch pasan por el guard anti-SSRF y quedan fijadas al
host original (un LLM eligiendo URLs es un vector SSRF nuevo).
"""

import json
from urllib.parse import urljoin, urlparse

from analyzer import SiteAnalyzer, SSRFError, _assert_safe_url
from ai_analyst import AIAnalyst, SYSTEM_PROMPT, parse_findings

MAX_ITERATIONS = 6          # tope de vueltas del loop (cuida el rate limit 40 rpm)
COMMON_PATHS = ["/robots.txt", "/sitemap.xml", "/login", "/admin", "/api", "/.env", "/.git/HEAD"]

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_overview",
        "description": "Datos generales: status HTTP, tiempo de respuesta, https, título, servidor, redirección.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "get_security_headers",
        "description": "Cabeceras de seguridad presentes y ausentes (CSP, HSTS, X-Frame-Options, etc.).",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "get_forms",
        "description": "Formularios del sitio: método, action, número de inputs y si tienen campo password.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "get_page_meta",
        "description": "Accesibilidad/UX: viewport, lang, imágenes sin alt, links, scripts inline, mixed-content.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "discover_endpoints",
        "description": "Sondea rutas comunes (robots.txt, sitemap.xml, /login, /admin, /api, /.env, /.git) y devuelve sus códigos de estado.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "fetch_path",
        "description": "Hace GET a una ruta del MISMO host (p.ej. '/login') y devuelve status, content-type y un fragmento.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Ruta relativa, ej: /login"}},
            "required": ["path"],
        },
    }},
]


class ToolExecutor:
    """Ejecuta las tools que pide el LLM, pinneado al host original y con SSRF guard."""

    def __init__(self, target_url: str, facts: dict | None = None):
        self.target_url = target_url
        self.host = urlparse(target_url).hostname
        self.analyzer = SiteAnalyzer()
        self._facts = facts  # hechos pre-cargados por el TestRunner (evita refetch)

    def _get_facts(self) -> dict:
        if self._facts is None:
            self._facts = self.analyzer.collect(self.target_url)
        return self._facts

    def dispatch(self, name: str, args: dict) -> dict:
        try:
            handler = getattr(self, name, None)
            if handler is None:
                return {"error": f"herramienta desconocida: {name}"}
            return handler(**(args or {}))
        except SSRFError as e:
            return {"error": f"bloqueado por seguridad: {e}"}
        except Exception as e:
            return {"error": str(e)}

    # --- tools que leen de los hechos ya recogidos ---
    def get_overview(self) -> dict:
        f = self._get_facts()
        return {k: f.get(k) for k in
                ("status_code", "elapsed_ms", "is_https", "redirected", "final_url",
                 "title", "server", "content_type", "content_length_bytes")}

    def get_security_headers(self) -> dict:
        return self._get_facts().get("security_headers", {})

    def get_forms(self) -> dict:
        f = self._get_facts()
        return {"form_count": f.get("form_count", 0), "forms": f.get("forms", [])}

    def get_page_meta(self) -> dict:
        f = self._get_facts()
        return {k: f.get(k) for k in
                ("has_title", "html_lang", "has_viewport_meta", "image_count",
                 "images_without_alt", "link_count", "inline_script_count", "mixed_content_count")}

    # --- tools que hacen fetch (same-host + SSRF) ---
    def discover_endpoints(self) -> dict:
        results = {}
        for path in COMMON_PATHS:
            url = self._same_host_url(path)
            try:
                resp = self.analyzer._safe_get(url)
                results[path] = resp.status_code
            except Exception as e:
                results[path] = f"error: {type(e).__name__}"
        return {"endpoints": results}

    def fetch_path(self, path: str) -> dict:
        url = self._same_host_url(path)
        resp = self.analyzer._safe_get(url)
        text = resp.text if "text" in resp.headers.get("Content-Type", "") else ""
        return {
            "url": url,
            "status_code": resp.status_code,
            "content_type": resp.headers.get("Content-Type", ""),
            "snippet": text[:500],
        }

    def _same_host_url(self, path: str) -> str:
        url = urljoin(self.target_url, path)
        if urlparse(url).hostname != self.host:
            raise SSRFError(f"Solo se permiten rutas del host original ({self.host}).")
        _assert_safe_url(url)
        return url


class TestAgent:
    """Orquesta el loop de tool-calling con el LLM."""

    def __init__(self, analyst: AIAnalyst):
        self.analyst = analyst
        self.client = analyst.client
        self.model = analyst.model

    def run(self, target_url: str, facts: dict | None = None, log=None) -> dict:
        """Corre el agente. Devuelve {'bugs': [...], 'test_cases': [...]}."""
        executor = ToolExecutor(target_url, facts=facts)
        _log = log or (lambda *_: None)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"Audita el sitio {target_url} como QA senior. Usa las herramientas "
                "disponibles para investigar (seguridad, formularios, accesibilidad, "
                "endpoints) y cuando tengas suficiente evidencia devuelve el JSON final "
                "con 'bugs' y 'test_cases'."
            )},
        ]

        for _ in range(MAX_ITERATIONS):
            resp = self.client.chat.completions.create(
                model=self.model, messages=messages, tools=TOOL_SCHEMAS,
                temperature=0.3, max_tokens=4096,
            )
            msg = resp.choices[0].message
            if not msg.tool_calls:
                return parse_findings(msg.content or "")

            messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls})
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                _log(f"🔧 {tc.function.name}({', '.join(f'{k}={v}' for k, v in args.items())})")
                result = executor.dispatch(tc.function.name, args)
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": json.dumps(result, ensure_ascii=False)})

        # Llegamos al tope: forzamos una síntesis final SIN tools.
        _log("Límite de iteraciones alcanzado; sintetizando reporte final...")
        messages.append({"role": "user", "content":
                         "Has alcanzado el límite de exploración. Devuelve YA el JSON final "
                         "con 'bugs' y 'test_cases' basándote en lo que ya investigaste."})
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=0.3, max_tokens=4096,
        )
        return parse_findings(resp.choices[0].message.content or "")
