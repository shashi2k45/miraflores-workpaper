# Errors Found in the Okafor-Lindqvist Packet — and How the Design Surfaces Them

**MiraFlores AI — AI Engineer (Tax) case study · Candidate: Shashi Kumar Sheelam**

Every finding below was verified against the packet data and the finished app's
live output (`GET /api/checks?version=v3`, re-run at delivery time). Findings are
separated by *who found them*, because in a review tool that distinction is the
whole point: the workpaper must never present the engine's own claims and its
independent findings as if they were the same thing.

- **§1 — Engine diagnostics in v3: 11** (5 warnings, 6 info)
- **§2 — Independent findings computed by this workpaper: 6 checks** (the app's
  own checks panel), including a material identity error the engine never flagged
- **§3 — Issues resolved between v1 and v3: 2 diagnostics cleared**, plus the
  version history that demonstrates how the design handles change

How to read the "Surfaced by" column: **Checks tab** = the app's checks panel
(`GET /api/checks`), **Trace** = line → inputs → sources → highlighted document,
**Versions tab** = v1/v2/v3 comparison, **Documents tab** = document index/detail.

---

## §1 Engine diagnostics in the current return (v3) — 11

These are the preparer engine's own flags, carried in the packet's
`return_versions[v3].diagnostics`. The app displays them verbatim, labelled as
engine diagnostics, in the Checks tab.

| # | Code (severity) | Finding | Surfaced by |
|---|---|---|---|
| 1 | `DIGITAL_ASSET_BASIS_MISSING` (warning) | Coinhaven crypto lot **C6 has no cost basis** (transfer-in from an external wallet). The engine used **zero basis** and the transfer-in date, so the gain on that lot is overstated by the full proceeds until a basis is substantiated. Refs: ev-0879, ev-0881, ev-0882, ev-0918, ev-0919. | Checks tab; Trace from the digital-asset gain lines to D35, where the basis value (§2.3) is visibly absent |
| 2 | `BROKER_SUMMARY_DETAIL_MISMATCH` (warning) | Meridian 1099-B **summary proceeds $71,965.00 do not equal the sum of the extracted lots, $71,715.00 — a $250 difference**. One of the two numbers feeding the return is wrong. Ref: ev-0703. | Checks tab; independent summary-vs-detail reconciliation is the pattern §2 generalises |
| 3 | `QUESTIONNAIRE_SALES_CONFLICT` (warning) | Questionnaire answer qa-14 says **no investments were sold**, while the documents show **282 brokerage sales and 12 digital-asset dispositions**. The client's claim and the evidence cannot both be true. | Checks tab; Summary tab shows the questionnaire next to the return it contradicts |
| 4 | `LOW_CONFIDENCE_READ` (warning) | A **handwritten receipt amount was read at 0.41 confidence** (ev-1049, D64, St. Brigid Parish cash gift, $1,500 as read). Below any reasonable auto-accept threshold. | Checks tab; §2.1 triages *all* low-confidence reads, not just this one |
| 5 | `FORM_1099_FILING` (warning) | Schedule C paid **two contractors ≥ $600 and no Forms 1099-NEC were filed** (client confirms at qa-22/qa-23: "didn't know we had to"). Refs: SchC lines I, J. | Checks tab; questionnaire answers are displayed as evidence, so the admission is one click from the flag |
| 6 | `DUE_DILIGENCE_REQUIRED` (warning) | **Form 8867 due diligence is still outstanding** for the child tax credit / credit for other dependents. Ref: F8867.status. | Checks tab |
| 7 | `CA_AMT_NOT_COMPUTED` (warning) | **California AMT (Schedule P, 540NR) was not computed**; the ISO exercise needs a California-source allocation review. Ref: F6251 line 2i. | Checks tab |
| 8 | `AMT_CREDIT_CARRYFORWARD` (info) | Federal AMT arises from the ISO exercise (a deferral item); a minimum-tax-credit carryforward to 2026 (Form 8801) is expected. Refs: F6251 line 11. | Checks tab; Versions tab shows `carryovers_out` per version |
| 9 | `AOTC_PHASED_OUT` (info) | The American Opportunity Credit is **fully phased out** by modified AGI — claimed-credit expectations should be set accordingly. Ref: F8863 line 7. | Checks tab |
| 10 | `FBAR_OUTSIDE_RETURN` (info) | Foreign-account maximum exceeds $10,000: **FinCEN Form 114 (FBAR) is due separately** and is outside the engagement scope — a deadline the return itself will never remind anyone about. Ref: F8938 line 1 max. | Checks tab |
| 11 | `HOME_OFFICE_AREA_CHANGE` (info) | Home-office area averages **240 sq ft vs 300 sq ft in 2024** — worth confirming the move (CA→TX, July 2025) explains it before the deduction is challenged. Ref: SchC line 30. | Checks tab; §2.6 covers prior-year variance systematically |

## §2 Found independently by this workpaper — 6 computed checks

These are computed by the app from the packet at request time
(`GET /api/checks`, "Independent checks"); none of them repeats an engine
diagnostic. Counts below are the app's actual output for v3.

### 2.1 `LOW_CONFIDENCE_VALUES` — count **2**
Extracted values read with confidence < 0.70 need human verification before a
reviewer relies on them. Exactly two exist in 3,012 values:
- **ev-1049** — the 0.41 handwritten receipt (the one case the engine also flagged), and
- **ev-0919** — the C6 crypto cost-basis field itself, read at **0.60 with an empty
  value** — i.e. the "missing basis" in §1.1 is not just an engine opinion; the
  underlying extraction is literally blank.
*Surfaced by:* Checks tab with refs; Trace shows the confidence next to every
source value, and any staff role can mark a value *verified* from the trace
(the client role cannot — server-enforced).

### 2.2 `IDENTITY_NUMBER_MISMATCH` — count **1** ⚠ material, engine-missed
**Theo Lindqvist-Okafor's SSN in the client organizer is transposed.** The
organizer lists **…-3309**; his Social Security card (D71, value ev-1080, read at
0.99 confidence) and the prior-year return both say **…-3390** — the last two
digit pairs are swapped. The check compares every household SSN against SSNs read
from source documents and the prior-year return and flags only near-matches
(same digits except the final pair), which is exactly the transposition pattern.
*Why it matters:* this is the class of error that rejects an e-file — and the
timeline shows the return **was** rejected (tl-21, 2026-07-13) and only accepted
the next day (tl-23). The engine's 11 diagnostics never mention it.
*Surfaced by:* Checks tab (this check); the masked/unmasked handling of the SSN
itself is governed by the permission model (§2.7).

### 2.3 `DOCUMENTS_NOT_FULLY_EXTRACTED` — count **6**
Documents whose extraction status is not "extracted" (of 74: 68 extracted,
2 partial, 4 not extracted):
- **D30 and D31 — both partial, and both are missing the same thing: page 32
  ("Additional transactions") was never read by the pipeline.** D31 is the
  *corrected* Meridian 1099 that the current return relies on (§3), so the
  corrected return is computed from a document with an unread page.
- D07 (prior-preparer workpaper export), D69 (IRS transcript), D70 (2023 CP2000
  file), D72 (2025 examination letter) — not extracted, but each is reproduced as
  structured data elsewhere in the packet, which the Documents tab shows.
*Surfaced by:* Checks tab; Documents tab lists extraction status and value counts
for every document, so an unread page cannot hide inside a 159-value document.

### 2.4 `DOCUMENTS_NOT_USED_IN_CURRENT_VERSION` — count **3**
Documents not in v3's `documents_used`, each of which must be used or explicitly
dispositioned: **D30** (superseded by D31 — correct, see §3), **D71** (Theo's SS
card — the very document that proves §2.2, sitting unused), and **D72** (the IRS
examination letter — correctly post-filing, and handled by the timeline's
amend-on-top layer rather than the filed return).
*Surfaced by:* Checks tab; Timeline replay shows D72 arriving after the filing froze.

### 2.5 `LEAF_LINES_WITHOUT_SOURCES` — count **5**
Leaf lines with neither input lines nor source values — numbers a reviewer cannot
trace to any evidence: `SchB.8`, `F4797.26g`, `SchD.18`, `F8960.14`, `F540NR.73`.
On inspection these are defaults/thresholds (e.g. the $250,000 NIIT threshold,
a "No" default, a $0 extension payment) — probably benign, but the design
principle is that *untraceable* is itself a finding: each one must be explainable
from its rule, which the trace view displays.
*Surfaced by:* Checks tab; Trace shows the rule and note for each such line.

### 2.6 `PRIOR_YEAR_VARIANCE` — count **22**
Lines that moved **> 50% and > $5,000** versus the 2024 return and therefore need
a variance explanation rather than silent acceptance. The headline: **federal AGI
rose from $228,409 (2024) to $445,590 (v3)** and capital gains (F1040 line 7)
swung from **−$3,000 to +$185,027**. Much of the swing is explainable from the
packet (condo sale, ISO exercise, job change, CA→TX move) — but "explainable
after the fact" is precisely what a variance check exists to force.
*Surfaced by:* Checks tab with the 22 line keys; Summary/Versions views show the
current-year numbers the variance is measured against.

### 2.7 Supporting findings from the same inspection (narrative, no separate counter)
- **Duplicate document risk, handled correctly:** D09 and D10 are the same
  Halvorsen W-2 (original + phone photo) with **17 identical extracted values
  each**. Line F1040.1a's note records that it was counted once — the trace
  makes that auditable, because both W-2 copies appear as documents while only
  the counted sources feed the line.
- **Client claims vs documents (general pattern):** beyond qa-14 (§1.3), qa-15
  ("we didn't really sell [crypto], just moved things around") sits awkwardly
  next to **12 digital-asset dispositions** — the design treats every
  questionnaire answer as a claim to be checked, which is why the Summary tab
  renders the questionnaire beside the return.
- **A preparer without clearance joined mid-engagement:** Marcus Bell
  (preparer, started 2026-03-24) has `sensitive_data_clearance = false`
  (background check pending, "no access to full SSNs or bank numbers"). The
  app enforces this on the server: his role sees SSNs and the Swedish bank
  account number (ev-0963, D36) masked in the app, and every sensitive view
  by any role is written to the view log. (The numbers discussed in this
  write-up are the packet's fictional data, stated because the mismatch
  itself is the finding.)
- **Quality reviewer timing:** Sam Adeyemi's `active_from` is **2027-01-04** —
  the same day the timeline shows the return being selected for quality review
  (tl-27). Consistent, but a reviewer who did not exist at the firm during
  preparation is exactly the kind of fact the role switcher surfaces by
  resolving real staff records instead of free-text names.

## §3 Resolved between v1 and v3 — what changed, and why it matters

v1 (2026-03-04) and v2 (2026-03-19) each carried **13 diagnostics**; v3
(2026-06-23) carries **11**. The two that disappeared demonstrate the version
story the app is built to tell:

| Resolved diagnostic | What happened | Evidence in the app |
|---|---|---|
| `SCORP_BASIS_INCOMPLETE` (v1, v2 → gone in v3) | The **2023 Schedule K-1** for the S corporation was not in file; the engine had assumed no net basis change while distributions exceeded computed basis. The K-1 was received **2026-06-05** and is in file for v3. | Versions tab: v3's trigger names the document; v3 shows 89 changes from v2 |
| `K1_EXPECTED_NOT_RECEIVED` (v1, v2 → gone in v3) | The **Ridgeline Real Estate Fund III LP K-1**, expected (reported in 2024) but not received, arrived **2026-06-22** and triggered the v3 recompute. The client had predicted this at qa-13 ("Ridgeline usually comes late — they said June"). | Versions tab: v3 trigger; Summary tab questionnaire qa-13 |

Version handling more broadly:
- **v2 exists because a corrected document superseded an original:** the
  corrected Meridian 1099 (**D31**, received 2026-03-18) superseded **D30**;
  v2 records D30 in `documents_superseded`, changed **61 lines, added 1,
  removed 1** versus v1 — and both versions of the document remain in the
  packet and in the app, so "which 1099 did this number come from?" is always
  answerable. (Caution carried into §2.3: both D30 and D31 are missing page 32.)
- **Change is a first-class view:** the Versions tab lists every version's
  `changes_from_previous` (v2: 63 entries; v3: 89 entries) next to its trigger,
  and a sign-off taken against an older value reports **reopened** rather than
  silently standing — the mechanism that keeps a v1 approval from blessing v3
  numbers.
- **The filing itself is a version event:** the timeline replay steps through
  computation (v1 → v2 → v3), the client's Form 8879 approval, the **e-file
  rejection on 2026-07-13** (§2.2's transposed SSN is the packet-consistent
  explanation), acceptance on 2026-07-14, federal payment and the California
  refund — then **freezes**. The 2028 examination notice (D72 / Letter 566,
  received 2028-01-26, items: noncash charitable contributions and Schedule C
  receipts reconciliation) arrives as an amend-on-top layer, never as a rewrite
  of the filed return.

---

*Method note: §1 is the engine's own output, quoted and labelled as such. §2 was
computed independently from the packet by the app in this repository
(`GET /api/checks`) and cross-checked by hand against the raw values cited
(ev-0919, ev-1049, ev-1080, D30/D31 page-32 notes, D09/D10 value comparison,
prior-year line comparison). §3 is read from the three versions' diagnostics,
triggers, `documents_superseded`, and `changes_from_previous` lists.*

*Disclosure: this document was prepared with AI assistance (Muse), as the case
study explicitly permits when disclosed.*
