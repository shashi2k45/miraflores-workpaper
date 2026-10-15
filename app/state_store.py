"""User-state store for the MiraFlores workpaper scaffold.

Everything a reviewer *does* in the workpaper — notes, sign-offs,
adjustments, verifications — is workpaper state, NOT packet data. It is
kept in a separate SQLite file so the packet JSON stays untouched and the
state can be reset by simply deleting the file.

Location: app/state.db (override with the WORKPAPER_STATE_DB env var).
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get(
    "WORKPAPER_STATE_DB", Path(__file__).resolve().parent / "state.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL, line_key TEXT NOT NULL,
    author TEXT NOT NULL, role TEXT, text TEXT NOT NULL,
    blocks_filing INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS signoffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL, line_key TEXT NOT NULL,
    signer TEXT NOT NULL, role TEXT,
    status TEXT NOT NULL DEFAULT 'signed',
    line_value_at_sign REAL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL, line_key TEXT NOT NULL,
    author TEXT NOT NULL, role TEXT,
    original_value REAL, new_value REAL NOT NULL, reason TEXT NOT NULL,
    tax_effect_estimate TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL, line_key TEXT,
    extracted_value_id TEXT,
    verified_by TEXT NOT NULL, status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS view_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL, role TEXT, resource TEXT NOT NULL,
    detail TEXT, sensitive INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
"""

# Columns added after the first scaffold: (table, column, DDL type)
_MIGRATIONS = [
    ("adjustments", "tax_effect_category", "TEXT"),
]


def _migrate(conn) -> None:
    for table, column, ddl in _MIGRATIONS:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _insert(table: str, row: dict) -> dict:
    row = {**row, "created_at": _now()}
    cols = ", ".join(row.keys())
    marks = ", ".join("?" for _ in row)
    with _conn() as conn:
        cur = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})",
                           list(row.values()))
        row["id"] = cur.lastrowid
    if "blocks_filing" in row:
        row["blocks_filing"] = bool(row["blocks_filing"])
    return row


def _list(table: str, version=None, line_key=None) -> list[dict]:
    sql, args = f"SELECT * FROM {table} WHERE 1=1", []
    if version:
        sql += " AND version = ?"; args.append(version)
    if line_key:
        sql += " AND line_key = ?"; args.append(line_key)
    sql += " ORDER BY id"
    with _conn() as conn:
        rows = [dict(r) for r in conn.execute(sql, args)]
    for r in rows:
        if "blocks_filing" in r:
            r["blocks_filing"] = bool(r["blocks_filing"])
    return rows


import json as _json


def add_note(row: dict) -> dict:
    row["blocks_filing"] = 1 if row.get("blocks_filing") else 0
    return _insert("notes", row)


def list_notes(version=None, line_key=None):
    return _list("notes", version, line_key)


def add_signoff(row: dict) -> dict:
    return _insert("signoffs", row)


def list_signoffs(version=None, line_key=None):
    return _list("signoffs", version, line_key)


def add_adjustment(row: dict) -> dict:
    row = dict(row)
    row["tax_effect_estimate"] = _json.dumps(row.get("tax_effect_estimate") or {})
    out = _insert("adjustments", row)
    out["tax_effect_estimate"] = _json.loads(out["tax_effect_estimate"])
    return out


def list_adjustments(version=None, line_key=None):
    rows = _list("adjustments", version, line_key)
    for r in rows:
        try:
            r["tax_effect_estimate"] = _json.loads(r.get("tax_effect_estimate") or "{}")
        except ValueError:
            r["tax_effect_estimate"] = {}
    return rows


def add_verification(row: dict) -> dict:
    return _insert("verifications", row)


def list_verifications(version=None):
    return _list("verifications", version)


def add_view_log(row: dict) -> dict:
    row = dict(row)
    row["sensitive"] = 1 if row.get("sensitive") else 0
    out = _insert("view_log", row)
    out["sensitive"] = bool(out["sensitive"])
    return out


def list_view_log(limit: int = 200) -> list[dict]:
    with _conn() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM view_log ORDER BY id DESC LIMIT ?", (limit,))]
    for r in rows:
        r["sensitive"] = bool(r["sensitive"])
    return rows


def summary() -> dict:
    with _conn() as conn:
        return {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("notes", "signoffs", "adjustments", "verifications", "view_log")
        }
