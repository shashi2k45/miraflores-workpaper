# A Provenance-First Tax Workpaper — Core Idea & Data Model

**MiraFlores AI — AI Engineer (Tax) case study · Candidate: Shashi Kumar Sheelam**
*Working app: `app/` in this repository (run/deploy instructions in `SUBMISSION.md`). All household data is fictional, per the packet.*

## The problem with a spreadsheet clone

A computed tax return is a set of numbers whose only defense is *where each number
came from*. A spreadsheet shows values; when a reviewer asks "why is this 212,400?",
the answer lives in someone's memory, a sticky note, or a PDF on page 19 of a 32-page
1099. Review becomes archaeology — and errors survive because nobody can afford to
re-derive every line.

## Core idea: every return line is a node in an evidence graph

The workpaper treats the return not as a form to fill in, but as a graph to inspect:

```
return line ──inputs──▶ other return lines
            ──sources─▶ extracted values (field, value, confidence,
                        highlight position on the page)
                        ──▶ simulated source document (page text as delivered)
```

Clicking any line walks that graph: the line, the lines that feed it, the extracted
values that feed those, and finally the simulated source document with the **exact
field highlighted** (drawn from the packet's stored position box). A number is never
more than one click from its evidence. Simulated documents sit behind a clean
document-view interface (`printed_content` + values + positions), so real page
images can replace them without touching the rest of the system.

Three design consequences follow:

1. **Checks are independent of the engine.** The workpaper recomputes what it can
   check without trusting the preparer's engine: extraction-confidence triage,
   completeness (every document used or explicitly dispositioned), leaf lines with
   no source, organizer-vs-document identity matching, and prior-year variance.
   Engine diagnostics and independent findings are displayed — and labelled —
   separately, so a reviewer always knows who is making a claim.
2. **Adjustments never overwrite.** A correction is a new fact — original value,
   proposed value, author, reason, tax-effect category, and an estimated tax effect
   priced from the version's published `tax_effect_rates` — never an edit to history.
   A sign-off records the line's value *at signing time*; if the value later changes,
   the sign-off's effective status recomputes to **reopened** on read. Stale approval
   is impossible to mistake for current approval.
3. **The packet is immutable; workpaper state is separate.** Everything the firm
   *does* — notes (which can block filing), sign-offs, adjustments, verifications,
   and a sensitive-data view log — lives in a separate store keyed by version and
   line. Deleting that store resets the workpaper; the evidence never changes.

## Data model

| Entity (packet, read-only) | Key fields | Notes |
|---|---|---|
| Document (74) | `id`, type, issuer, pages[] | `extraction.status`: 68 extracted / 2 partial / 4 not extracted |
| Extracted value (3,012) | `id`, `document_id`, `page`, `field`, `value`, `confidence`, `position{x0,y0,x1,y1}` | The atomic unit of evidence; low confidence is a first-class signal |
| Return version (v1–v3) | `computed_at`, `trigger`, `summary`, `tax_effect_rates`, `diagnostics`, `changes_from_previous` | v3 (2026-06-23) is current: 627 lines |
| Return line (per version) | `key`, form/line, `value`, `rule`, `inputs[]`, `sources[]` | The graph node; `inputs` = other lines, `sources` = extracted-value ids |
| Client layer | 45 questionnaire answers, messages, call notes | Client answers are claims to be checked against documents, not facts |
| Firm layer | 6 staff + roles + `sensitive_data_clearance`, timeline (29 events), 5 what-if alternatives | Roles drive server-side permissions |

**Permissions are enforced on the server, not the switcher.** Every request carries
the acting person's id; the server resolves the real role from the packet's staff
list. Preparers/reviewers/partners/quality reviewers may sign off, adjust and
verify; the client may read and ask questions (a question becomes evidence) but
cannot sign off or see firm-internal notes. SSNs and bank numbers are unmasked only
for staff holding sensitive-data clearance — the preparer whose background check is
pending sees them masked — and every sensitive view is written to an auditable log.

**What-if honesty.** The engine cannot be rerun, so the app never pretends to
recompute tax. Exploration uses only the 5 precomputed alternatives and the
per-version tax-effect rates; combined views are labelled as sums of precomputed
changes, not engine results.

**Timeline.** The 29 events replay in order; once the return is signed (Form 8879)
and e-file accepted, the filed state freezes and later events (an examination
notice) form an amend-on-top layer — the filed return is never rewritten.

---

*Disclosure: this prototype and document were built with AI assistance (Muse),
as the case study explicitly permits when disclosed. See `SUBMISSION.md` for the
full disclosure text and the deliverables map.*
