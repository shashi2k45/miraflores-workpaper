# MiraFlores AI — AI Engineer (Tax) Case Study: Starter Plan
Prepared 2026-10-14 (evening, America/New_York) from the invitation email received today at 14:00 EDT.

## What this is
- Sender: Camila Ceal, MiraFlores AI (via PeopleForce)
- Role: AI Engineer (Tax) at MiraFlores AI
- Invitation: move forward by completing a case study — build a working, web-native tax workpaper for one complex household (the invented Okafor-Lindqvist household, tax year 2025, married filing jointly, moved CA -> TX mid-year)
- The packet data is saved alongside this plan: `okafor_lindqvist_2025_packet.json` (downloaded 2026-10-14 from the link in the invitation email)

## Deliverables (from the case study brief, paraphrased)
1. A working web app, run from a link, that loads the packet as delivered, saves everything, and has a role switcher
2. One page explaining the core idea and the data model
3. A list of the errors found in the packet, and how the design surfaced them
4. A video walkthrough (link required) explaining technical decisions and tradeoffs
The email also asks for: the prototype, a brief explanation of approach/key decisions, and the video. Using AI/tools is explicitly allowed — say how they were used.

## Timing — important
- NO submission deadline is stated in the email or in the 3-page brief. The brief's only timing guidance is that sending sooner is better.
- Do NOT confuse this with the fictional in-packet firm deadlines (e.g. the client's extended filing date of 2026-10-15 inside the invented data). Those are part of the test data, not your deadline.
- Practical implication: this is a speed + quality race against other candidates. It outranks cold Dice/Monster applications — it is already past the application stage.

## Packet anatomy (verified by parsing the JSON on 2026-10-14)
- 74 documents (D01–D74): 68 fully extracted, 2 partial, 4 not extracted
- 3,012 extracted values, each with source document/page, field, synthetic highlight position, and a confidence score
- 3 computed return versions: v1 2026-03-04, v2 2026-03-19 (corrected brokerage 1099), v3 2026-06-23 (current; late K-1 + other docs arrived) — v3 has 627 lines
- Client layer: 45 questionnaire answers, 10 messages, 1 call note set
- Firm layer: 6 staff with roles (preparer, reviewer, partner, administrator, quality reviewer), area budgets in hours, starter standards
- 29 timeline events that can be replayed, including an e-file rejection and later acceptance, and a 2028 examination notice
- 5 precomputed what-if alternatives (e.g. Section 179 election, standard vs itemized) — use these plus the per-version tax-effect rates for what-ifs; the tax engine cannot be rerun

## Errors / flags already visible — starting point for deliverable #3
Engine-flagged in v3 diagnostics (11 total; distinguish these from errors you find independently):
- Crypto lot with no cost basis — engine used zero basis
- Brokerage summary vs detail mismatch: summary proceeds differ from the sum of extracted lots by $250
- Client questionnaire says no investments sold, yet documents show 282 brokerage sales + 12 digital asset dispositions
- One handwritten receipt read at only 0.41 confidence
- Unfiled 1099-NECs for two contractors paid $600+; Form 8867 due-diligence still required
- California AMT not computed; FBAR flagged as due separately and outside engagement scope
Resolved between v1 and v3 (good material for showing version/change handling):
- S-corporation basis gap (2023 K-1 missing in v1/v2, in file by v3)
- Partnership K-1 expected but not received in v1/v2, received for v3
- Corrected brokerage 1099 (D31) superseded the original (D30); both are partial — page 32 was never read by the pipeline
Also built into the scenario: an e-file rejection for a dependent's name/ID mismatch, later accepted; prior-year swings are large (2024 AGI vs v3 AGI) and need variance flags, not just display.

## Suggested core idea (for deliverable #2 — adjust to taste)
A provenance-first workpaper, not a spreadsheet clone: every return line is a node in an evidence graph.
- Line -> inputs (other lines) -> sources (extracted-value IDs) -> simulated source document rendered from the packet's printed content, with the exact field highlighted using the stored position. The brief requires simulated documents designed so real documents could replace them seamlessly — keep a clean document-view interface.
- Checks are independent of the engine: reconciliations, summary-vs-detail sums, prior-year variance, completeness (every document used or explicitly dispositioned).
- Adjustments never overwrite: original + who/why + tax effect (computed via the version's tax-effect rates) are kept; sign-offs reopen automatically when a signed line changes.
- Review notes can block filing; client questions become evidence when answered.

## Build sequence (fits his stack: Python / FastAPI / RAG-era tooling)
1. FastAPI backend that loads the packet JSON as-is; expose lines, documents, extracted values, versions, timeline. Persist user state (notes, sign-offs, adjustments, verification status) separately from the packet — never mutate the packet.
2. Frontend (any stack): return summary vs prior year, area summaries, line detail with trace-to-source, document index with extraction status.
3. Version compare v1 -> v2 -> v3 using the packet's changes_from_previous lists; "what changed since I last looked" view.
4. Role switcher over the 6 firm staff + client view, with enforced permissions and a view log for sensitive data (SSNs are fictional in the packet).
5. Checks panel surfacing the diagnostics + your own independent reconciliations; what-if panel using the 5 precomputed alternatives.
6. Timeline replay through filing, rejection, acceptance, payment/refund, and the 2028 notice — freeze at filing, amend on top.
7. Deploy to a public link, write the one-pager, record the video last (script: core idea -> trace a number end-to-end -> show an error surfacing -> show a change reopening a sign-off -> tradeoffs).

## Open / unknown
- No deadline, no named contact beyond the sender, no stated time-box expectation in the email or brief.
- Whether the user has already started this is unknown — nothing in today's chat mentions it; the invitation was only mentioned in passing in this morning's Gmail summary.
