# MiraFlores AI — AI Engineer (Tax) Case Study: Working Prototype

A provenance-first tax workpaper for the fictional Okafor-Lindqvist household
(2025, married filing jointly, CA → TX move), built from the packet in
`okafor_lindqvist_2025_packet.json`. See `PLAN.md` for the case-study
analysis this prototype implements, and `deliverables/SUBMISSION.md` for
the full submission package.

**Status: submission-ready locally.** The app runs locally, loads the real
packet, and implements the core architecture end-to-end, including
server-side permission enforcement with a sensitive-data view log. The
one-pager and errors write-up are in `deliverables/`. Two things remain
for the candidate personally: deploying to a public link (needs their own
hosting account — one-command Docker path prepared in `app/Dockerfile`
and `deliverables/DEPLOY.md`) and uploading the video walkthrough
(`deliverables/walkthrough.mp4`, AI-narrated from the word-for-word
script in `deliverables/video-script.md`; a personal recording is the
alternative). Nothing has been sent to MiraFlores.

## Install & run (local)

```bash
cd ~/workspace/miraflores-case-study/app
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --port 8765
# open http://localhost:8765/
```

Interactive API docs: http://localhost:8765/docs

To reset all review state, stop the server and delete `app/state.db`
(the packet is never written to).

## Core idea / architecture

Every return line is a node in an evidence graph:

```
return line ──inputs──▶ other return lines
            ──sources─▶ extracted values (id, field, value, confidence,
                        synthetic highlight position)
                        ──▶ source document + page (printed_content)
```

- `app/main.py` — FastAPI backend. Loads the packet JSON read-only at
  startup, indexes documents / extracted values / lines by id, and exposes
  the APIs below. The packet file is opened once, never mutated.
- `app/state_store.py` — SQLite store (`app/state.db`) for *workpaper*
  state only: review notes, sign-offs, adjustments, verifications, and a
  sensitive-data view log — kept fully separate from packet data,
  mirroring the packet readme's point that the packet "contains no
  reviews, notes, sign-offs or decisions."
- `app/static/` — a dependency-free vanilla-JS single page served by
  FastAPI: summary, line list + trace-to-source detail, document index,
  checks panel, versions, what-ifs, timeline, and a review tab.
- **Sign-off reopen rule:** a sign-off records the line's value at signing
  time; its effective status is recomputed on read — if the line's current
  value differs, the sign-off reports `reopened`. Adjustments never
  overwrite a line: original value, new value, author, reason, a selectable
  per-line tax-effect category (validated against the version's
  `tax_effect_rates` keys; `ordinary_income` by default), and an estimated
  tax effect (delta × the chosen category's rates) are stored instead.
- **Independent checks** (`GET /api/checks`): on top of the engine's own
  diagnostics, the workpaper computes six of its own — low-confidence
  extracted values (< 0.70), documents not fully extracted, documents not
  used in the current version, leaf lines with no sources, an
  organizer-vs-document identity (SSN) mismatch check, and a prior-year
  variance check (> 50% and > $5,000 vs the 2024 return).
- **Permissions** (server-side): every request may carry an `X-Actor-Id`
  header (`st-01`…`st-06` or `client`); the server resolves the actor's
  real role from the packet's staff records and enforces it — write-State
  actions (sign-offs, adjustments, verifications) are staff-only, the
  client cannot read firm-internal notes, SSNs and bank numbers unmask
  only for staff with `sensitive_data_clearance`, and sensitive views are
  written to the view log (`GET /api/view-log`, staff only). Requests
  without the header fall back to the preparer role for local-demo
  convenience; see "Implemented vs deferred" for the honest limits.

### API endpoints

| Endpoint | What |
|---|---|
| `GET /api/meta` | Packet info, counts, household (SSNs masked unless the actor holds sensitive-data clearance) |
| `GET /api/staff` | 6 firm staff + a client role, each with computed permissions (role switcher source) |
| `GET /api/permissions` | The acting role's permission set + the permission model in words |
| `GET /api/questionnaire` | 45 questionnaire answers + messages + call notes |
| `GET /api/timeline` | 29 timeline events |
| `GET /api/timeline/replay?upto=N` | Replay state after N events (current version at that point, signed/accepted/frozen flags, phase) |
| `GET /api/versions` / `GET /api/versions/{v}` | Version list / detail incl. summary, rates, diagnostics, `changes_from_previous` |
| `GET /api/versions/{v}/lines?jurisdiction=&form=&q=` | Line list with filters/pagination |
| `GET /api/versions/{v}/lines/{key}` | One line |
| `GET /api/versions/{v}/lines/{key}/trace` | **Provenance trace**: line → inputs (recursive) → extracted values → document, page text, position, confidence |
| `GET /api/documents` / `GET /api/documents/{id}` | Document index (extraction status) / document with pages + its values |
| `GET /api/extracted-values?...` / `GET /api/extracted-values/{id}` | Values with filters (document, confidence, search) / one value resolved to its document |
| `GET /api/diagnostics?version=v3` | Engine diagnostics for a version |
| `GET /api/checks?version=v3` | Engine diagnostics + independent checks |
| `GET /api/whatifs` / `GET /api/whatifs/{id}` | 5 precomputed what-if alternatives |
| `POST /api/whatifs/explore` | Combine selected precomputed alternatives (labelled sum, not an engine result) |
| `POST/GET /api/notes` | Review notes (can block filing); clients see only client-visible notes |
| `POST/GET /api/signoffs` | Sign-offs with effective (reopen-aware) status (staff write roles only) |
| `POST/GET /api/adjustments` | Non-overwriting adjustments with per-line tax-effect category + estimate |
| `POST/GET /api/verifications` | Verification status for lines / extracted values |
| `GET /api/view-log` | Sensitive-data view log (staff only) |
| `GET /api/state-summary` | Counts of stored user state |

## Implemented vs deferred

**Implemented**

- All read APIs above over the packet as delivered (3,012 extracted values,
  74 documents, 627-line current return, 3 versions).
- Trace-to-source UI with the source page's printed content and the
  packet's synthetic highlight position **drawn as an overlay box**, plus
  confidence per value.
- Checks panel surfacing all 11 v3 engine diagnostics plus 6 independent
  checks computed from the packet (low confidence 2, not fully extracted
  6, unused in v3 3, leaf lines without sources 5, identity mismatch 1,
  prior-year variance 22).
- Version view listing v1/v2/v3 with summaries and their full
  `changes_from_previous` lists (63 for v2, 89 for v3).
- What-if panel: all 5 precomputed alternatives plus an explorer that
  combines selected alternatives as a clearly-labelled sum (no fake
  engine).
- Timeline replay: step/play through all 29 events; the filed state
  freezes at e-file acceptance and post-filing events are presented as
  an amend-on-top layer.
- Role switcher over the 6 firm staff plus a client view, with
  **server-side permission enforcement**: write-State actions are
  staff-only (client writes get 403), firm-internal notes are hidden
  from the client, SSNs/bank numbers unmask only for clearance holders,
  and sensitive views are recorded in a view log.
- Adjustment tax-effect category is selectable per line (validated
  against the version's rate categories; `ordinary_income` default).
- Persistent notes / sign-offs / adjustments / verifications / view log
  in SQLite.

**Deferred / honest limits**

- **Authentication.** The role switcher sends the actor id in a header
  and the server enforces that actor's real permissions, but there is no
  login/session proof behind it — a production deployment must put real
  authentication in front. Requests without the header default to the
  preparer for local-demo convenience (documented in the API).
- Timeline replay derives version/phase state from event kinds; it does
  not re-derive return lines at each historical point.
- What-if exploration combines only the 5 precomputed alternatives; no
  interactive what-if creation (the engine cannot be rerun — tax effects
  for adjustments are estimated from `tax_effect_rates`).
- No public deployment yet: `app/Dockerfile` + `deliverables/DEPLOY.md`
  are prepared, but a public link needs the candidate's own hosting
  account.

## Deliverables checklist (case study → this package)

- [x] Working web app that loads the packet as delivered — runs locally;
      public link still needs the candidate's hosting account
      (`deliverables/DEPLOY.md`)
- [x] Saves everything — review state persists in SQLite across restarts
- [x] Role switcher — 6 firm staff + client view, server-enforced
- [x] One page on core idea / data model — `deliverables/one-pager.md`
      and `deliverables/one-pager.pdf`
- [x] Errors found + how the design surfaced them —
      `deliverables/errors-found.md` (engine diagnostics vs. independent
      checks vs. v1→v3 resolutions, with verified counts)
- [x] Video walkthrough — word-for-word script + shot list in
      `deliverables/video-script.md`, and an AI-narrated video generated
      from it: `deliverables/walkthrough.mp4` (4 min 50 s, real app
      screenshots + TTS, disclosed on its title card). Uploading it (or
      recording a personal version) is the candidate's step — see
      `deliverables/SUBMISSION.md`
- [x] Submission package — `deliverables/SUBMISSION.md` (checklist,
      deliverables map, paste-ready disclosure). Nothing has been sent
      to MiraFlores.

## Disclosure

This prototype and its written deliverables were built with AI assistance
(Muse), as the case study explicitly permits with disclosure. All
household data is fictional (per the packet readme).
