# ruff: noqa: E501 - embedded JavaScript/CSS string literals
"""Offline HTML page for an owner-review bundle (see :mod:`sbr.eval.review_bundle`).

One self-contained file: the bundle is embedded as JSON, the script is plain JavaScript, and a Content-Security-Policy
forbids every network request (``connect-src 'none'``; scripts and styles inline only). Decisions live in the browser
(``localStorage``, keyed by the bundle fingerprint) until the owner presses **Export decisions**, which downloads a
``sbr-review-decisions/1`` file for ``tools/review_bundle.py import``. The page never records an identity and never
writes approvals: the import command does that, with the reviewer named by the person running it.
"""

from __future__ import annotations

import html
import json
from collections.abc import Mapping
from typing import Any

_CSP = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' file: data:; "
    "object-src 'self' file:; frame-src 'self' file:; connect-src 'none'; form-action 'none'; base-uri 'none'"
)

_STYLE = """
:root{--bg:#f5f6f8;--fg:#172033;--muted:#5b6676;--card:#fff;--line:#d9dee5;--acc:#2457c5;--warn:#b26b00;--err:#b3261e;
--ok:#1e7a3b}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--fg:#e6e9ee;--muted:#9aa4b2;--card:#1d2128;--line:#2e343e;
--acc:#7aa2ff;--warn:#f0b35a;--err:#ff8a80;--ok:#7fd69b}}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
header{padding:.8rem 1rem;border-bottom:1px solid var(--line);display:flex;gap:1rem;flex-wrap:wrap;align-items:center}
header h1{font-size:1.1rem;margin:0}.counts span{margin-right:.8rem;color:var(--muted)}
main{display:grid;grid-template-columns:minmax(220px,320px) 1fr;min-height:calc(100vh - 60px)}
nav{border-right:1px solid var(--line);overflow:auto;max-height:calc(100vh - 60px)}
nav .filters{padding:.5rem;display:flex;gap:.4rem;flex-wrap:wrap;position:sticky;top:0;background:var(--bg)}
nav button.it{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid var(--line);background:none;
color:inherit;padding:.45rem .6rem;cursor:pointer;font:inherit}nav button.it.sel{background:var(--card)}
.badge{font-size:.75rem;padding:0 .35rem;border-radius:4px;border:1px solid var(--line);margin-left:.3rem}
.b-error{color:var(--err)}.b-warn{color:var(--warn)}.b-done{color:var(--ok)}
section#detail{padding:1rem 1.4rem;overflow:auto;max-height:calc(100vh - 60px)}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:.8rem 1rem;margin:.8rem 0}
.card h3{margin:.1rem 0 .5rem;font-size:.95rem}pre{white-space:pre-wrap;overflow:auto;margin:0;font-size:.85rem}
.flag{margin:.2rem 0}.sev-error{color:var(--err)}.sev-warn{color:var(--warn)}.sev-info{color:var(--muted)}
.decide button{margin:.2rem .3rem .2rem 0;padding:.35rem .8rem;border-radius:6px;border:1px solid var(--line);
background:var(--card);color:inherit;cursor:pointer}.decide button.on{border-color:var(--acc);outline:2px solid var(--acc)}
textarea{width:100%;min-height:4.5rem;font:13px ui-monospace,monospace;background:var(--bg);color:inherit;
border:1px solid var(--line);border-radius:6px;padding:.4rem}
object{width:100%;height:420px;border:1px solid var(--line);border-radius:6px}
.muted{color:var(--muted)}a{color:var(--acc)}.math{font-size:1.5rem;padding:.6rem 0;overflow-x:auto}
@media(max-width:800px){main{grid-template-columns:1fr}nav{max-height:40vh}}
"""

_SCRIPT = r"""
const B = JSON.parse(document.getElementById('bundle').textContent);
const KEY = 'sbr-review:' + B.fingerprint;
let state = {};
try { state = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { state = {}; }
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} };
let filter = {kind: 'all', status: 'all'};
let current = 0;
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const visible = () => B.items.filter(i => (filter.kind === 'all' || i.kind === filter.kind) &&
  (filter.status === 'all' || (filter.status === 'pending' ? !state[i.item_id] :
   filter.status === 'flagged' ? (i.flags.some(f => f.severity !== 'info') || i.proposals.length > 0) : (state[i.item_id]||{}).decision === filter.status)));
function counts() {
  const el = document.getElementById('counts'); const per = {};
  for (const i of B.items) { const p = per[i.kind] ||= {n:0, d:0}; p.n++; if (state[i.item_id]) p.d++; }
  el.innerHTML = Object.entries(per).map(([k,v]) => `<span><b>${esc(k)}</b> ${v.d}/${v.n}</span>`).join('') +
    (Object.keys(B.withheld_for_sensitivity||{}).length ? `<span>withheld (sensitivity): ${esc(JSON.stringify(B.withheld_for_sensitivity))}</span>` : '');
}
function list() {
  const items = visible(); const nav = document.getElementById('list');
  nav.innerHTML = items.map((i, n) => {
    const d = state[i.item_id]; const worst = i.flags.some(f=>f.severity==='error') ? 'error' : i.flags.some(f=>f.severity==='warn') ? 'warn' : '';
    return `<button class="it ${n===current?'sel':''}" data-n="${n}">${esc(i.title)}` +
      (worst ? `<span class="badge b-${worst}">${worst}</span>` : '') +
      (d ? `<span class="badge b-done">${esc(d.decision)}</span>` : '') + `</button>`;
  }).join('') || '<p class="muted" style="padding:.6rem">No items for this filter.</p>';
  nav.querySelectorAll('button.it').forEach(b => b.onclick = () => { current = +b.dataset.n; render(); });
}
function render() {
  counts(); list(); const items = visible(); const i = items[current]; const box = document.getElementById('detail');
  if (!i) { box.innerHTML = ''; return; }
  const d = state[i.item_id] || {};
  const att = i.attachments.map(a => a.endsWith('.pdf') ? `<object data="${esc(a)}" type="application/pdf"><a href="${esc(a)}">${esc(a)}</a></object>` : `<a href="${esc(a)}">${esc(a)}</a>`).join('');
  box.innerHTML = `<h2>${esc(i.title)} <span class="muted">${esc(i.item_id)}</span></h2>
   ${i.source ? `<p class="muted">source: ${esc(JSON.stringify(i.source))}</p>` : ''}
   ${i.prior_decision ? `<p class="muted">earlier decision in the gold log: ${esc(JSON.stringify(i.prior_decision))}</p>` : ''}
   ${att ? `<div class="card"><h3>Source page / crop (local file)</h3>${att}</div>` : ''}
   <div class="card"><h3>Original annotation (unchanged)</h3>${(i.render||{}).original ? `<div class="math">${i.render.original}</div>` : ''}<pre>${esc(JSON.stringify(i.original, null, 2))}</pre></div>
   <div class="card"><h3>Machine checks</h3>${i.flags.map(f => `<div class="flag sev-${esc(f.severity)}">[${esc(f.severity)}] <b>${esc(f.check)}</b>: ${esc(f.detail)}</div>`).join('') || '<span class="muted">none</span>'}</div>
   ${i.proposals.map(p => `<div class="card"><h3>Machine proposal: ${esc(p.proposal_id)} <span class="muted">(${esc(p.confidence)} confidence, ${esc(p.origin)}; not a decision)</span></h3>
     <p class="muted">${esc(p.rationale)}</p>${(i.render||{})[p.proposal_id] ? `<div class="math">${i.render[p.proposal_id]}</div>` : ''}<pre>${esc(typeof p.value === 'string' ? p.value : JSON.stringify(p.value, null, 2))}</pre>
     <div class="decide"><button data-use="${esc(p.proposal_id)}">Use this proposal as my correction</button></div></div>`).join('')}
   <div class="card"><h3>Your decision</h3><div class="decide">${i.allowed_decisions.map(x => `<button data-d="${x}" class="${d.decision===x?'on':''}">${x}</button>`).join('')}
     <button data-d="">clear</button></div>
     <p class="muted">correct: put the corrected value below (text, LaTeX or JSON). Keys: j/k next/prev, 1-4 decide.</p>
     <textarea id="corr" placeholder="corrected value (only for 'correct')">${esc(d.corrected_text || '')}</textarea>
     <textarea id="note" placeholder="note (optional)">${esc(d.note || '')}</textarea>
     ${d.proposal_id ? `<p>using proposal <b>${esc(d.proposal_id)}</b></p>` : ''}</div>`;
  box.querySelectorAll('[data-d]').forEach(b => b.onclick = () => decide(i, b.dataset.d, null));
  box.querySelectorAll('[data-use]').forEach(b => b.onclick = () => decide(i, 'correct', b.dataset.use));
  box.querySelector('#corr').oninput = e => { if (state[i.item_id]) { state[i.item_id].corrected_text = e.target.value; save(); } };
  box.querySelector('#note').oninput = e => { if (state[i.item_id]) { state[i.item_id].note = e.target.value; save(); } };
}
function decide(i, decision, proposal) {
  if (!decision) { delete state[i.item_id]; }
  else { const prev = state[i.item_id] || {}; state[i.item_id] = {decision, proposal_id: proposal || (decision === 'correct' ? prev.proposal_id || null : null),
         corrected_text: decision === 'correct' ? (prev.corrected_text || '') : '', note: prev.note || ''}; }
  save(); render();
}
function parseCorrected(t) { const s = (t || '').trim(); if (!s) return null; if (/^[\[{]/.test(s)) { try { return JSON.parse(s); } catch (e) {} } return s; }
document.getElementById('export').onclick = () => {
  const decisions = B.items.filter(i => state[i.item_id]).map(i => { const d = state[i.item_id];
    return {item_id: i.item_id, decision: d.decision, corrected: d.decision === 'correct' ? parseCorrected(d.corrected_text) : null,
            proposal_id: d.proposal_id || null, note: d.note || ''}; });
  const blob = new Blob([JSON.stringify({schema: 'sbr-review-decisions/1', bundle_fingerprint: B.fingerprint, decisions}, null, 2)], {type: 'application/json'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'review_decisions.json'; a.click();
};
document.getElementById('import').onchange = async e => {
  const f = e.target.files[0]; if (!f) return; const doc = JSON.parse(await f.text());
  if (doc.bundle_fingerprint !== B.fingerprint) { alert('These decisions belong to a different bundle.'); return; }
  for (const d of doc.decisions) state[d.item_id] = {decision: d.decision, proposal_id: d.proposal_id, note: d.note,
    corrected_text: d.corrected == null ? '' : (typeof d.corrected === 'string' ? d.corrected : JSON.stringify(d.corrected, null, 2))};
  save(); render();
};
document.getElementById('kind').onchange = e => { filter.kind = e.target.value; current = 0; render(); };
document.getElementById('status').onchange = e => { filter.status = e.target.value; current = 0; render(); };
document.addEventListener('keydown', e => {
  if (['TEXTAREA','INPUT','SELECT'].includes(e.target.tagName)) return;
  const items = visible(); const i = items[current];
  if (e.key === 'j') { current = Math.min(items.length - 1, current + 1); render(); }
  if (e.key === 'k') { current = Math.max(0, current - 1); render(); }
  if (i && '1234'.includes(e.key) && i.allowed_decisions[+e.key - 1]) decide(i, i.allowed_decisions[+e.key - 1], null);
});
render();
"""


def render_html(bundle: Mapping[str, Any]) -> str:
    data = json.dumps(bundle, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    kinds = "".join(
        f'<option value="{html.escape(k)}">{html.escape(k)} ({n})</option>' for k, n in bundle["sections"].items() if n
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{_CSP}">
<title>Phase 3 owner review</title><style>{_STYLE}</style></head><body>
<header><h1>Phase 3 owner review</h1><div class="counts" id="counts"></div>
<span class="muted">bundle {html.escape(str(bundle["fingerprint"])[:19])} · {html.escape(str(bundle.get("renderer", "")))}</span>
<button id="export">Export decisions</button><label class="muted">Resume from file <input type="file" id="import"
accept="application/json"></label></header>
<main><nav><div class="filters"><select id="kind"><option value="all">all sections</option>{kinds}</select>
<select id="status"><option value="all">all</option><option value="pending">pending</option>
<option value="flagged">flagged</option><option value="accept">accepted</option><option value="correct">corrected</option>
<option value="reject">rejected</option><option value="uncertain">uncertain</option></select></div>
<div id="list"></div></nav><section id="detail"></section></main>
<p class="muted" style="padding:0 1rem">Local file, no network access. Nothing here is approved until you export your
decisions and import them with <code>tools/review_bundle.py import --reviewer user:&lt;you&gt;</code>.</p>
<script type="application/json" id="bundle">{data}</script>
<script>{_SCRIPT}</script></body></html>
"""
