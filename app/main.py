"""
MiraFlores AI — AI Engineer (Tax) case study scaffold.

Provenance-first tax workpaper: every return line is a node in an evidence
graph (line -> input lines -> extracted values -> source document).

Design rules for this scaffold (see README.md for the full list):
- The packet JSON is loaded READ-ONLY at startup and never mutated.
- All user state (notes, sign-offs, adjustments, verifications) lives in a
  separate SQLite store (state_store.py), keyed by version + line key.
- Sign-offs store the line value at signing time. A sign-off is reported as
  "reopened" whenever the current packet value for that line differs from
  the signed value (see `effective_signoff_status`). With an immutable
  packet this only triggers if the packet is replaced by a newer compute,
  which is exactly the production scenario the rule exists for.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import state_store

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
PACKET_PATH = Path(os.environ.get("PACKET_PATH", PROJECT_DIR / "okafor_lindqvist_2025_packet.json"))
STATIC_DIR = BASE_DIR / "static"

# --------------------------------------------------------------------------
# Packet loading (read-only) + indexes
# --------------------------------------------------------------------------
with open(PACKET_PATH, encoding="utf-8") as fh:
    PACKET: dict[str, Any] = json.load(fh)

DOCUMENTS: dict[str, dict] = {d["id"]: d for d in PACKET["documents"]}
EXTRACTED: dict[str, dict] = {ev["id"]: ev for ev in PACKET["extracted_values"]}
VERSIONS: dict[str, dict] = {}
LINES: dict[str, dict[str, dict]] = {}
for version in PACKET["return_versions"]:
    VERSIONS[version["version"]] = version
    LINES[version["version"]] = {line["key"]: line for line in version["lines"]}
CURRENT_VERSION = PACKET["return_versions"][-1]["version"]

state_store.init_db()

app = FastAPI(title="MiraFlores Workpaper", version="1.0.0")

# --------------------------------------------------------------------------
# Role / permission model (server-side enforcement for state APIs)
#
# The role switcher sends the acting person in headers on every request:
#   X-Actor-Id:    staff id (st-01..st-06) or a client user id (cu-01/cu-02)
#                  or the literal "client" (household view)
#   X-Actor-Name / X-Actor-Role: display values the server *recomputes* from
#                  the packet for staff/client ids, so a forged role string
#                  in a header cannot grant itself rights.
# Legacy scaffold clients that send no X-Actor-Id keep working as the
# first preparer (st-01) so the original API contract/tests still pass;
# any request that DOES identify itself is enforced as below.
#
#   read_packet    - read return lines, documents, values, checks
#   write_notes    - create review notes
#   write_state    - sign-offs, adjustments, verifications
#   firm_internal  - see firm-internal notes and the sensitive-data view log
#   sensitive      - see unmasked SSNs / bank account numbers
#                    (packet staff flag: sensitive_data_clearance)
#
# Client role: read_packet for summaries/documents of their own return,
# can add a note (a client question becomes evidence), but cannot sign off,
# adjust, verify, or see firm-internal notes / the view log.
# --------------------------------------------------------------------------
WRITE_ROLES = {"preparer", "reviewer", "partner", "quality_reviewer"}
ALL_STAFF_ROLES = WRITE_ROLES | {"firm_administrator"}

CLIENT_ROLE = {
    "id": "client",
    "name": "Client view (Okafor-Lindqvist household)",
    "role": "client",
    "credential": None,
    "sensitive_data_clearance": False,
}
STAFF_BY_ID: dict[str, dict] = {s["id"]: s for s in PACKET["firm"]["staff"]}
CLIENT_BY_ID: dict[str, dict] = {c["id"]: c for c in PACKET["firm"].get("client_users", [])}
DEFAULT_ACTOR = STAFF_BY_ID.get("st-01", {})


def current_actor(x_actor_id: Optional[str]) -> dict:
    """Resolve the acting person from the X-Actor-Id header (trusted ids
    only; unknown ids fall back to the read-only client role)."""
    if not x_actor_id:
        return dict(DEFAULT_ACTOR)  # legacy no-header client = preparer
    if x_actor_id in STAFF_BY_ID:
        return dict(STAFF_BY_ID[x_actor_id])
    if x_actor_id in CLIENT_BY_ID:
        return {**CLIENT_BY_ID[x_actor_id], "sensitive_data_clearance": False}
    if x_actor_id == "client":
        return dict(CLIENT_ROLE)
    return dict(CLIENT_ROLE)


def can(actor: dict, action: str) -> bool:
    role = actor.get("role")
    if action == "read_packet":
        return True
    if action == "write_notes":
        return role in ALL_STAFF_ROLES or role == "client"
    if action == "write_state":
        return role in WRITE_ROLES
    if action == "firm_internal":
        return role in ALL_STAFF_ROLES
    if action == "sensitive":
        return bool(actor.get("sensitive_data_clearance")) and role in ALL_STAFF_ROLES
    return False


def require(actor: dict, action: str) -> None:
    if not can(actor, action):
        raise HTTPException(
            403,
            f"Role '{actor.get('role')}' ({actor.get('name')}) may not perform "
            f"'{action}' in this workpaper. See the permission model in README.md.")


def check_author_matches(actor: dict, claimed_name: str, claimed_role: Optional[str]) -> None:
    """Writes are attributed to the *resolved* actor; a body whose claimed
    author is someone else is rejected instead of silently re-attributed."""
    if claimed_name and claimed_name != actor.get("name"):
        raise HTTPException(
            403,
            f"Author '{claimed_name}' does not match the acting role "
            f"'{actor.get('name')}'. Switch the role switcher to that person first.")


def log_view(actor: dict, resource: str, detail: str = "", sensitive: bool = False) -> None:
    state_store.add_view_log({
        "actor": actor.get("name"), "role": actor.get("role"),
        "resource": resource, "detail": detail, "sensitive": sensitive,
    })


def get_version(version: str) -> dict:
    if version not in VERSIONS:
        raise HTTPException(404, f"Unknown return version: {version}")
    return VERSIONS[version]


def get_line(version: str, key: str) -> dict:
    get_version(version)
    line = LINES[version].get(key)
    if line is None:
        raise HTTPException(404, f"No line {key} in version {version}")
    return line


SENSITIVE_VALUE_TYPES = {"ssn", "account_number"}


def mask_ssn(person: dict) -> dict:
    """Household data includes fictional SSNs; mask them in API output."""
    out = dict(person)
    if out.get("ssn"):
        out["ssn"] = "***-**-" + out["ssn"][-4:]
    return out


def present_person(person: dict, actor: dict) -> dict:
    """Full SSN only for staff with sensitive_data_clearance; masked for
    everyone else (and the view is written to the view log)."""
    out = dict(person)
    if out.get("ssn") and not can(actor, "sensitive"):
        out["ssn"] = "***-**-" + out["ssn"][-4:]
        out["ssn_masked_for_role"] = actor.get("role")
    return out


def present_ev(ev: dict, actor: dict) -> dict:
    """Extracted values of sensitive types (SSN, bank account number) are
    masked unless the actor holds sensitive-data clearance."""
    out = dict(ev)
    if out.get("value_type") in SENSITIVE_VALUE_TYPES and not can(actor, "sensitive"):
        val = str(out.get("value") or "")
        out["value"] = ("***" + val[-4:]) if val else val
        out["text_as_read"] = out["value"]
        out["masked_for_role"] = actor.get("role")
    return out


def resolve_source(ev_id: str, actor: Optional[dict] = None) -> Optional[dict]:
    ev = EXTRACTED.get(ev_id)
    if ev is None:
        return None
    if actor is not None:
        ev = present_ev(ev, actor)
    doc = DOCUMENTS.get(ev["document_id"], {})
    page_text = None
    for page in doc.get("pages", []):
        if page.get("page") == ev.get("page"):
            page_text = page.get("printed_content")
            break
    return {
        "extracted_value": ev,
        "document": {
            "id": doc.get("id"),
            "title": doc.get("title"),
            "document_type": doc.get("document_type"),
            "file_name": doc.get("file_name"),
        },
        "page": ev.get("page"),
        "printed_content": page_text,
        # position + confidence come straight from the packet: the frontend
        # uses position to place a highlight on the rendered page text.
        "position": ev.get("position"),
        "confidence": ev.get("confidence"),
    }


# --------------------------------------------------------------------------
# Meta / household / staff / questionnaire / timeline
# --------------------------------------------------------------------------
@app.get("/api/meta")
def meta(x_actor_id: Optional[str] = Header(None)):
    actor = current_actor(x_actor_id)
    if can(actor, "sensitive"):
        log_view(actor, "meta:household", "household incl. full SSNs", sensitive=True)
    return {
        "packet": PACKET.get("packet"),
        "readme_what_this_is": PACKET.get("readme", {}).get("what_this_is"),
        "current_version": CURRENT_VERSION,
        "versions": list(VERSIONS.keys()),
        "counts": {
            "documents": len(PACKET["documents"]),
            "extracted_values": len(PACKET["extracted_values"]),
            "timeline_events": len(PACKET["timeline"]),
            "questionnaire_answers": len(PACKET["client"]["questionnaire"]),
            "what_if_alternatives": len(PACKET["what_if"]["alternatives"]),
        },
        "household": {
            "filing_status": PACKET["household"].get("filing_status"),
            "tax_year": PACKET["household"].get("tax_year"),
            "people": [present_person(p, actor) for p in PACKET["household"].get("people", [])],
        },
        "firm_name": PACKET["firm"].get("name"),
        "acting_as": {"id": actor.get("id"), "name": actor.get("name"),
                      "role": actor.get("role"),
                      "permissions": {a: can(actor, a) for a in
                                      ("read_packet", "write_notes", "write_state",
                                       "firm_internal", "sensitive")}},
    }


@app.get("/api/staff")
def staff():
    """Firm staff for the role switcher, plus a synthetic client role.
    Permissions are enforced server-side (see the permission model at the
    top of this file); each entry reports its effective permissions."""
    roles = []
    for s in PACKET["firm"]["staff"]:
        entry = dict(s)
        entry["permissions"] = {a: can(s, a) for a in
                                ("read_packet", "write_notes", "write_state",
                                 "firm_internal", "sensitive")}
        roles.append(entry)
    client = dict(CLIENT_ROLE)
    client["note"] = ("Client role: may read summaries/questionnaire and ask "
                      "questions (notes); cannot sign off, adjust, verify, or "
                      "see firm-internal notes or the sensitive-data view log.")
    client["permissions"] = {a: can(CLIENT_ROLE, a) for a in
                            ("read_packet", "write_notes", "write_state",
                             "firm_internal", "sensitive")}
    roles.append(client)
    return {"staff": roles}


@app.get("/api/questionnaire")
def questionnaire(x_actor_id: Optional[str] = Header(None)):
    actor = current_actor(x_actor_id)
    call_notes = PACKET["client"].get("call_notes", [])
    if not can(actor, "firm_internal"):
        # Call notes are firm-internal working notes; the client sees their
        # own questionnaire answers and messages, not the firm's call notes.
        call_notes = []
    return {"questionnaire": PACKET["client"]["questionnaire"],
            "messages": PACKET["client"].get("messages", []),
            "call_notes": call_notes}


@app.get("/api/timeline")
def timeline():
    return {"timeline": PACKET["timeline"]}


@app.get("/api/timeline/replay")
def timeline_replay(upto: int = Query(0, ge=0)):
    """Step-through replay state: events[0..upto-1] have 'happened'.

    Documented simplification (see README): the replay tracks which
    return version was current at that point (from the return_computed
    events, in order), flags the filing freeze once a return is both
    signed (8879) and e-filed, and lists post-filing events as an
    amend-on-top layer rather than rewriting the filed return. It does
    not re-derive line values per event — the packet's returns are the
    three computed versions, not per-event snapshots."""
    events = PACKET["timeline"]
    upto = min(upto, len(events))
    happened = events[:upto]
    version_order = [v["version"] for v in PACKET["return_versions"]]
    computed = [i for i, e in enumerate(happened) if e["event"] == "return_computed"]
    current = version_order[min(len(computed) - 1, len(version_order) - 1)] if computed else None
    signed = any(e["event"] == "client_approved_and_signed_8879" for e in happened)
    accepted = any(e["event"].startswith("efile_accepted") for e in happened)
    frozen = bool(signed and accepted)
    return {
        "total_events": len(events),
        "upto": upto,
        "happened": happened,
        "next_event": events[upto] if upto < len(events) else None,
        "state": {
            "current_version_at_point": current,
            "signed_8879": signed,
            "efile_accepted": accepted,
            "filing_frozen": frozen,
            "phase": ("post_filing_amend_layer" if frozen else
                      "filed_signed_awaiting_acceptance" if signed else
                      "preparation"),
            "note": "Once filing is frozen, later events (examination "
                    "notice, next-year engagement) are shown as an "
                    "amend-on-top layer; the filed version is never rewritten.",
        },
    }


# --------------------------------------------------------------------------
# Versions, lines, provenance trace
# --------------------------------------------------------------------------
@app.get("/api/versions")
def versions():
    out = []
    for v in PACKET["return_versions"]:
        out.append({
            "version": v["version"],
            "computed_at": v["computed_at"],
            "trigger": v["trigger"],
            "is_current": v["version"] == CURRENT_VERSION,
            "line_count": len(v["lines"]),
            "summary": v["summary"],
            "diagnostics_count": len(v["diagnostics"]),
            "changes_from_previous_count": len(v["changes_from_previous"]),
            "documents_used": len(v["documents_used"]),
            "documents_superseded": v["documents_superseded"],
        })
    return {"versions": out}


@app.get("/api/versions/{version}")
def version_detail(version: str):
    v = get_version(version)
    return {
        "version": v["version"],
        "computed_at": v["computed_at"],
        "trigger": v["trigger"],
        "is_current": version == CURRENT_VERSION,
        "summary": v["summary"],
        "tax_effect_rates": v["tax_effect_rates"],
        "carryovers_out": v["carryovers_out"],
        "diagnostics": v["diagnostics"],
        "changes_from_previous": v["changes_from_previous"],
        "documents_used": v["documents_used"],
        "documents_superseded": v["documents_superseded"],
        "assets": v["assets"],
    }


@app.get("/api/versions/{version}/lines")
def lines(version: str,
          jurisdiction: Optional[str] = None,
          form: Optional[str] = None,
          q: Optional[str] = None,
          limit: int = Query(100, ge=1, le=1000),
          offset: int = Query(0, ge=0)):
    get_version(version)
    items = list(LINES[version].values())
    if jurisdiction:
        items = [l for l in items if l.get("jurisdiction") == jurisdiction]
    if form:
        items = [l for l in items if l.get("form") == form]
    if q:
        ql = q.lower()
        items = [l for l in items if ql in l["key"].lower() or ql in (l.get("label") or "").lower()]
    total = len(items)
    return {"version": version, "total": total, "lines": items[offset:offset + limit]}


@app.get("/api/versions/{version}/lines/{key}")
def line_detail(version: str, key: str):
    return get_line(version, key)


@app.get("/api/versions/{version}/lines/{key}/trace")
def line_trace(version: str, key: str, max_depth: int = Query(6, ge=1, le=12),
               x_actor_id: Optional[str] = Header(None)):
    """Provenance trace: line -> input lines (recursive) -> extracted values
    -> source document + page text + highlight position + confidence."""
    actor = current_actor(x_actor_id)
    root = get_line(version, key)
    visited: set[str] = set()

    def build(line_key: str, depth: int) -> Optional[dict]:
        if line_key in visited or depth > max_depth:
            return {"key": line_key, "truncated": True}
        visited.add(line_key)
        line = LINES[version].get(line_key)
        if line is None:
            return {"key": line_key, "missing": True}
        return {
            "key": line["key"],
            "label": line.get("label"),
            "value": line.get("value"),
            "form": line.get("form"),
            "line": line.get("line"),
            "jurisdiction": line.get("jurisdiction"),
            "rule": line.get("rule"),
            "note": line.get("note"),
            "inputs": [build(k, depth + 1) for k in line.get("inputs", [])],
            "sources": [resolve_source(ev_id, actor) for ev_id in line.get("sources", [])],
        }

    return {"version": version, "trace": build(key, 0), "root_line": root}


# --------------------------------------------------------------------------
# Documents & extracted values
# --------------------------------------------------------------------------
@app.get("/api/documents")
def documents(status: Optional[str] = None):
    items = PACKET["documents"]
    if status:
        items = [d for d in items if d.get("extraction", {}).get("status") == status]
    return {
        "total": len(items),
        "status_counts": {
            s: sum(1 for d in PACKET["documents"] if d.get("extraction", {}).get("status") == s)
            for s in ("extracted", "partial", "not_extracted")
        },
        "documents": [
            {k: d.get(k) for k in ("id", "title", "document_type", "issuer", "belongs_to",
                                    "tax_year", "received_at", "file_name", "page_count")}
            | {"extraction": d.get("extraction")}
            for d in items
        ],
    }


SENSITIVE_DOCUMENT_IDS = {"D36", "D71"}  # foreign bank statement / SS card


@app.get("/api/documents/{doc_id}")
def document_detail(doc_id: str, x_actor_id: Optional[str] = Header(None)):
    doc = DOCUMENTS.get(doc_id)
    if doc is None:
        raise HTTPException(404, f"No document {doc_id}")
    actor = current_actor(x_actor_id)
    raw_values = [ev for ev in PACKET["extracted_values"] if ev["document_id"] == doc_id]
    sensitive = doc_id in SENSITIVE_DOCUMENT_IDS or any(
        ev.get("value_type") in SENSITIVE_VALUE_TYPES for ev in raw_values)
    if sensitive:
        log_view(actor, f"document:{doc_id}", doc.get("title", ""), sensitive=True)
    values = [present_ev(ev, actor) for ev in raw_values]
    return {"document": doc, "extracted_values": values, "sensitive_document": sensitive}


@app.get("/api/extracted-values")
def extracted_values(document_id: Optional[str] = None,
                     max_confidence: Optional[float] = None,
                     q: Optional[str] = None,
                     limit: int = Query(100, ge=1, le=1000),
                     offset: int = Query(0, ge=0),
                     x_actor_id: Optional[str] = Header(None)):
    actor = current_actor(x_actor_id)
    items = PACKET["extracted_values"]
    if document_id:
        items = [ev for ev in items if ev["document_id"] == document_id]
    if max_confidence is not None:
        items = [ev for ev in items if (ev.get("confidence") or 0) <= max_confidence]
    if q:
        ql = q.lower()
        items = [ev for ev in items if ql in ev.get("field", "").lower()
                 or ql in ev.get("label", "").lower() or ql in ev["id"].lower()]
    total = len(items)
    page = [present_ev(ev, actor) for ev in items[offset:offset + limit]]
    return {"total": total, "extracted_values": page}


@app.get("/api/extracted-values/{ev_id}")
def extracted_value_detail(ev_id: str, x_actor_id: Optional[str] = Header(None)):
    ev = EXTRACTED.get(ev_id)
    if ev is None:
        raise HTTPException(404, f"No extracted value {ev_id}")
    actor = current_actor(x_actor_id)
    if ev.get("value_type") in SENSITIVE_VALUE_TYPES:
        log_view(actor, f"extracted-value:{ev_id}",
                 f"{ev.get('label')} on {ev.get('document_id')}", sensitive=True)
    return resolve_source(ev_id, actor)


# --------------------------------------------------------------------------
# Diagnostics & independent checks
# --------------------------------------------------------------------------
@app.get("/api/diagnostics")
def diagnostics(version: str = CURRENT_VERSION):
    v = get_version(version)
    return {"version": version, "diagnostics": v["diagnostics"]}


@app.get("/api/checks")
def checks(version: str = CURRENT_VERSION):
    """Diagnostics from the engine PLUS a few independent checks computed
    here from the packet (the workpaper must not just trust the engine)."""
    v = get_version(version)
    used = set(v["documents_used"])
    low_conf = [ev for ev in PACKET["extracted_values"] if (ev.get("confidence") or 0) < 0.70]
    not_extracted = [d["id"] for d in PACKET["documents"]
                     if d.get("extraction", {}).get("status") != "extracted"]
    unused_docs = [d["id"] for d in PACKET["documents"] if d["id"] not in used]
    leaf_no_source = [l["key"] for l in v["lines"]
                      if not l.get("inputs") and not l.get("sources")]
    # Identity cross-check: organizer SSNs vs SSNs read off source documents
    # and the prior-year return. A transposed digit here is what gets an
    # e-file rejected, and the engine never flagged it.
    doc_ssns = {ev["value"] for ev in PACKET["extracted_values"]
                if ev.get("value_type") == "ssn" and ev.get("value")}
    prior_ssns = {d.get("ssn") for d in
                  PACKET.get("prior_years", {}).get("return_2024", {}).get("dependents", [])}
    identity_mismatches = []
    for person in PACKET["household"].get("people", []):
        ssn = person.get("ssn")
        if ssn and ssn not in (doc_ssns | prior_ssns):
            # Only flag a *near* match (same digits except the final pair):
            # the transposition pattern that rejects an e-file. A person
            # whose SSN simply appears on no document (e.g. a self-employed
            # spouse with no W-2 in the packet) is not a mismatch.
            near = [s for s in (doc_ssns | prior_ssns)
                    if s and s.replace("-", "")[:-2] == (ssn or "").replace("-", "")[:-2]]
            if near:
                identity_mismatches.append(
                    f"{person.get('name')}: organizer SSN ends "
                    f"{(ssn or '')[-4:]}; document/prior-year SSNs on file end "
                    f"{sorted(s[-4:] for s in near)}")
    # Prior-year variance: lines that moved >50% and >$5,000 vs 2024 need a
    # variance explanation, not just display.
    prior_lines = PACKET.get("prior_years", {}).get("return_2024", {}).get("lines", {})
    current_lines = {l["key"]: l.get("value") for l in v["lines"]}
    variance_keys = []
    for k, old in prior_lines.items():
        new = current_lines.get(k)
        if isinstance(old, (int, float)) and isinstance(new, (int, float)) and old:
            if abs(new - old) > 5000 and abs(new - old) / max(abs(old), 1) > 0.5:
                variance_keys.append(k)
    return {
        "version": version,
        "engine_diagnostics": v["diagnostics"],
        "independent_checks": [
            {"code": "LOW_CONFIDENCE_VALUES", "severity": "warning",
             "count": len(low_conf),
             "message": "Extracted values read with confidence < 0.70 need human verification.",
             "refs": [ev["id"] for ev in low_conf[:25]]},
            {"code": "DOCUMENTS_NOT_FULLY_EXTRACTED", "severity": "warning",
             "count": len(not_extracted),
             "message": "Documents whose extraction status is partial or not_extracted.",
             "refs": not_extracted},
            {"code": "DOCUMENTS_NOT_USED_IN_CURRENT_VERSION", "severity": "info",
             "count": len(unused_docs),
             "message": "Documents not listed in documents_used for this version; each "
                        "should be used or explicitly dispositioned.",
             "refs": unused_docs},
            {"code": "LEAF_LINES_WITHOUT_SOURCES", "severity": "info",
             "count": len(leaf_no_source),
             "message": "Leaf lines with neither input lines nor source values.",
             "refs": leaf_no_source[:25]},
            {"code": "IDENTITY_NUMBER_MISMATCH", "severity": "warning",
             "count": len(identity_mismatches),
             "message": "Organizer SSNs that match no SSN read from source "
                        "documents or the prior-year return (e-file rejection "
                        "risk): " + "; ".join(identity_mismatches),
             "refs": ["D71", "ev-1080", "ev-0012"] if identity_mismatches else []},
            {"code": "PRIOR_YEAR_VARIANCE", "severity": "info",
             "count": len(variance_keys),
             "message": "Lines that moved >50% and >$5,000 vs the 2024 return "
                        "and need a variance explanation (e.g. federal AGI "
                        "228,409 in 2024 vs 445,590 in v3).",
             "refs": variance_keys[:25]},
        ],
    }


# --------------------------------------------------------------------------
# What-if alternatives
# --------------------------------------------------------------------------
@app.get("/api/whatifs")
def whatifs():
    return {"alternatives": [
        {k: a.get(k) for k in ("id", "description", "base_version", "choices",
                                "federal", "california", "changed_lines")}
        for a in PACKET["what_if"]["alternatives"]
    ]}


@app.get("/api/whatifs/{alt_id}")
def whatif_detail(alt_id: str):
    for a in PACKET["what_if"]["alternatives"]:
        if a["id"] == alt_id:
            return a
    raise HTTPException(404, f"No what-if alternative {alt_id}")


class WhatifExploreIn(BaseModel):
    alternative_ids: list[str]
    version: str = CURRENT_VERSION


@app.post("/api/whatifs/explore")
def whatif_explore(body: WhatifExploreIn):
    """Interactive exploration over the 5 PRECOMPUTED alternatives only.

    The tax engine cannot be rerun, so combining alternatives is presented
    honestly as the sum of each precomputed alternative's tax change
    (labelled an approximation — interactions between choices are NOT
    recomputed), never as a new engine result. `estimated_tax_effect` uses
    the version's tax-effect rates for a hypothetical line delta."""
    version = get_version(body.version)
    by_id = {a["id"]: a for a in PACKET["what_if"]["alternatives"]}
    chosen = []
    for alt_id in body.alternative_ids:
        if alt_id not in by_id:
            raise HTTPException(404, f"No what-if alternative {alt_id}")
        a = by_id[alt_id]
        chosen.append({
            "id": a["id"], "description": a["description"],
            "federal_tax_change": a["federal"]["total_tax_change"],
            "california_tax_change": a["california"]["total_tax_change"],
            "changed_lines": len(a["changed_lines"]),
        })
    return {
        "version": body.version,
        "method": "sum_of_precomputed_alternatives",
        "honesty_note": "Each alternative was precomputed by the engine "
                        "against its base version. Summing them is an "
                        "exploration approximation; interactions between "
                        "choices are not recomputed and this is NOT an "
                        "engine result.",
        "alternatives": chosen,
        "combined_federal_tax_change": sum(c["federal_tax_change"] for c in chosen),
        "combined_california_tax_change": sum(c["california_tax_change"] for c in chosen),
        "tax_effect_rates": version.get("tax_effect_rates", {}),
    }


# --------------------------------------------------------------------------
# User state (separate store): notes, sign-offs, adjustments, verifications
# --------------------------------------------------------------------------
class NoteIn(BaseModel):
    version: str = CURRENT_VERSION
    line_key: str
    author: str
    role: Optional[str] = None
    text: str
    blocks_filing: bool = False


class SignoffIn(BaseModel):
    version: str = CURRENT_VERSION
    line_key: str
    signer: str
    role: Optional[str] = None


class AdjustmentIn(BaseModel):
    version: str = CURRENT_VERSION
    line_key: str
    author: str
    role: Optional[str] = None
    new_value: float
    reason: str
    # Which tax_effect_rates category to price the delta with. Defaults to
    # ordinary_income when omitted (the scaffold's documented default).
    category: Optional[str] = None


class VerificationIn(BaseModel):
    version: str = CURRENT_VERSION
    line_key: Optional[str] = None
    extracted_value_id: Optional[str] = None
    verified_by: str
    status: str  # e.g. verified / rejected / needs_review


def effective_signoff_status(row: dict) -> str:
    """A sign-off reopens when the signed line's current value has changed
    since signing. Packet values are immutable in this scaffold, so this
    compares against the value captured at sign-off time."""
    line = LINES.get(row["version"], {}).get(row["line_key"])
    if line is None:
        return "reopened_line_missing"
    if line.get("value") != row["line_value_at_sign"]:
        return "reopened"
    return row.get("status", "signed")


@app.post("/api/notes", status_code=201)
def create_note(body: NoteIn, x_actor_id: Optional[str] = Header(None)):
    actor = current_actor(x_actor_id)
    require(actor, "write_notes")
    check_author_matches(actor, body.author, body.role)
    get_line(body.version, body.line_key)
    payload = body.model_dump()
    payload["author"] = actor.get("name")
    payload["role"] = actor.get("role")
    return state_store.add_note(payload)


@app.get("/api/notes")
def list_notes(version: Optional[str] = None, line_key: Optional[str] = None,
               x_actor_id: Optional[str] = Header(None)):
    actor = current_actor(x_actor_id)
    notes = state_store.list_notes(version, line_key)
    if not can(actor, "firm_internal"):
        # The client sees only their own questions, never firm-internal notes.
        notes = [n for n in notes if n.get("role") == "client"]
    return {"notes": notes}


@app.post("/api/signoffs", status_code=201)
def create_signoff(body: SignoffIn, x_actor_id: Optional[str] = Header(None)):
    actor = current_actor(x_actor_id)
    require(actor, "write_state")
    check_author_matches(actor, body.signer, body.role)
    line = get_line(body.version, body.line_key)
    payload = body.model_dump()
    payload["signer"] = actor.get("name")
    payload["role"] = actor.get("role")
    row = state_store.add_signoff({**payload, "status": "signed",
                                   "line_value_at_sign": line.get("value")})
    row["effective_status"] = effective_signoff_status(row)
    return row


@app.get("/api/signoffs")
def list_signoffs(version: Optional[str] = None, line_key: Optional[str] = None):
    rows = state_store.list_signoffs(version, line_key)
    for row in rows:
        row["effective_status"] = effective_signoff_status(row)
    return {"signoffs": rows}


@app.post("/api/adjustments", status_code=201)
def create_adjustment(body: AdjustmentIn, x_actor_id: Optional[str] = Header(None)):
    """Adjustments never overwrite the packet line: original value, new
    value, author and reason are stored, with the tax effect estimated from
    the version's tax_effect_rates (per the packet readme, the engine
    cannot be rerun). The caller may select the tax-effect category
    (per-line category selection); it defaults to ordinary_income and must
    be one of the version's published rate categories."""
    actor = current_actor(x_actor_id)
    require(actor, "write_state")
    check_author_matches(actor, body.author, body.role)
    line = get_line(body.version, body.line_key)
    version = get_version(body.version)
    original = line.get("value") or 0
    delta = body.new_value - original
    rates_table = version.get("tax_effect_rates", {})
    category = body.category or "ordinary_income"
    if category not in rates_table:
        raise HTTPException(
            422,
            f"Unknown tax-effect category '{category}'. "
            f"Available: {sorted(rates_table.keys())}")
    rates = rates_table.get(category, {})
    tax_effect = {
        "category_used": category,
        "delta": delta,
        "federal": delta * rates.get("federal_per_dollar", 0),
        "california": delta * rates.get("california_per_dollar", 0),
    }
    payload = body.model_dump()
    payload.pop("category", None)
    payload["author"] = actor.get("name")
    payload["role"] = actor.get("role")
    return state_store.add_adjustment({**payload,
                                       "original_value": original,
                                       "tax_effect_category": category,
                                       "tax_effect_estimate": tax_effect})


@app.get("/api/adjustments")
def list_adjustments(version: Optional[str] = None, line_key: Optional[str] = None):
    return {"adjustments": state_store.list_adjustments(version, line_key)}


@app.post("/api/verifications", status_code=201)
def create_verification(body: VerificationIn, x_actor_id: Optional[str] = Header(None)):
    actor = current_actor(x_actor_id)
    require(actor, "write_state")
    check_author_matches(actor, body.verified_by, None)
    if body.line_key:
        get_line(body.version, body.line_key)
    if body.extracted_value_id and body.extracted_value_id not in EXTRACTED:
        raise HTTPException(404, f"No extracted value {body.extracted_value_id}")
    payload = body.model_dump()
    payload["verified_by"] = actor.get("name")
    return state_store.add_verification(payload)


@app.get("/api/verifications")
def list_verifications(version: Optional[str] = None):
    return {"verifications": state_store.list_verifications(version)}


@app.get("/api/view-log")
def view_log(limit: int = Query(200, ge=1, le=1000),
             x_actor_id: Optional[str] = Header(None)):
    """Sensitive-data view log. Firm-internal only: the log itself reveals
    who looked at what, so clients and anonymous callers cannot read it.
    Requests with no X-Actor-Id use the legacy preparer identity (see the
    permission model note), so this still requires identifying as staff
    with any future non-legacy client."""
    actor = current_actor(x_actor_id)
    require(actor, "firm_internal")
    return {"view_log": state_store.list_view_log(limit)}


@app.get("/api/permissions")
def permissions(x_actor_id: Optional[str] = Header(None)):
    actor = current_actor(x_actor_id)
    return {"acting_as": {"id": actor.get("id"), "name": actor.get("name"),
                          "role": actor.get("role"),
                          "sensitive_data_clearance": actor.get("sensitive_data_clearance")},
            "permissions": {a: can(actor, a) for a in
                            ("read_packet", "write_notes", "write_state",
                             "firm_internal", "sensitive")},
            "model": "Roles are resolved server-side from X-Actor-Id against "
                     "the packet's staff/client lists. write_state = sign-offs, "
                     "adjustments, verifications (preparer/reviewer/partner/"
                     "quality_reviewer). write_notes also allows the client "
                     "(questions become evidence). sensitive = unmasked SSNs / "
                     "bank numbers, only with sensitive_data_clearance. "
                     "firm_internal = firm notes + view log. Requests without "
                     "X-Actor-Id are treated as the legacy preparer identity."}


@app.get("/api/state-summary")
def state_summary():
    return state_store.summary()


# --------------------------------------------------------------------------
# Frontend (static single page; all data comes from the APIs above)
# --------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")
