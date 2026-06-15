"""
SiteAnalyzer — "las manos" del framework.

Recoge datos REALES de una URL (status, headers de seguridad, formularios,
accesibilidad, mixed-content, etc.) que luego el LLM analiza como QA senior.

Incluye un guard anti-SSRF: la app es pública y hace fetch de URLs arbitrarias,
así que bloqueamos direcciones privadas/loopback/metadata de la nube.
"""

import ipaddress
import socket
import time
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

# Headers de seguridad que un QA senior espera encontrar.
SECURITY_HEADERS = [
    "Content-Security-Policy",
    "Strict-Transport-Security",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Permissions-Policy",
]

REQUEST_TIMEOUT = 10
USER_AGENT = "GREENSOFT-Testing-Framework/1.0 (+https://github.com/orozcolazaro/Test-Automation-Framework)"


class SSRFError(ValueError):
    """La URL apunta a un destino no permitido (privado/loopback/metadata)."""


def _assert_safe_url(url: str) -> None:
    """Bloquea esquemas no http(s) y destinos de red internos (anti-SSRF)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SSRFError("Solo se permiten URLs http/https.")
    host = parsed.hostname
    if not host:
        raise SSRFError("URL sin host válido.")

    # Resolver todas las IPs del host y verificar que ninguna sea interna.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise SSRFError(f"No se pudo resolver el host: {host}")

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local      # incluye 169.254.x.x (metadata cloud)
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise SSRFError(f"Destino no permitido (IP interna): {ip}")


class SiteAnalyzer:
    """Recoge hechos verificables sobre una URL objetivo."""

    def collect(self, url: str) -> dict:
        """Devuelve un dict de 'hechos' sobre el sitio. Lanza SSRFError si la URL es interna."""
        _assert_safe_url(url)

        started = time.perf_counter()
        resp = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        facts = {
            "url": url,
            "final_url": resp.url,
            "redirected": resp.url != url,
            "status_code": resp.status_code,
            "elapsed_ms": elapsed_ms,
            "content_length_bytes": len(resp.content),
            "is_https": resp.url.startswith("https://"),
            "security_headers": self._security_headers(resp.headers),
            "server": resp.headers.get("Server", ""),
            "content_type": resp.headers.get("Content-Type", ""),
        }

        # Solo parseamos HTML si el content-type lo es.
        if "html" in facts["content_type"].lower():
            facts.update(self._parse_html(resp.text, resp.url))
        else:
            facts["html_parsed"] = False

        return facts

    def _security_headers(self, headers) -> dict:
        present, missing = {}, []
        for h in SECURITY_HEADERS:
            if h in headers:
                present[h] = headers[h][:120]  # recortado para el prompt
            else:
                missing.append(h)
        return {"present": present, "missing": missing}

    def _parse_html(self, html: str, base_url: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        on_https = base_url.startswith("https://")

        # Formularios
        forms = []
        for form in soup.find_all("form"):
            inputs = form.find_all("input")
            forms.append({
                "method": (form.get("method") or "get").lower(),
                "action": form.get("action") or "",
                "input_count": len(inputs),
                "has_password": any(i.get("type") == "password" for i in inputs),
            })

        # Imágenes sin alt (accesibilidad)
        images = soup.find_all("img")
        images_without_alt = sum(1 for img in images if not (img.get("alt") or "").strip())

        # Mixed content: recursos http:// en una página https
        mixed = 0
        if on_https:
            for tag, attr in (("img", "src"), ("script", "src"), ("link", "href")):
                for el in soup.find_all(tag):
                    src = el.get(attr) or ""
                    if src.startswith("http://"):
                        mixed += 1

        title_tag = soup.find("title")
        viewport = soup.find("meta", attrs={"name": "viewport"})

        return {
            "html_parsed": True,
            "title": (title_tag.get_text(strip=True) if title_tag else ""),
            "has_title": bool(title_tag and title_tag.get_text(strip=True)),
            "html_lang": (soup.html.get("lang") if soup.html else "") or "",
            "has_viewport_meta": viewport is not None,
            "form_count": len(forms),
            "forms": forms[:10],
            "link_count": len(soup.find_all("a")),
            "image_count": len(images),
            "images_without_alt": images_without_alt,
            "inline_script_count": sum(1 for s in soup.find_all("script") if not s.get("src")),
            "mixed_content_count": mixed,
        }
