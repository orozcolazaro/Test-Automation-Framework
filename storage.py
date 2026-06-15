"""
Persistencia de sesiones en Postgres (Neon).

Degrada con gracia: si no hay DATABASE_URL, `enabled()` es False y la app
funciona solo en memoria (la demo nunca se rompe por falta de DB).
"""

import os

import psycopg
from psycopg.types.json import Jsonb


def _url():
    # Lazy: se lee en cada uso (después de load_dotenv() en app.py).
    return os.getenv("DATABASE_URL")


def enabled() -> bool:
    return bool(_url())


def _connect():
    return psycopg.connect(_url(), connect_timeout=15)


def init_db() -> None:
    """Crea la tabla de sesiones si no existe."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id        TEXT PRIMARY KEY,
                target_url        TEXT,
                mode              TEXT,
                status            TEXT,
                total_bugs        INT,
                bugs              JSONB,
                test_cases        JSONB,
                logs              JSONB,
                bugs_by_severity  JSONB,
                created_at        TIMESTAMPTZ DEFAULT now()
            )
        """)


def save_session(session: dict, logs: list, bugs_by_severity: dict) -> None:
    """Upsert de una sesión finalizada."""
    bugs = session.get("bugs", [])
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sessions
                (session_id, target_url, mode, status, total_bugs,
                 bugs, test_cases, logs, bugs_by_severity)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id) DO UPDATE SET
                status = EXCLUDED.status,
                total_bugs = EXCLUDED.total_bugs,
                bugs = EXCLUDED.bugs,
                test_cases = EXCLUDED.test_cases,
                logs = EXCLUDED.logs,
                bugs_by_severity = EXCLUDED.bugs_by_severity
        """, (
            session["session_id"], session.get("target_url"), session.get("mode"),
            session.get("status"), len(bugs),
            Jsonb(bugs), Jsonb(session.get("test_cases", [])),
            Jsonb(logs), Jsonb(bugs_by_severity),
        ))


def get_session(session_id: str) -> dict | None:
    """Devuelve una sesión (con bugs/test_cases/logs) o None."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT session_id, target_url, mode, status, bugs, test_cases, logs
            FROM sessions WHERE session_id = %s
        """, (session_id,))
        row = cur.fetchone()
    if not row:
        return None
    return {
        "session_id": row[0], "target_url": row[1], "mode": row[2],
        "status": row[3], "bugs": row[4] or [], "test_cases": row[5] or [],
        "logs": row[6] or [],
    }


def list_sessions(limit: int = 25) -> list:
    """Lista las sesiones más recientes (resumen para el historial)."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT session_id, target_url, mode, status, total_bugs,
                   bugs_by_severity, created_at
            FROM sessions ORDER BY created_at DESC LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
    return [{
        "session_id": r[0], "target_url": r[1], "mode": r[2], "status": r[3],
        "total_bugs": r[4] or 0, "bugs_by_severity": r[5] or {},
        "created_at": r[6].isoformat() if r[6] else None,
    } for r in rows]


def clear() -> None:
    """Borra todo el historial."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM sessions")
