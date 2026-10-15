// MiraFlores workpaper frontend — vanilla JS over the FastAPI APIs.
// Permissions are enforced SERVER-side: every request carries X-Actor-Id
// for the role-switcher selection, and the API resolves the real role from
// the packet's staff/client lists. The UI additionally disables controls
// the API would reject, using /api/staff's reported permissions.
const $ = (s) => document.querySelector(s);
let currentVersion = "v3";
let currentRole = null; // staff/client entry incl. permissions
let allStaff = [];

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (currentRole) headers["X-Actor-Id"] = currentRole.id;
  const res = await fetch(path, { ...opts, headers });
  if (!res.ok) {
    let detail = `${res.status} ${path}`;
    try { detail += " — " + (await res.json()).detail; } catch (e) { /* keep */ }
    throw new Error(detail);
  }
  return res.json();
}
const money = (v) => (typeof v === "number" ? v.toLocaleString("en-US") : v);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const canDo = (action) => !!(currentRole && currentRole.permissions && currentRole.permissions[action]);

async function init() {
  const staff = await api("/api/staff");
  allStaff = staff.staff;
  const meta = await api("/api/meta");
  currentVersion = meta.current_version;
  $("#metaLine").textContent =
    `${meta.packet.name} · client ${meta.packet.client_id} · ${meta.counts.documents} documents · ` +
    `${meta.counts.extracted_values.toLocaleString()} extracted values · filing status: ${meta.household.filing_status.replaceAll("_", " ")}`;
  const vs = await api("/api/versions");
  $("#versionSelect").innerHTML = vs.versions.map(v =>
    `<option value="${v.version}" ${v.version === currentVersion ? "selected" : ""}>${v.version} — ${v.computed_at.slice(0, 10)}${v.is_current ? " (current)" : ""}</option>`).join("");
  $("#roleSwitcher").innerHTML = allStaff.map(s =>
    `<option value="${s.id}">${esc(s.name)} — ${esc(s.role)}</option>`).join("");
  setRole(allStaff[0]);
  $("#roleSwitcher").addEventListener("change", (e) =>
    setRole(allStaff.find(s => s.id === e.target.value)));
  $("#versionSelect").addEventListener("change", (e) => { currentVersion = e.target.value; renderSummary(); renderLines(); renderChecks(); });
  document.querySelectorAll("nav button").forEach(b => b.addEventListener("click", () => showTab(b.dataset.tab)));
  $("#lineSearch").addEventListener("input", renderLines);
  $("#lineJurisdiction").addEventListener("change", renderLines);
  renderSummary(); renderLines(); renderDocuments(); renderChecks(); renderVersions(); renderWhatifs(); initReplay(); renderReview();
}

function setRole(person) {
  currentRole = person;
  const p = person.permissions || {};
  $("#roleNote").textContent =
    `Acting as ${person.name} (${person.role}) — server-enforced permissions: ` +
    `notes ${p.write_notes ? "✓" : "✗"}, sign-offs/adjustments/verifications ${p.write_state ? "✓" : "✗"}, ` +
    `firm-internal ${p.firm_internal ? "✓" : "✗"}, unmasked sensitive data ${p.sensitive ? "✓" : "✗"}` +
    (!person.sensitive_data_clearance && person.role !== "client" ? " · No sensitive-data clearance: SSNs/bank numbers stay masked for this role and sensitive views are logged." : "");
  // Re-render views that depend on the actor (masking, filtering, buttons).
  renderSummary(); renderLines(); renderReview();
}

function showTab(name) {
  document.querySelectorAll("nav button").forEach(b => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll("main section").forEach(s => s.hidden = s.id !== `tab-${name}`);
}

// ---- Simulated document with the highlight box drawn ---------------------
// The packet's position is a normalized box {x0,y0,x1,y1} over the page.
// We render the page's printed_content in a positioned container and draw
// the box as an absolutely-positioned overlay (% = normalized coords x100).
function docPageHTML(pageText, position, caption) {
  const hl = position
    ? `<div class="hlbox" title="${esc(caption || "highlighted field")}" style="left:${position.x0 * 100}%;top:${position.y0 * 100}%;width:${(position.x1 - position.x0) * 100}%;height:${(position.y1 - position.y0) * 100}%"></div>`
    : "";
  return `<div class="docwrap"><div class="docpage">${esc(pageText || "(no page text)")}</div>${hl}</div>`;
}

async function renderSummary() {
  const v = await api(`/api/versions/${currentVersion}`);
  const fed = v.summary.federal, ca = v.summary.california;
  const row = (label, o) => `<tr><td>${label}</td><td>${money(o.agi ?? o.total_agi)}</td><td>${money(o.total_tax)}</td><td>${money(o.payments)}</td><td>${money(o.balance_due)}</td></tr>`;
  const q = await api("/api/questionnaire");
  $("#tab-summary").innerHTML = `
    <h2>Return summary — ${currentVersion} (computed ${v.computed_at})</h2>
    <p class="muted">${esc(v.trigger)}</p>
    <table><tr><th></th><th>AGI</th><th>Total tax</th><th>Payments</th><th>Balance due (− = refund)</th></tr>
    ${row("Federal", fed)}${row("California", ca)}</table>
    <h3>Questionnaire (${q.questionnaire.length} answers)</h3>
    <div class="list">${q.questionnaire.map(a => `<div class="card"><b>${esc(a.id)}</b> ${esc(a.question)}<br><i>${esc(a.answer)}</i> <span class="muted">— ${esc(a.answered_by)}</span></div>`).join("")}</div>
    ${q.call_notes && q.call_notes.length ? `<h3>Call notes (firm-internal)</h3><div class="list">${q.call_notes.map(n => `<div class="card">${esc(JSON.stringify(n))}</div>`).join("")}</div>` : ""}`;
}

async function renderLines() {
  const q = encodeURIComponent($("#lineSearch").value || "");
  const jur = $("#lineJurisdiction").value;
  const data = await api(`/api/versions/${currentVersion}/lines?limit=200&q=${q}${jur ? `&jurisdiction=${jur}` : ""}`);
  $("#lineList").innerHTML = `<p class="muted">${data.total} lines (showing ${data.lines.length})</p>` +
    data.lines.map(l => `<button data-key="${esc(l.key)}"><code>${esc(l.key)}</code> ${esc(l.label)} — <b>${money(l.value)}</b></button>`).join("");
  $("#lineList").querySelectorAll("button").forEach(b => b.addEventListener("click", () => renderTrace(b.dataset.key)));
}

async function renderTrace(key) {
  const t = await api(`/api/versions/${currentVersion}/lines/${encodeURIComponent(key)}/trace`);
  const rates = (await api(`/api/versions/${currentVersion}`)).tax_effect_rates;
  const cats = Object.keys(rates);
  const node = (n, depth) => {
    if (!n || n.truncated || n.missing) return `<li><code>${esc(n ? n.key : "?")}</code> (not expanded)</li>`;
    const srcs = (n.sources || []).filter(Boolean).map(s => {
      const ev = s.extracted_value;
      return `<div class="card">
        <b>${esc(ev.id)}</b> · ${esc(ev.label)} = <b>${esc(ev.value)}</b>
        <span class="muted">confidence ${ev.confidence}${ev.masked_for_role ? " · masked for role " + esc(ev.masked_for_role) : ""}</span><br>
        Source: <code>${esc(s.document.id)}</code> ${esc(s.document.title)}, page ${s.page} — simulated document, highlighted field:
        ${docPageHTML(s.printed_content, s.position, `${ev.id}: ${ev.label}`)}
        <span class="muted">Highlight box drawn from the packet's synthetic position ${JSON.stringify(s.position)}</span>
        <br><button ${canDo("write_state") ? "" : "disabled"} onclick="verifyValue('${ev.id}')">Mark verified as ${esc(currentRole.name)}</button>
        ${canDo("write_state") ? "" : `<span class="muted">(role ${esc(currentRole.role)} cannot verify — server-enforced)</span>`}
      </div>`;
    }).join("");
    return `<li><code>${esc(n.key)}</code> ${esc(n.label || "")} — <b>${money(n.value)}</b>
      <span class="muted">${esc(n.rule || "")}${n.note ? " · " + esc(n.note) : ""}</span>
      ${n.inputs && n.inputs.length ? `<ul>${n.inputs.map(i => node(i, depth + 1)).join("")}</ul>` : ""}
      ${srcs}</li>`;
  };
  $("#lineTrace").innerHTML = `<h3>Trace: ${esc(key)}</h3><ul>${node(t.trace, 0)}</ul>
    <div class="row">
      <button ${canDo("write_state") ? "" : "disabled"} onclick="signOff('${esc(key)}')">Sign off ${esc(key)} as ${esc(currentRole.name)} (${esc(currentRole.role)})</button>
      <input id="adjValue" type="number" step="any" placeholder="Adjustment: new value">
      <select id="adjCategory">${cats.map(c => `<option value="${c}" ${c === "ordinary_income" ? "selected" : ""}>${c}</option>`).join("")}</select>
      <input id="adjReason" placeholder="Reason for adjustment">
      <button ${canDo("write_state") ? "" : "disabled"} onclick="adjustLine('${esc(key)}')">Add adjustment</button>
      ${canDo("write_state") ? "" : `<span class="muted">This role cannot sign off or adjust (server-enforced).</span>`}
    </div>
    <div id="traceMsg"></div>`;
}

async function signOff(key) {
  try {
    const r = await api("/api/signoffs", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version: currentVersion, line_key: key, signer: currentRole.name, role: currentRole.role }) });
    $("#traceMsg").innerHTML = `<p>Signed off (id ${r.id}, status: ${esc(r.effective_status)}).</p>`;
    renderReview();
  } catch (e) { $("#traceMsg").innerHTML = `<p class="err">${esc(e.message)}</p>`; }
}
async function adjustLine(key) {
  try {
    const r = await api("/api/adjustments", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version: currentVersion, line_key: key, author: currentRole.name, role: currentRole.role,
        new_value: parseFloat($("#adjValue").value), reason: $("#adjReason").value || "(no reason given)",
        category: $("#adjCategory").value }) });
    $("#traceMsg").innerHTML = `<p>Adjustment recorded (id ${r.id}, category ${esc(r.tax_effect_category)}, est. tax effect ${esc(JSON.stringify(r.tax_effect_estimate))}). The packet line itself is never overwritten.</p>`;
    renderReview();
  } catch (e) { $("#traceMsg").innerHTML = `<p class="err">${esc(e.message)}</p>`; }
}
async function verifyValue(evId) {
  try {
    await api("/api/verifications", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version: currentVersion, extracted_value_id: evId, verified_by: currentRole.name, status: "verified" }) });
    alert(`${evId} marked verified by ${currentRole.name}`);
  } catch (e) { alert(e.message); }
}

async function renderDocuments() {
  const d = await api("/api/documents");
  $("#docList").innerHTML = `<h2>Documents (${d.total})</h2>
    <p class="muted">Extraction: ${JSON.stringify(d.status_counts)} · Sensitive documents (bank/identity) log a view entry when opened.</p>` +
    d.documents.map(doc => `<div class="card"><button onclick="showDoc('${doc.id}')"><code>${doc.id}</code> ${esc(doc.title)}</button>
      <span class="muted">${esc(doc.document_type)} · ${doc.page_count} pages · status: ${esc(doc.extraction.status)} (${doc.extraction.values} values)</span></div>`).join("");
}
async function showDoc(id) {
  const d = await api(`/api/documents/${id}`);
  // Map each extracted value on the shown page to its highlight box.
  const firstPage = (d.document.pages || [])[0];
  const pageValues = firstPage ? d.extracted_values.filter(ev => ev.page === firstPage.page) : [];
  $("#docDetail").innerHTML = `<h3>${esc(d.document.id)} — ${esc(d.document.title)}${d.sensitive_document ? ' <span class="tag">sensitive — view logged</span>' : ""}</h3>` +
    (firstPage ? docPageHTML(firstPage.printed_content,
        pageValues.length ? pageValues[0].position : null,
        pageValues.length ? `${pageValues[0].id}: ${pageValues[0].label}` : "") : "") +
    `<div class="list">${d.extracted_values.map(ev => `<div class="card"><b>${esc(ev.id)}</b> p.${ev.page} · ${esc(ev.label)} = <b>${esc(ev.value)}</b> <span class="muted">confidence ${ev.confidence}${ev.masked_for_role ? " · masked for your role" : ""} · position ${JSON.stringify(ev.position)}</span></div>`).join("")}</div>` +
    `<p class="muted">${d.extracted_values.length} extracted values on this document. The first value on page 1 is highlighted above; pick any line's trace to see each value highlighted in context.</p>`;
  $("#docDetail").scrollIntoView();
}

async function renderChecks() {
  const c = await api(`/api/checks?version=${currentVersion}`);
  const diag = (x) => `<div class="card ${x.severity === "warning" ? "warn" : "info"}"><code>${esc(x.code)}</code> (${esc(x.severity)}) — ${esc(x.message)}<br><span class="muted">refs: ${(x.refs || []).slice(0, 12).map(esc).join(", ")}</span></div>`;
  $("#tab-checks").innerHTML = `<h2>Checks — ${currentVersion}</h2>
    <h3>Engine diagnostics (${c.engine_diagnostics.length})</h3>${c.engine_diagnostics.map(diag).join("")}
    <h3>Independent checks (computed by this workpaper, not by the engine)</h3>${c.independent_checks.map(x => diag({ ...x, message: `${x.message} Count: ${x.count}` })).join("")}`;
}

async function renderVersions() {
  const vs = await api("/api/versions");
  const details = await Promise.all(vs.versions.map(v => api(`/api/versions/${v.version}`)));
  $("#tab-versions").innerHTML = "<h2>Return versions</h2>" + details.map(v => `
    <div class="card"><h3>${v.version} — ${v.computed_at} ${v.is_current ? "(current)" : ""}</h3>
    <p class="muted">${esc(v.trigger)}</p>
    <p>Federal AGI ${money(v.summary.federal.agi)} · tax ${money(v.summary.federal.total_tax)} · balance ${money(v.summary.federal.balance_due)}</p>
    <p>${v.changes_from_previous.length} changes from previous version
    ${v.changes_from_previous.length ? `<details><summary>Show changes</summary><div class="list">${v.changes_from_previous.slice(0, 100).map(c => `<div><code>${esc(c.key)}</code> ${esc(c.change)}: ${money(c.old)} → ${money(c.new)}</div>`).join("")}</div></details>` : ""}</p></div>`).join("");
}

async function renderWhatifs() {
  const w = await api("/api/whatifs");
  $("#tab-whatifs").innerHTML = `<h2>What-if explorer — precomputed alternatives only</h2>
    <p class="muted">The tax engine cannot be rerun. Tick alternatives to see each one's precomputed
    result; combined totals are the <b>sum of the precomputed changes</b> (an exploration
    approximation — interactions are not recomputed, and /api/whatifs/explore labels it as such).</p>` +
    w.alternatives.map(a => `
    <div class="card"><label><input type="checkbox" class="whatifPick" value="${a.id}"> <b>${esc(a.id)}</b></label>
    <p>${esc(a.description)}</p>
    <p>Federal tax change: <b>${money(a.federal.total_tax_change)}</b> · California tax change: <b>${money(a.california.total_tax_change)}</b> · ${a.changed_lines.length} lines change</p></div>`).join("") +
    `<button id="whatifGo">Explore selected combination</button><div id="whatifResult"></div>`;
  $("#whatifGo").addEventListener("click", async () => {
    const ids = [...document.querySelectorAll(".whatifPick:checked")].map(x => x.value);
    if (!ids.length) { $("#whatifResult").innerHTML = "<p>Select at least one alternative.</p>"; return; }
    const r = await api("/api/whatifs/explore", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alternative_ids: ids, version: currentVersion }) });
    $("#whatifResult").innerHTML = `<div class="card"><h3>Combined (sum of precomputed)</h3>
      <p>Federal tax change: <b>${money(r.combined_federal_tax_change)}</b> · California tax change: <b>${money(r.combined_california_tax_change)}</b></p>
      <p class="muted">${esc(r.honesty_note)}</p></div>`;
  });
}

// ---- Timeline replay -----------------------------------------------------
let replayUpto = 0;
async function initReplay() { renderReplay(); }
async function renderReplay() {
  const r = await api(`/api/timeline/replay?upto=${replayUpto}`);
  const s = r.state;
  $("#tab-timeline").innerHTML = `<h2>Timeline replay — step ${r.upto} of ${r.total_events}</h2>
    <div class="row">
      <button id="rpPrev">◀ Step back</button>
      <button id="rpNext">Step forward ▶</button>
      <button id="rpPlay">Play</button>
      <button id="rpReset">Reset</button>
      <span class="muted">Phase: <b>${esc(s.phase)}</b> · current version at this point: <b>${esc(s.current_version_at_point || "—")}</b>
      · signed 8879: ${s.signed_8879 ? "yes" : "no"} · e-file accepted: ${s.efile_accepted ? "yes" : "no"}
      · filing frozen: ${s.filing_frozen ? "YES — later events form an amend-on-top layer" : "no"}</span>
    </div>
    <p class="muted">${esc(s.note)}</p>
    ${r.next_event ? `<p>Next: <code>${esc(r.next_event.id)}</code> ${esc(r.next_event.at)} — <b>${esc(r.next_event.event)}</b></p>` : "<p><b>Replay complete.</b></p>"}
    <div class="list">${r.happened.map(e => `<div class="card"><code>${esc(e.id)}</code> ${esc(e.at)} — <b>${esc(e.event)}</b> ${esc(e.detail || "")} <span class="muted">${(e.refs || []).map(esc).join(", ")}</span></div>`).join("")}</div>`;
  $("#rpPrev").onclick = () => { replayUpto = Math.max(0, replayUpto - 1); renderReplay(); };
  $("#rpNext").onclick = () => { replayUpto = Math.min(r.total_events, replayUpto + 1); renderReplay(); };
  $("#rpReset").onclick = () => { replayUpto = 0; renderReplay(); };
  $("#rpPlay").onclick = async () => {
    while (replayUpto < r.total_events) {
      replayUpto += 1; await renderReplay();
      await new Promise(res => setTimeout(res, 450));
    }
  };
}

async function renderReview() {
  const notes = await api(`/api/notes?version=${currentVersion}`);
  const signoffs = await api(`/api/signoffs?version=${currentVersion}`);
  const adj = await api(`/api/adjustments?version=${currentVersion}`);
  let viewLogHTML = `<p class="muted">The view log is firm-internal; role ${esc(currentRole.role)} cannot read it (server-enforced).</p>`;
  if (canDo("firm_internal")) {
    const vl = await api("/api/view-log?limit=50");
    viewLogHTML = vl.view_log.map(x => `<div class="card"><span class="muted">${esc(x.created_at)}</span> ${esc(x.actor)} (${esc(x.role)}) viewed <code>${esc(x.resource)}</code>${x.sensitive ? ' <b>sensitive</b>' : ""} <span class="muted">${esc(x.detail || "")}</span></div>`).join("") || `<p class="muted">No views logged yet.</p>`;
  }
  $("#tab-review").innerHTML = `<h2>Review state (stored separately from the packet)</h2>
    <h3>Add a note ${currentRole.role === "client" ? "(client question — becomes evidence)" : ""}</h3>
    <input id="noteLine" placeholder="Line key, e.g. F1040.1a">
    <label><input type="checkbox" id="noteBlocks"> blocks filing</label>
    <textarea id="noteText" placeholder="Note text"></textarea>
    <button id="noteAdd" ${canDo("write_notes") ? "" : "disabled"}>Add note as ${esc(currentRole.name)}</button>
    <h3>Notes visible to your role (${notes.notes.length})</h3>
    ${notes.notes.map(n => `<div class="card"><code>${esc(n.line_key)}</code> — ${esc(n.text)} <span class="muted">by ${esc(n.author)} (${esc(n.role || "")})${n.blocks_filing ? " · BLOCKS FILING" : ""}</span></div>`).join("")}
    <h3>Sign-offs (${signoffs.signoffs.length})</h3>
    ${signoffs.signoffs.map(s => `<div class="card"><code>${esc(s.line_key)}</code> signed by ${esc(s.signer)} — status: <b>${esc(s.effective_status)}</b> <span class="muted">(signed at value ${money(s.line_value_at_sign)})</span></div>`).join("")}
    <h3>Adjustments (${adj.adjustments.length})</h3>
    ${adj.adjustments.map(a => `<div class="card"><code>${esc(a.line_key)}</code>: ${money(a.original_value)} → ${money(a.new_value)} by ${esc(a.author)} — ${esc(a.reason)} <span class="muted">category ${esc(a.tax_effect_category || "ordinary_income")} · est. tax effect ${esc(JSON.stringify(a.tax_effect_estimate))}</span></div>`).join("")}
    <h3>Sensitive-data view log (firm-internal)</h3>
    ${viewLogHTML}`;
  const addBtn = $("#noteAdd");
  if (addBtn) addBtn.addEventListener("click", async () => {
    try {
      await api("/api/notes", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: currentVersion, line_key: $("#noteLine").value, author: currentRole.name, role: currentRole.role, text: $("#noteText").value, blocks_filing: $("#noteBlocks").checked }) });
      renderReview();
    } catch (e) { alert(e.message); }
  });
}

init().catch(e => { document.body.insertAdjacentHTML("beforeend", `<p>Error: ${esc(e.message)}</p>`); });
