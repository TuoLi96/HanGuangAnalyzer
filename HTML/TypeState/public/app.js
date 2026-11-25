const state = {
  status: 'all',
  query: '',
  tsFilter: 'all',
  page: 1,
  items: [],
  selected: null,
  patch: null,
  typestate: null,
  dirtyPatch: false,
  dirtyTs: false,
  suppressInput: false
};

const $ = (id) => document.getElementById(id);
const statusLabels = { pending: '待审核', correct: '正确', wrong: '错误', reviewed: '已审核', modified: '已修改' };
const els = {
  search: $('searchInput'), typeFilter: $('typestateFilter'), statusNav: $('statusNav'), patchList: null,
  empty: $('emptyState'), detail: $('detailView'), headingCommit: $('headingCommit'), headingTitle: $('headingTitle'),
  headingFile: $('headingFile'), headingFunction: $('headingFunction'), status: $('statusSelect'), reviewNote: $('reviewNote'),
  description: $('descriptionInput'), diff: $('diffInput'), file: $('fileInput'), func: $('functionInput'), bad: $('badVersionInput'),
  mid: $('midVersionInput'), good: $('goodVersionInput'), midPosition: $('midPositionInput'), bugType: $('bugTypeInput'),
  fixes: $('fixesInput'), before: $('beforeCodeInput'), midCode: $('midCodeInput'), after: $('afterCodeInput'), ts: $('tsInput'),
  jsonStatus: $('jsonStatus'), graph: $('graphCanvas'), toast: $('toast'),
};

function makePatchList() {
  if (!els.patchList) els.patchList = document.createElement('div');
}

function showToast(message, kind = '') {
  els.toast.textContent = message;
  els.toast.className = `toast show ${kind}`;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { els.toast.className = 'toast'; }, 2800);
}

async function api(url, options = {}) {
  const response = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `请求失败 (${response.status})`);
  return data;
}

function setCount(id, value) { $(id).textContent = Number(value).toLocaleString('zh-CN'); }

async function loadStats() {
  const stats = await api('/api/stats');
  setCount('countAll', stats.total); setCount('countPending', stats.pending); setCount('countCorrect', stats.correct);
  setCount('countWrong', stats.wrong); setCount('countReviewed', stats.reviewed); setCount('countModified', stats.modified);
  $('datasetCount').textContent = Number(stats.total).toLocaleString('zh-CN');
}

function renderPatchList(data) {
  const host = document.querySelector('.sidebar .patch-list') || (() => {
    const node = document.createElement('div'); node.className = 'patch-list';
    document.querySelector('.status-nav').after(node); return node;
  })();
  host.innerHTML = '';
  if (!data.items.length) { host.innerHTML = '<div class="list-empty">没有符合条件的 patch</div>'; return; }
  for (const item of data.items) {
    const button = document.createElement('button');
    button.type = 'button'; button.className = `patch-row ${state.selected === item.commit ? 'active' : ''}`;
    button.dataset.commit = item.commit;
    const title = document.createElement('div'); title.className = 'patch-row-title'; title.textContent = item.title;
    const meta = document.createElement('div'); meta.className = 'patch-row-meta'; meta.textContent = `${item.commit.slice(0, 12)}  ·  ${item.file || '未指定文件'}`;
    const foot = document.createElement('div'); foot.className = 'patch-row-foot';
    const status = document.createElement('span'); status.className = `row-status ${item.status}`; status.textContent = item.status_label;
    const ts = document.createElement('span'); ts.className = `ts-presence ${item.has_typestate ? '' : 'missing'}`; ts.textContent = item.has_typestate ? '● TS' : '○ 无 TS';
    foot.append(status, ts); button.append(title, meta, foot); button.addEventListener('click', () => selectPatch(item.commit)); host.append(button);
  }
  state.items = data.items;
}

async function loadList() {
  const host = document.querySelector('.sidebar .patch-list');
  if (host) host.innerHTML = '<div class="list-loading">正在载入 patch…</div>';
  const params = new URLSearchParams({ q: state.query, status: state.status, typestate: state.tsFilter, page: state.page, pageSize: 2500 });
  try { renderPatchList(await api(`/api/patches?${params}`)); }
  catch (error) { if (host) host.innerHTML = `<div class="list-empty">${escapeHtml(error.message)}</div>`; }
}

function escapeHtml(text) { return String(text).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char])); }

function setValue(element, value) { element.value = value == null ? '' : String(value); }
function lines(value) { return String(value || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean); }

function renderDetail() {
  const p = state.patch;
  if (!p) return;
  els.empty.classList.add('hidden'); els.detail.classList.remove('hidden');
  els.headingCommit.textContent = p.commit;
  els.headingTitle.textContent = String(p.description || '').split(/\r?\n/, 1)[0] || '无标题 patch';
  els.headingFile.textContent = p.file || '未指定文件'; els.headingFunction.textContent = p.function || '未指定函数';
  els.status.value = p.review_status || 'pending'; setValue(els.reviewNote, p.review_note);
  setValue(els.description, p.description); setValue(els.diff, p.diff); setValue(els.file, p.file); setValue(els.func, p.function);
  setValue(els.bad, p.bad_version); setValue(els.mid, p.mid_version); setValue(els.good, p.good_version); setValue(els.midPosition, p.mid_position);
  setValue(els.bugType, (p.bug_type || []).join('\n')); setValue(els.fixes, (p.fixes || []).join('\n'));
  setValue(els.before, p.before_code); setValue(els.midCode, p.mid_code); setValue(els.after, p.after_code);
  $('badVersion').textContent = p.bad_version || '—'; $('midVersion').textContent = `中间版本 ${p.mid_version || '—'}`; $('goodVersion').textContent = p.good_version || '—';
  $('bugTypes').innerHTML = (p.bug_type || []).length ? p.bug_type.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join('') : '<span class="tag-empty">未标注</span>';
  const hasTs = state.typestate && typeof state.typestate === 'object'; $('tsSummary').textContent = hasTs ? `${(state.typestate.state || []).length} 个状态` : '尚未抽取'; $('tsSummaryNote').textContent = hasTs ? `${(state.typestate.transition || []).length} 条转移` : '可在此新建';
  state.suppressInput = true; setValue(els.ts, state.typestate ? JSON.stringify(state.typestate, null, 2) : ''); state.suppressInput = false;
  els.ts.disabled = false; $('tsEditHint').textContent = state.typestate ? 'JSON 可编辑' : '尚未抽取';
  updateJsonAndGraph(false); updateListActive();
}

function updateListActive() { document.querySelectorAll('.patch-row').forEach((row) => row.classList.toggle('active', row.dataset.commit === state.selected)); }

async function selectPatch(commit) {
  if (state.selected && (state.dirtyPatch || state.dirtyTs)) {
    if (!window.confirm('当前 patch 有未同步的修改，切换前放弃这些修改吗？')) return;
  }
  try {
    const data = await api(`/api/patches/${commit}`); state.selected = commit; state.patch = data.patch; state.typestate = data.typestate; state.dirtyPatch = false; state.dirtyTs = false; renderDetail();
  } catch (error) { showToast(error.message, 'error'); }
}

function collectPatch() {
  return {
    description: els.description.value, diff: els.diff.value, file: els.file.value, function: els.func.value,
    bad_version: els.bad.value, mid_version: els.mid.value, good_version: els.good.value, mid_position: els.midPosition.value,
    bug_type: lines(els.bugType.value), fixes: lines(els.fixes.value), before_code: els.before.value, mid_code: els.midCode.value,
    after_code: els.after.value, review_status: els.status.value, review_note: els.reviewNote.value
  };
}

function parseTs() {
  const raw = els.ts.value.trim();
  if (!raw) return null;
  try { const value = JSON.parse(raw); if (!value || Array.isArray(value) || typeof value !== 'object') throw new Error('根节点必须是 JSON 对象'); return value; }
  catch (error) { return { __error: error.message }; }
}

function updateJsonAndGraph(markDirty = true) {
  if (state.suppressInput) return;
  const parsed = parseTs();
  if (parsed && parsed.__error) { els.jsonStatus.textContent = `JSON 错误：${parsed.__error}`; els.jsonStatus.className = 'json-status error'; els.graph.innerHTML = '<div class="graph-placeholder">JSON 尚未闭合或格式有误<br />修正后状态图会自动更新</div>'; return; }
  els.jsonStatus.textContent = parsed ? 'JSON 格式有效 · 状态图已更新' : '当前没有 typestate · 可点击“新建”'; els.jsonStatus.className = 'json-status';
  if (markDirty) state.dirtyTs = true; renderGraph(parsed);
}

function svgElement(name, attrs = {}) { const node = document.createElementNS('http://www.w3.org/2000/svg', name); Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value)); return node; }

function renderGraph(ts) {
  if (!ts) { els.graph.innerHTML = '<div class="graph-placeholder">当前 patch 没有 typestate<br />点击右上角“新建”开始编辑</div>'; return; }
  const states = Array.isArray(ts.state) ? [...ts.state] : []; const transitions = Array.isArray(ts.transition) ? ts.transition : [];
  if (!states.length) { els.graph.innerHTML = '<div class="graph-placeholder">typestate 中没有 state 字段<br />先在 JSON 中定义状态</div>'; return; }
  const allStates = [...states]; transitions.forEach((edge) => { if (edge.curr_state && !allStates.includes(edge.curr_state) && edge.curr_state !== 'Any') allStates.push(edge.curr_state); if (edge.next_state && !allStates.includes(edge.next_state)) allStates.push(edge.next_state); });
  const cols = Math.max(1, Math.ceil(Math.sqrt(allStates.length * 1.35))); const rows = Math.ceil(allStates.length / cols); const width = Math.max(620, cols * 165 + 30); const height = Math.max(260, rows * 90 + 45);
  const positions = new Map(); allStates.forEach((name, index) => { const col = index % cols; const row = Math.floor(index / cols); positions.set(name, { x: 80 + col * ((width - 130) / Math.max(1, cols - 1)), y: 55 + row * 80 }); });
  const svg = svgElement('svg', { class: 'graph-svg', viewBox: `0 0 ${width} ${height}`, preserveAspectRatio: 'xMidYMid meet' });
  const defs = svgElement('defs'); const marker = svgElement('marker', { id: 'arrow', markerWidth: 7, markerHeight: 7, refX: 6, refY: 3.5, orient: 'auto', markerUnits: 'strokeWidth' }); marker.append(svgElement('path', { d: 'M0,0 L7,3.5 L0,7 z', fill: '#91aeb5' })); defs.append(marker); svg.append(defs);
  const bugState = ts.bug && ts.bug.bug_state; const edges = transitions.filter((edge) => edge.next_state && (edge.curr_state === 'Any' || positions.has(edge.curr_state)) && positions.has(edge.next_state));
  edges.forEach((edge, index) => { const from = edge.curr_state === 'Any' ? { x: 20, y: positions.get(edge.next_state).y } : positions.get(edge.curr_state); const to = positions.get(edge.next_state); const same = edge.curr_state === edge.next_state; let path;
    if (same) path = svgElement('path', { d: `M ${from.x + 27} ${from.y - 12} C ${from.x + 80} ${from.y - 55}, ${from.x + 80} ${from.y - 55}, ${from.x + 27} ${from.y - 12}`, fill: 'none', stroke: '#9ab0b5', 'stroke-width': 1.3, 'marker-end': 'url(#arrow)' });
    else path = svgElement('path', { d: `M ${from.x} ${from.y} C ${(from.x + to.x) / 2} ${from.y}, ${(from.x + to.x) / 2} ${to.y}, ${to.x - 36} ${to.y}`, fill: 'none', stroke: '#a4b7bb', 'stroke-width': 1.35, 'marker-end': 'url(#arrow)' });
    svg.append(path); const label = String(edge.act || ''); const lx = same ? from.x + 51 : (from.x + to.x) / 2; const ly = same ? from.y - 47 : (from.y + to.y) / 2 - 4; const group = svgElement('g'); const bg = svgElement('rect', { x: lx - Math.max(18, label.length * 3.3) - 5, y: ly - 10, width: Math.max(36, label.length * 6.6 + 10), height: 18, rx: 5, fill: '#fff', stroke: '#dce6e7' }); const text = svgElement('text', { x: lx, y: ly + 3, 'text-anchor': 'middle', fill: '#6b8187', 'font-size': '9', 'font-family': 'DM Mono, monospace' }); text.textContent = label; group.append(bg, text); svg.append(group);
  });
  allStates.forEach((name, index) => { const point = positions.get(name); const isBug = name === bugState; const isStart = index === 0 || name === states[0]; const group = svgElement('g'); const rect = svgElement('rect', { x: point.x - 36, y: point.y - 17, width: 72, height: 34, rx: 8, fill: isBug ? '#fff0ef' : isStart ? '#eaf4f5' : '#fff', stroke: isBug ? '#d98680' : isStart ? '#79aeb7' : '#c5d5d8', 'stroke-width': isBug || isStart ? 1.7 : 1.2 }); const text = svgElement('text', { x: point.x, y: point.y + 4, 'text-anchor': 'middle', fill: isBug ? '#b44e4b' : '#29434c', 'font-size': '10', 'font-family': 'Manrope, Noto Sans SC, sans-serif', 'font-weight': isBug || isStart ? '700' : '500' }); text.textContent = String(name); group.append(rect, text); if (isStart) { const start = svgElement('circle', { cx: point.x - 29, cy: point.y - 11, r: 3, fill: '#3c8290' }); group.append(start); } svg.append(group); });
  els.graph.innerHTML = ''; els.graph.append(svg);
}

async function saveAll() {
  if (!state.selected) return;
  try {
    const patch = collectPatch(); const parsed = parseTs(); if (parsed && parsed.__error) { showToast('请先修正 typestate JSON', 'error'); return; }
    const patchResult = await api(`/api/patches/${state.selected}`, { method: 'PUT', body: JSON.stringify({ patch }) });
    const tsResult = await api(`/api/typestates/${state.selected}`, { method: 'PUT', body: JSON.stringify({ typestate: parsed }) });
    state.patch = patchResult.patch; state.typestate = tsResult.typestate; state.dirtyPatch = false; state.dirtyTs = false; renderDetail(); await loadStats(); await loadList(); showToast('已同步到本地文件', 'success');
  } catch (error) { showToast(error.message, 'error'); }
}

function markPatchDirty() { if (!state.suppressInput) state.dirtyPatch = true; }
function debounce(fn, delay) { let timer; return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); }; }

document.addEventListener('DOMContentLoaded', async () => {
  makePatchList();
  document.querySelectorAll('.status-filter').forEach((button) => button.addEventListener('click', () => { document.querySelectorAll('.status-filter').forEach((item) => item.classList.remove('active')); button.classList.add('active'); state.status = button.dataset.status; state.page = 1; loadList(); }));
  els.search.addEventListener('input', debounce(() => { state.query = els.search.value; state.page = 1; loadList(); }, 180));
  els.typeFilter.addEventListener('change', () => { state.tsFilter = els.typeFilter.value; state.page = 1; loadList(); });
  document.querySelectorAll('.patch-panel input, .patch-panel textarea, #reviewNote').forEach((element) => element.addEventListener('input', markPatchDirty));
  els.status.addEventListener('change', markPatchDirty); els.ts.addEventListener('input', () => updateJsonAndGraph(true)); $('saveAllButton').addEventListener('click', saveAll);
  $('newTsButton').addEventListener('click', () => { if (!state.selected) return; state.suppressInput = true; els.ts.value = JSON.stringify({ state: ['Init', 'Bug'], action: {}, transition: [], bug: { name: '', tbl: '', key_actions: [], bug_state: 'Bug' }, sliced_action: [], context: { start_action: '', end_action: '' } }, null, 2); state.suppressInput = false; updateJsonAndGraph(true); els.ts.focus(); });
  $('copyCommitButton').addEventListener('click', async () => { if (!state.selected) return; await navigator.clipboard.writeText(state.selected); showToast('commit 已复制', 'success'); });
  document.addEventListener('keydown', (event) => { if (event.key === '/' && document.activeElement !== els.search && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) { event.preventDefault(); els.search.focus(); } if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); saveAll(); } });
  try { await loadStats(); await loadList(); } catch (error) { showToast(error.message, 'error'); }
});
