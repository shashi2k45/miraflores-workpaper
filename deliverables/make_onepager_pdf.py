#!/usr/bin/env python3
"""Generate one-pager.pdf (exactly one A4 page) from the one-pager content.
Tooling only - not part of the app. Run: python3 make_onepager_pdf.py"""
from fpdf import FPDF

OUT = __file__.rsplit("/", 1)[0] + "/one-pager.pdf"


class OnePager(FPDF):
    def section(self, title):
        self.set_font("helvetica", "B", 10.5)
        self.set_text_color(28, 79, 214)
        self.cell(0, 5.2, title, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(20, 20, 20)

    def body(self, text, size=9.3):
        self.set_font("helvetica", "", size)
        self.multi_cell(0, 4.35, text)
        self.ln(1.2)

    def bullet(self, text):
        self.set_font("helvetica", "", 9.3)
        x = self.get_x()
        self.cell(4, 4.35, "-")
        self.multi_cell(0, 4.35, text)
        self.ln(0.6)


pdf = OnePager("P", "mm", "A4")
pdf.set_auto_page_break(False)
pdf.set_margins(14, 12, 14)
pdf.add_page()

pdf.set_font("helvetica", "B", 15)
pdf.cell(0, 7, "A Provenance-First Tax Workpaper", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("helvetica", "B", 11)
pdf.cell(0, 5.5, "Core Idea & Data Model", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("helvetica", "I", 8.5)
pdf.multi_cell(0, 4, "MiraFlores AI - AI Engineer (Tax) case study - Candidate: Shashi Kumar Sheelam. "
                     "All household data is fictional, per the packet.")
pdf.ln(2)

pdf.section("The problem with a spreadsheet clone")
pdf.body("A computed tax return is a set of numbers whose only defense is where each number came from. "
         "A spreadsheet shows values; when a reviewer asks why a line is 212,400, the answer lives in "
         "someone's memory or on page 19 of a 32-page 1099. Review becomes archaeology - and errors "
         "survive because nobody can afford to re-derive every line.")

pdf.section("Core idea: every return line is a node in an evidence graph")
pdf.body("return line -> inputs (other return lines) -> sources (extracted values: field, value, "
         "confidence, highlight position) -> simulated source document (page text as delivered).")
pdf.body("Clicking any line walks that graph to the simulated source document with the exact field "
         "highlighted, drawn from the packet's stored position box. A number is never more than one "
         "click from its evidence. Simulated documents sit behind a clean document-view interface, so "
         "real page images can replace them without touching the rest of the system.")
pdf.bullet("Checks are independent of the engine. The workpaper recomputes what it can check without "
           "trusting the preparer's engine: extraction-confidence triage, completeness (every document "
           "used or explicitly dispositioned), leaf lines with no source, organizer-vs-document identity "
           "matching, prior-year variance. Engine diagnostics and independent findings are labelled separately.")
pdf.bullet("Adjustments never overwrite. A correction is a new fact - original value, proposed value, "
           "author, reason, tax-effect category, and an estimated tax effect priced from the version's "
           "tax_effect_rates. A sign-off records the line's value at signing time; if the value changes, "
           "its effective status recomputes to reopened on read.")
pdf.bullet("The packet is immutable; workpaper state is separate. Notes (which can block filing), "
           "sign-offs, adjustments, verifications and a sensitive-data view log live in a separate "
           "store keyed by version and line. Deleting it resets the workpaper; the evidence never changes.")

pdf.section("Data model (packet, read-only)")
pdf.body("Document (74): id, type, issuer, pages[]; extraction.status = 68 extracted / 2 partial / 4 not extracted.  "
         "Extracted value (3,012): id, document_id, page, field, value, confidence, position {x0,y0,x1,y1} - "
         "the atomic unit of evidence.  Return version (v1-v3): computed_at, trigger, summary, tax_effect_rates, "
         "diagnostics, changes_from_previous; v3 (2026-06-23) is current, 627 lines.  Return line: key, form/line, "
         "value, rule, inputs[], sources[] - the graph node.  Client layer: 45 questionnaire answers, messages, "
         "call notes (claims to check, not facts).  Firm layer: 6 staff with roles and sensitive_data_clearance, "
         "29 timeline events, 5 what-if alternatives.")

pdf.section("Permissions, what-ifs, timeline - honesty by design")
pdf.body("Permissions are enforced on the server, not the switcher: every request carries the acting person's "
         "id and the server resolves the real role from the packet's staff list. Staff with write roles may sign "
         "off, adjust and verify; the client may read and ask questions but cannot sign off or see firm-internal "
         "notes. SSNs and bank numbers unmask only for clearance holders (a preparer with a pending background "
         "check sees them masked), and every sensitive view is logged.  What-ifs: the engine cannot be rerun, so "
         "exploration uses only the 5 precomputed alternatives and tax-effect rates, with combined views labelled "
         "as sums, not engine results.  Timeline: the 29 events replay in order; once signed (Form 8879) and "
         "e-file accepted, the filed state freezes and later events form an amend-on-top layer.")

pdf.ln(1)
pdf.set_font("helvetica", "I", 8)
pdf.multi_cell(0, 3.8, "Disclosure: this prototype and document were built with AI assistance (Muse), as the "
                       "case study explicitly permits when disclosed. Full disclosure text and deliverables map: SUBMISSION.md.")

pdf.output(OUT)
print("pages:", pdf.page_no(), "->", OUT)
