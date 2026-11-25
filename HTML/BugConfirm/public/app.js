const savedTypes = (() => { try { const value = JSON.parse(localStorage.getItem('bugconfirm.types')); return Array.isArray(value) && value.length ? value : null; } catch { return null; } })();
const state = { page: 1, pages: 1, total: 0, selected: null, timers: null, staticTags: [], llmTags: [], securityTags: [], knownTags: {}, typeOptions: [], selectedTypes: savedTypes, pageSize: Number(localStorage.getItem('bugconfirm.pageSize')) || 50, groupBy: localStorage.getItem('bugconfirm.groupBy') || 'type' };
const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (ch) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' }[ch]));
const labelName = { unreviewed: 'Unreviewed', real: 'Real bug', not_real: 'Not a bug', unsure: 'Unsure' };
const reportedPhases = ['Not Reported', 'Reported', 'Submitted', 'Confirmed', 'Accepted'];

async function request(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || 'Request failed');
  return payload;
}
function connection(message, kind = '') { const node = $('#connection'); node.textContent = message; node.className = `connection ${kind}`; }
function pill(kind, text) { return `<span class="pill ${kind}">${esc(text)}</span>`; }
function agentResultPill(verified) {
  if (verified === true) return pill('true', 'TRUE');
  if (verified === false) return pill('false', 'FALSE');
  return pill('pending', 'NOT VERIFIED');
}
function renderSource(ref) {
  const highlights = new Set(ref.highlight_lines || []);
  return ref.source.split('\n').map((line, index) => {
    const number = (ref.start_line || 1) + index;
    return `<span class="code-line ${highlights.has(number) ? 'highlighted' : ''}"><span class="line-number">${number}</span>${esc(line)}</span>`;
  }).join('');
}

function percent(value) { return value == null ? '—' : `${(value * 100).toFixed(1)}%`; }
function renderMetrics(stats) {
  const items = [[stats.total, 'static-analysis bugs'], [stats.verified, 'agent-verified'], [stats.reviewed, 'manually decided'], [stats.fixed, 'fixed'], [percent(stats.false_positive_rate), 'false-positive rate'], [percent(stats.false_negative_rate), 'false-negative rate'], [percent(stats.original_positive_ratio), 'original agent-positive ratio'], [percent(stats.confirmed_real_ratio), 'confirmed-real ratio']];
  $('#metrics').innerHTML = items.map(([number, text]) => `<article class="metric"><strong>${number}</strong><span>${text}</span></article>`).join('');
}
async function loadStats() { renderMetrics(await request('/api/stats')); }
function saveTypeFilter() { if (state.selectedTypes === null) localStorage.removeItem('bugconfirm.types'); else localStorage.setItem('bugconfirm.types', JSON.stringify(state.selectedTypes)); }
function renderTypeOptions() {
  const selected = state.selectedTypes === null ? null : new Set(state.selectedTypes);
  $('#type-options').innerHTML = state.typeOptions.length ? state.typeOptions.map(({ type, count }) => `<label class="type-option"><input type="checkbox" value="${esc(type)}" ${selected === null || selected.has(type) ? 'checked' : ''}><span>${esc(type)}</span><small>${count}</small></label>`).join('') : '<span class="muted">No bug types available.</span>';
}
async function loadBugTypes() {
  const data = await request('/api/bug-types');
  state.typeOptions = data.items;
  if (state.selectedTypes !== null) {
    state.selectedTypes = state.selectedTypes.filter((type) => data.items.some((item) => item.type === type));
    if (!state.selectedTypes.length) { state.selectedTypes = null; saveTypeFilter(); }
  }
  renderTypeOptions();
}
async function loadKnownTags() {
  const classes = ['static', 'llm', 'security'];
  const responses = await Promise.all(classes.map((tagClass) => request(`/api/tags?class=${tagClass}`)));
  for (const [index, tagClass] of classes.entries()) {
    const items = responses[index].items;
    state.knownTags[tagClass] = items;
    $(`#known-${tagClass}-tags`).innerHTML = items.map(({ tag, count }) => `<option value="${esc(tag)}" label="used ${count} time${count === 1 ? '' : 's'}"></option>`).join('');
  }
}

function query() { const params = new URLSearchParams({ page: state.page, pageSize: state.pageSize, group: state.groupBy, q: $('#search').value, tag: $('#tag-filter').value, verified: $('#verified').value, label: $('#label').value, fixed: $('#fixed').value, reported_phase: $('#reported-phase-filter').value }); if (state.selectedTypes !== null) params.set('types', state.selectedTypes.join(',')); return params; }
function renderBugItem(item) {
  return `<button class="bug ${state.selected === item.id ? 'active' : ''}" data-id="${item.id}"><span class="bug-title">${esc(item.title)}</span><span class="bug-meta">#${item.id} · ${esc(item.type)} ${agentResultPill(item.verified)} ${pill(item.review.label, labelName[item.review.label])}${item.review.fixed ? pill('fixed', 'FIXED') : ''}${item.review.review_confidence ? pill('confidence', `Confidence: ${item.review.review_confidence}`) : ''}${item.review.security_impact ? pill('security', `Security: ${item.review.security_impact}`) : ''}${item.review.reported_phase ? pill('phase', item.review.reported_phase) : ''}${item.review.static_tags.map(tag => pill('tag', `Static: ${tag}`)).join('')}${item.review.llm_tags.map(tag => pill('tag', `LLM: ${tag}`)).join('')}${item.review.security_tags.map(tag => pill('tag', `Security: ${tag}`)).join('')}</span></button>`;
}
function renderBugList(items) {
  if (!items.length) return '<p class="error">No bugs match these filters.</p>';
  if (state.groupBy !== 'type') return items.map(renderBugItem).join('');
  const groups = new Map();
  for (const item of items) { const key = item.type || 'unknown'; if (!groups.has(key)) groups.set(key, []); groups.get(key).push(item); }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([type, grouped]) => `<section class="bug-group"><h3>${esc(type)} <span>${grouped.length}</span></h3>${grouped.map(renderBugItem).join('')}</section>`).join('');
}
async function loadList() {
  connection('Loading…');
  try {
    const data = await request(`/api/bugs?${query()}`);
    state.pages = data.pages; state.total = data.total;
    $('#total').textContent = `${data.total} shown`;
    $('#page-info').textContent = `Page ${data.page} / ${data.pages}`;
    $('#prev').disabled = data.page <= 1; $('#next').disabled = data.page >= data.pages;
    $('#list').innerHTML = renderBugList(data.items);
    connection('Connected', 'ok');
  } catch (error) { connection('Unavailable', 'error'); $('#list').innerHTML = `<p class="error">${esc(error.message)}</p>`; }
}
async function selectBug(id) {
  state.selected = Number(id); $('#detail').innerHTML = '<div class="empty"><p>Loading bug…</p></div>'; await loadList();
  try {
    const { bug, report, review, references } = await request(`/api/bugs/${id}`);
    state.staticTags = [...review.static_tags]; state.llmTags = [...review.llm_tags]; state.securityTags = [...review.security_tags];
    const sourceCards = references.length ? references.map(ref => `<article class="card source-card"><h3>${esc(ref.function)} <span class="source-path">${esc(ref.file)}:${ref.start_line || ref.line}${ref.end_line ? `–${ref.end_line}` : ''}</span></h3><div class="content"><p class="muted">${esc((ref.roles || [ref.role]).join(' · '))}${ref.call_targets?.length ? ` · calls: ${esc(ref.call_targets.join(', '))}` : ''}${ref.knowledge?.summary ? ` · Knowledge: ${esc(ref.knowledge.summary)}` : ''}</p>${ref.message ? `<p class="source-message">${esc(ref.message)}</p>` : ''}${ref.available ? `<pre class="mono source">${renderSource(ref)}</pre>` : ''}</div></article>`).join('') : '<article class="card"><h3>Related source code</h3><div class="content"><p class="muted">No source locations could be extracted from this task.</p></div></article>';
    const reportName = report ? ` · ${esc(report.filename)}` : '';
    const reportAnalysis = report ? `<pre class="mono">${esc(report.analysis)}</pre>` : '<p class="muted">No agent verification report is available for this static-analysis bug yet.</p>';
    $('#detail').innerHTML = `<div class="detail-header"><div><p class="eyebrow">BUG #${bug.id} · ${esc(bug.type)}</p><h2>${esc(bug.title)}</h2><p class="muted">Agent result: ${agentResultPill(report?.verified)}${reportName}${review.report_link ? ` · <a class="report-link" href="${esc(review.report_link)}" target="_blank" rel="noopener noreferrer">Open report</a>` : ''}</p></div></div><div class="sections"><div><article class="card"><h3>Original bug detail</h3><div class="content"><pre class="mono">${esc(bug.description)}</pre></div></article><article class="card" style="margin-top:1rem"><h3>Agent verification analysis</h3><div class="content analysis">${reportAnalysis}</div></article></div><article class="card"><h3>Manual review</h3><div class="content"><p class="muted">Use separate, self-defined reason tags for each phase. They are saved locally in <code>data/review-labels.json</code>.</p><section class="phase-box"><h4>Reported phase</h4><div class="review-options phase-options">${reportedPhases.map(phase => `<label><input type="radio" name="reported-phase" value="${phase}" ${review.reported_phase === phase ? 'checked' : ''}>${phase}</label>`).join('')}</div><label>Bug report link<input id="report-link" type="url" placeholder="https://…" value="${esc(review.report_link)}"></label></section><div class="review-options">${Object.keys(labelName).map(key => `<label><input type="radio" name="review" value="${key}" ${review.label === key ? 'checked' : ''}>${labelName[key]}</label>`).join('')}</div><label class="fixed-toggle"><input id="is-fixed" type="checkbox" ${review.fixed ? 'checked' : ''}>Bug has been fixed</label><section class="phase-box"><h4>Static phase — false-positive reason tags</h4><p class="muted">Tag why the static analysis candidate is a false positive.</p><div class="tag-editor"><input id="static-tag-input" type="text" placeholder="Type tag(s), separated by commas"><button id="add-static-tag" class="secondary" type="button">Add</button></div><div id="static-tags" class="tags"></div></section><section class="phase-box"><h4>LLM phase — false-negative reason tags</h4><p class="muted">Tag why LLM verification missed a real bug.</p><div class="tag-editor"><input id="llm-tag-input" type="text" placeholder="Type tag(s), separated by commas"><button id="add-llm-tag" class="secondary" type="button">Add</button></div><div id="llm-tags" class="tags"></div></section><label>Review note<textarea id="note" rows="6" placeholder="Other review notes">${esc(review.note)}</textarea></label><div class="review-actions"><button id="save">Save review</button><span id="save-state" class="save-state">${review.updated_at ? `Last saved ${new Date(review.updated_at).toLocaleString()}` : 'Not saved yet'}</span></div></div></article></div><section class="source-section"><h2>Related source code</h2><p class="muted">Function definitions are resolved from the local Linux source tree. Available Knowledge documentation is shown with each function.</p>${sourceCards}</section>`;
    // Preserve a true three-column work surface: results | details and source | review.
    const middleColumn = $('.sections > div:first-child');
    middleColumn.classList.add('middle-column');
    middleColumn.append($('.source-section'));
    $('.sections > article.card').classList.add('manual-column');
    // Keep reporting state adjacent to the fix state in the right review column.
    const manualColumn = $('.manual-column');
    const reportPhaseBox = manualColumn?.querySelector('.phase-box');
    if (reportPhaseBox) $('.fixed-toggle')?.after(reportPhaseBox);
    $('.fixed-toggle')?.insertAdjacentHTML('afterend', `<label class="confidence-toggle">Review confidence<select id="review-confidence"><option value="">Not set</option>${['Low', 'Medium', 'High'].map(level => `<option value="${level}" ${review.review_confidence === level ? 'selected' : ''}>${level}</option>`).join('')}</select></label>`);
    reportPhaseBox?.insertAdjacentHTML('afterend', `<section class="phase-box security-box"><h4>Security assessment</h4><label>Security impact<select id="security-impact"><option value="">Not set</option>${['Low', 'Medium', 'High'].map(level => `<option value="${level}" ${review.security_impact === level ? 'selected' : ''}>${level}</option>`).join('')}</select></label><p class="muted">Add reusable tags for the potential security impact.</p><div class="tag-editor"><input id="security-tag-input" list="known-security-tags" type="text" placeholder="Type or reuse tag(s), separated by commas"><button id="add-security-tag" class="secondary" type="button">Add</button></div><div id="security-tags" class="tags"></div></section>`);
    $('#static-tag-input').setAttribute('list', 'known-static-tags');
    $('#llm-tag-input').setAttribute('list', 'known-llm-tags');
    $('#save')?.addEventListener('click', saveReview);
    for (const phase of ['static', 'llm', 'security']) {
      const addButton = $(`#add-${phase}-tag`), input = $(`#${phase}-tag-input`), tags = $(`#${phase}-tags`);
      addButton?.addEventListener('click', () => addTags(phase));
      input?.addEventListener('keydown', (event) => { if (event.key === 'Enter') { event.preventDefault(); addTags(phase); } });
      tags?.addEventListener('click', (event) => { const button = event.target.closest('[data-tag]'); if (button) { const key = tagStateKey(phase); state[key] = state[key].filter(tag => tag !== button.dataset.tag); renderTags(phase); } });
      if (tags) renderTags(phase);
    }
  } catch (error) { $('#detail').innerHTML = `<p class="error">${esc(error.message)}</p>`; }
}
async function saveReview() {
  const label = document.querySelector('input[name="review"]:checked').value; const fixed = $('#is-fixed').checked; const reported_phase = document.querySelector('input[name="reported-phase"]:checked')?.value || null; const report_link = $('#report-link').value; const review_confidence = $('#review-confidence')?.value || null; const security_impact = $('#security-impact')?.value || null; const note = $('#note').value; const status = $('#save-state');
  try { $('#save').disabled = true; status.textContent = 'Saving…'; const data = await request(`/api/bugs/${state.selected}/review`, { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({label, fixed, reported_phase, report_link, review_confidence, security_impact, static_tags: state.staticTags, llm_tags: state.llmTags, security_tags: state.securityTags, note}) }); status.textContent = `Saved ${new Date(data.review.updated_at).toLocaleString()}`; status.className = 'save-state saved'; await Promise.all([loadStats(), loadList(), loadKnownTags()]); }
  catch (error) { status.textContent = error.message; status.className = 'save-state error'; }
  finally { $('#save').disabled = false; }
}
function addTags(phase) {
  const input = $(`#${phase}-tag-input`), key = tagStateKey(phase);
  for (const tag of input.value.split(',')) { const clean = tag.trim().replace(/\s+/g, ' ').slice(0, 64); if (clean && !state[key].includes(clean) && state[key].length < 30) state[key].push(clean); }
  input.value = ''; renderTags(phase);
}
function tagStateKey(phase) { return phase === 'static' ? 'staticTags' : phase === 'llm' ? 'llmTags' : 'securityTags'; }
function renderTags(phase) { const key = tagStateKey(phase); $(`#${phase}-tags`).innerHTML = state[key].length ? state[key].map(tag => `<button type="button" class="tag-chip" data-tag="${esc(tag)}">${esc(tag)} <span>×</span></button>`).join('') : '<span class="muted">No tags yet.</span>'; }
function resetPage() { state.page = 1; loadList(); }
$('#list')?.addEventListener('click', (event) => { const item = event.target.closest('[data-id]'); if (item) selectBug(item.dataset.id); });
$('#prev')?.addEventListener('click', () => { state.page--; loadList(); }); $('#next')?.addEventListener('click', () => { state.page++; loadList(); });
$('#verified')?.addEventListener('change', resetPage); $('#label')?.addEventListener('change', resetPage); $('#fixed')?.addEventListener('change', resetPage); $('#reported-phase-filter')?.addEventListener('change', resetPage);
$('#type-options')?.addEventListener('change', (event) => { const input = event.target.closest('input[type="checkbox"]'); if (!input) return; if (state.selectedTypes === null) state.selectedTypes = state.typeOptions.map((item) => item.type); const selected = new Set(state.selectedTypes); input.checked ? selected.add(input.value) : selected.delete(input.value); state.selectedTypes = [...selected]; saveTypeFilter(); state.page = 1; renderTypeOptions(); loadList(); });
$('#type-select-all')?.addEventListener('click', () => { state.selectedTypes = null; saveTypeFilter(); state.page = 1; renderTypeOptions(); loadList(); });
$('#type-clear')?.addEventListener('click', () => { state.selectedTypes = null; saveTypeFilter(); state.page = 1; renderTypeOptions(); loadList(); });
$('#group-by')?.addEventListener('change', () => { state.groupBy = $('#group-by').value; localStorage.setItem('bugconfirm.groupBy', state.groupBy); loadList(); });
$('#page-size')?.addEventListener('change', () => { state.pageSize = Number($('#page-size').value); state.page = 1; localStorage.setItem('bugconfirm.pageSize', String(state.pageSize)); loadList(); });
$('#search')?.addEventListener('input', () => { clearTimeout(state.timers); state.timers = setTimeout(resetPage, 220); });
$('#tag-filter')?.addEventListener('input', () => { clearTimeout(state.timers); state.timers = setTimeout(resetPage, 220); });
$('#reload')?.addEventListener('click', async () => { try { await request('/api/reload', {method:'POST'}); await Promise.all([loadStats(), loadList(), loadKnownTags(), loadBugTypes()]); connection('Source reloaded', 'ok'); } catch (error) { connection(error.message, 'error'); } });
$('#group-by').value = state.groupBy;
$('#page-size').value = String(state.pageSize);
Promise.all([loadStats(), loadList(), loadKnownTags(), loadBugTypes()]).catch(() => {});
