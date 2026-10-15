# MiraFlores AI Engineer (Tax) — Submission Package

**Candidate:** Shashi Kumar Sheelam · **Case study:** Okafor-Lindqvist household,
2025, MFJ, CA→TX move (all data fictional, per the packet).

> **Nothing in this package has been sent to MiraFlores.** This file is the
> checklist and the paste-ready text for the candidate to submit personally.

## What to submit (checklist)

| # | Brief deliverable | Where it lives | Status |
|---|---|---|---|
| 1 | Working web app, run from a link; loads the packet as delivered; saves everything; role switcher | Code: `app/` (FastAPI + vanilla JS, packet read-only). Run/deploy: `deliverables/DEPLOY.md`. **Public link: ⬜ PASTE VERIFIED URL HERE** — not yet deployed; needs the candidate's own free hosting account (one-command Docker path is prepared, see DEPLOY.md) | ✅ built & tested locally · ⬜ public link pending candidate's hosting account |
| 2 | One page on the core idea / data model | `deliverables/one-pager.md` and `deliverables/one-pager.pdf` (exactly 1 page) | ✅ |
| 3 | Errors found + how the design surfaced them | `deliverables/errors-found.md` (11 engine diagnostics · 6 independent checks with verified counts · v1→v3 resolutions) | ✅ |
| 4 | Video walkthrough: technical decisions & tradeoffs | Script + shot list: `deliverables/video-script.md` (word-for-word). **Generated video: `deliverables/walkthrough.mp4`** (4 min 50 s; real app screenshots + AI text-to-speech narration of the script, disclosed on its title card). **Video link: ⬜ PASTE LINK HERE** after uploading the file (or a self-recorded version) | ✅ video file generated · ⬜ upload + link pending candidate |

## Brief requirements → where each is met

- **Loads the packet as delivered** — the app reads
  `okafor_lindqvist_2025_packet.json` untouched; all workpaper state lives in a
  separate SQLite store (`app/state.db`). Delete that file = fresh start.
- **Saves everything** — notes (incl. client questions and blocking flags),
  sign-offs (with the line value at signing time; a later value change
  recomputes the status to *reopened*), adjustments (never overwrite; estimated
  tax effect from the version's `tax_effect_rates`, with a selectable
  per-line category), source-value verifications, and a sensitive-data view log.
- **Role switcher** — 6 firm staff + client view. Server-side enforcement:
  the API resolves the actor's real role from the packet's staff records;
  clients cannot sign off/adjust/verify or read firm-internal notes (403);
  SSNs and bank numbers unmask only for staff with sensitive-data clearance
  (the preparer with a pending background check sees them masked); sensitive
  views are logged (`GET /api/view-log`, staff only).
- **Core idea** — provenance-first evidence graph: line → input lines →
  extracted values (with confidence) → simulated source document with the
  field's position drawn as a highlight box. See the one-pager.
- **Errors surfaced by design** — Checks tab separates the engine's 11 v3
  diagnostics from 6 independently computed checks (incl. the transposed-SSN
  identity error the engine missed); Versions tab shows v1→v3 change lists,
  superseded documents (D30→D31) and resolved diagnostics; Timeline replays
  all 29 events with the filed state freezing at e-file acceptance and later
  events (2028 examination) as an amend-on-top layer.
- **What-ifs without a fake engine** — exploration uses only the 5
  precomputed alternatives and per-version tax-effect rates; combined views
  are labelled as sums of precomputed changes, not engine results.

## Paste-ready AI-use disclosure

> **Disclosure of AI/tool use:** I used an AI assistant (Muse) extensively
> in preparing this case study — to explore the packet, scaffold and build
> the prototype application, compute the independent checks, and draft the
> written deliverables and the video script. The design decisions described
> (provenance-first evidence graph, adjustments-never-overwrite, sign-offs
> that reopen on change, independent checks kept separate from engine
> diagnostics, server-side role enforcement with a sensitive-data view log)
> and the findings in the errors document were verified by me against the
> packet data and the running application, and I take responsibility for
> their accuracy. [If the submitted video is AI-narrated, add: "The
> walkthrough video's narration is AI-generated text-to-speech from my
> script, which the video description also states."]

## Suggested submission email / message (draft — candidate sends)

> Subject: AI Engineer (Tax) case study — Shashi Kumar Sheelam
>
> Hi Camila,
>
> Thank you for the opportunity. My case study deliverables:
>
> 1. **Working app:** <PASTE VERIFIED PUBLIC LINK> — loads the packet as
>    delivered, saves all workpaper state, and includes the role switcher
>    (server-enforced permissions, sensitive-data view log).
> 2. **Core idea / data model (one page):** attached — `one-pager.pdf`.
> 3. **Errors found:** attached — `errors-found.md` (engine diagnostics for
>    v3, independently computed checks — including a transposed dependent SSN
>    that the organizer, documents, and e-file timeline disagree on — and
>    issues resolved v1→v3), each mapped to the app surface that reveals it.
> 4. **Video walkthrough (≈5 min):** <PASTE VIDEO LINK>
>
> [Paste the AI-use disclosure above.]
>
> Source code and run instructions are in the repository (`app/`,
> `deliverables/DEPLOY.md`) if you'd like to run it locally instead.
>
> Best regards,
> Shashi Kumar Sheelam

## Final pre-send checks (candidate)

- [ ] Public app link deployed, opened in a private window, and verified
      (DEPLOY.md checklist), then pasted above and in the message.
- [ ] Video: `walkthrough.mp4` generated (AI-narrated — disclosure
      sentence required if submitted as-is) or self-recorded from
      `video-script.md`; watched end-to-end once; link pasted.
- [ ] `one-pager.pdf` and `errors-found.md` attached (or linked).
- [ ] Disclosure paragraph included in the submission itself.
- [ ] Demo state in the deployed app reset (`state.db` cleared) so
      reviewers start clean.
