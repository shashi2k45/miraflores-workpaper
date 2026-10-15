# Video Walkthrough — Narration Script & Shot List

**MiraFlores AI — AI Engineer (Tax) case study · Candidate: Shashi Kumar Sheelam**
**Target length: ≈ 5 minutes** at a natural ~130 words/minute.
Narration below is **word-for-word**. Bracketed lines are directions, not spoken.

> **Status:** an AI-narrated version of this exact script was generated and
> saved as `deliverables/walkthrough.mp4` (4 min 50 s, real app screenshots
> + text-to-speech narration, with an on-screen disclosure on the title
> card). The candidate may submit that file, or record their own voice
> using this script — either way the AI use must be disclosed (see
> `SUBMISSION.md`). Timings below are the script's plan; the generated
> video's scene boundaries are within a few seconds of them.

## Before you record (5 minutes)

1. Start the app: `cd app && .venv/bin/uvicorn main:app --port 8765`, open
   `http://localhost:8765/`. Delete `app/state.db` first so the demo state is clean.
2. Browser at 100% zoom, window ≈1280×800. Close other tabs. Silence notifications.
3. Record screen + voice (QuickTime / OBS / Loom — any tool). Speak the script as
   written; pause where a scene changes. If you stumble, pause 2 seconds and
   restart that scene — editing beats re-recording everything.
4. Demo state is created *live* by the script (a sign-off, an adjustment, a
   verification). If you re-record from the top, delete `app/state.db` and
   restart the server so the demo starts clean again.

---

## Scene 1 — Core idea (0:00–0:35) · Shot: Summary tab

> "Hi, I'm Shashi Kumar Sheelam. This is my prototype for the MiraFlores case
> study: a workpaper for the Okafor-Lindqvist 2025 return. The core idea is
> simple. A tax return is a set of numbers whose only defense is where each
> number came from — so I built the workpaper as an evidence graph. Every
> return line points to the lines that feed it, and to the extracted values
> and source documents behind those. Nothing in this app is more than one
> click from its evidence."

**Action:** slow scroll over the Summary tab (federal/CA table, questionnaire).

## Scene 2 — Trace a number end-to-end (0:35–1:50) · Shot: Lines & trace tab

> "Let's trace a number. Form 1040, line 1a: wages, two hundred twelve
> thousand four hundred dollars."
>
> [click Lines & trace; search "F1040.1a"; click the line]
>
> "The trace shows exactly what produced it: two W-2 wages values. The first
> is one hundred four thousand six hundred dollars, read from document D08,
> the Corvane W-2, box 1, at ninety-nine percent confidence. And here is the
> part I care most about — the simulated source document, with the exact
> field highlighted, drawn from the position the extraction pipeline stored.
> The reviewer never has to take the number on faith, and never has to go
> hunting through a thirty-two-page PDF. The document view is an interface:
> simulated pages today, real page images tomorrow, with nothing else in the
> system changing."
>
> [hover the red highlight box on the D08 page; scroll to the second source]

## Scene 3 — An error surfacing (1:50–2:55) · Shot: Checks tab

> "Second: how errors surface. This Checks tab deliberately separates two
> kinds of findings. At the top, the engine's own eleven diagnostics for the
> current version — including a crypto lot with no cost basis, and a two
> hundred fifty dollar mismatch between the brokerage summary and its own
> detail."
>
> [scroll to Independent checks]
>
> "Below that are checks my workpaper computes itself, because a review tool
> should not just repeat the engine's claims. The one I want to show you was
> never flagged by the engine: an identity mismatch. Theo's Social Security
> number in the client organizer ends in thirty-three-oh-nine. His Social
> Security card — document D71 — and the prior-year return both say
> thirty-three-ninety. The last two digit pairs are transposed. That is
> precisely the error that gets an e-file rejected — and the timeline shows
> this return was rejected, on July thirteenth, and accepted the next day.
> The design also triages every low-confidence read: exactly two values in
> three thousand and twelve fall below point seven, including a handwritten
> receipt read at point four one — and any reviewer can mark it verified,
> right from the trace."

**Action:** on the Checks tab, point at `IDENTITY_NUMBER_MISMATCH`, then
`LOW_CONFIDENCE_VALUES` (count 2), `PRIOR_YEAR_VARIANCE` (count 22).

## Scene 4 — Change, sign-off, and who is allowed to do what (2:55–4:00) · Shot: Lines & trace → Review tab; role switcher

> "Third: change. Back on the wages line, I'll sign it off as Priya Raman,
> the preparer."
>
> [as Priya (preparer, default): click "Sign off F1040.1a"; then enter
> adjustment new value 212500, category "wages", reason "demo — pending W-2c",
> click "Add adjustment"]
>
> "Notice what did not happen: the original number was not overwritten. The
> adjustment is a new fact — original value, new value, who, why, and an
> estimated tax effect priced from this version's own tax-effect rates for
> the wages category I selected. And the sign-off stored the value at
> signing time: if a recompute changes this line, that sign-off's status
> recomputes to 'reopened' on read. A v1 approval can never silently bless
> v3 numbers."
>
> [switch role switcher to "Client view"; scroll the trace action row]
>
> "Permissions are enforced on the server, not hidden in the UI. As the
> client, I can read and ask questions — a question becomes evidence — but
> the sign-off and adjustment controls are disabled, and if I call the API
> directly, it answers four-oh-three. The client also never sees
> firm-internal notes. And one more real case from this packet: Marcus Bell,
> a preparer whose background check is pending, has no sensitive-data
> clearance — for him, Social Security and bank numbers stay masked, and
> every sensitive view anyone makes is written to an audit log you can see
> in the Review tab."

**Action:** open Review tab as a staff role at the end to show the note/
sign-off/adjustment rows and the view log.

## Scene 5 — What-ifs and the timeline (4:00–4:45) · Shot: What-ifs tab → Timeline tab

> "Two shorter points. What-ifs: the tax engine cannot be rerun, so the app
> never pretends to recompute. It explores only the five alternatives the
> engine precomputed — ticking 'standard deduction' and 'no bonus
> depreciation' sums their precomputed changes, and the screen labels that
> as an approximation, not an engine result. And the timeline replays all
> twenty-nine events in order: three computed versions, the signing, the
> rejection, the acceptance. At acceptance the filed state freezes — the
> twenty twenty-eight examination notice arrives as an amend-on-top layer.
> Filed history is never rewritten."

**Action:** tick the two what-ifs, click "Explore selected combination";
then Timeline tab, click "Play" briefly / step to the end.

## Scene 6 — Tradeoffs and close (4:45–5:20) · Shot: Versions tab, then Summary

> "Tradeoffs, honestly. I spent the budget on provenance, independent
> checks, and the state model, because those are what a reviewer trusts.
> What I deliberately did not build: a tax engine — the packet forbids
> recomputation — and authentication, which a production deployment must
> add in front of the permission model that is already enforced server-side.
> The packet itself is never mutated; delete one SQLite file and the
> workpaper resets. The code, a one-page write-up of the data model, and a
> full list of the errors found — engine-flagged and independently
> discovered — are in the submission package. Thank you for your time."

---

## Shot list (for editing / the generated version)

| # | Time | Screen / action | Key visual |
|---|---|---|---|
| 1 | 0:00–0:35 | Summary tab, slow scroll | Federal/CA summary table + questionnaire |
| 2 | 0:35–1:50 | Lines & trace: search `F1040.1a`, open trace | Source card for ev-0016 (D08, 0.99) with the **red highlight box** on the simulated W-2 page |
| 3 | 1:50–2:55 | Checks tab | 11 engine diagnostics; `IDENTITY_NUMBER_MISMATCH` (Theo …-3309 vs …-3390); `LOW_CONFIDENCE_VALUES` = 2 |
| 4 | 2:55–4:00 | Trace actions → Review tab; role switcher → Client, then Marcus Bell | Sign-off created; adjustment with category `wages`; client controls disabled; masked SSN for st-04; view log rows |
| 5 | 4:00–4:45 | What-ifs tab; Timeline tab | Two alternatives ticked, combined (labelled) totals; replay stepping to "filing frozen" |
| 6 | 4:45–5:20 | Versions tab → Summary | v1/v2/v3 change counts (63 / 89); closing frame |

## Disclosure

AI/tool use is disclosed in the submission package (`SUBMISSION.md`). If any
part of this video is AI-narrated in the submitted version, say so in the
submission wherever the video link is pasted — the case study permits AI use
with disclosure, and the honest label is part of the deliverable.

*Script prepared with AI assistance (Muse), as the case study permits when disclosed.*
