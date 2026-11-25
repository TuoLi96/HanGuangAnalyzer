const http = require('http');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

// Reuse the workspace-wide path variables used by the other HanGuang modules.
const ROOT = __dirname;
const DEFAULT_WORK_ROOT = path.resolve(ROOT, '../../workdir');
const configuredWorkRoot = process.env.HG_WORK_ROOT && path.resolve(process.env.HG_WORK_ROOT);
// A shell can retain HG_* values from another checkout.  Only use that shared
// location when it contains this dataset; otherwise keep the local workspace
// usable and create its review store there.
const WORK_ROOT = configuredWorkRoot && fs.existsSync(path.join(configuredWorkRoot, 'AgentTasks/TypeState/tasks.jsonl'))
  ? configuredWorkRoot
  : DEFAULT_WORK_ROOT;
const configuredSourceRoot = process.env.HG_CHECKED_SRC && path.resolve(process.env.HG_CHECKED_SRC);
const SOURCE = {
  tasksFile: path.join(WORK_ROOT, 'AgentTasks/TypeState/tasks.jsonl'),
  resultDir: path.join(WORK_ROOT, 'AgentTasks/TypeState/Result'),
  sourceRoot: configuredSourceRoot && fs.existsSync(configuredSourceRoot) ? configuredSourceRoot : path.join(WORK_ROOT, 'linux'),
  knowledgeFile: path.join(WORK_ROOT, 'database/Knowledge/doc.json')
};
const PUBLIC_DIR = path.join(ROOT, 'public');
// Reviews belong to the shared work directory.  This lets a container and the
// host use the same persistent store without Docker creating it on their behalf.
const DATA_DIR = path.join(WORK_ROOT, 'HTML/BugConfirm/data');
const LABELS_FILE = path.join(DATA_DIR, 'review-labels.json');
const LEGACY_LABELS_FILE = path.join(ROOT, 'data/review-labels.json');
const HOST = process.env.HG_BUGCONFIRM_HOST || '127.0.0.1';
const PORT = Number(process.env.HG_BUGCONFIRM_PORT || 8786);
const VALID_LABELS = new Set(['unreviewed', 'real', 'not_real', 'unsure']);
const REPORTED_PHASES = new Set(['Not Reported', 'Reported', 'Submitted', 'Confirmed', 'Accepted']);
const REVIEW_LEVELS = new Set(['Low', 'Medium', 'High']);

let bugs = new Map();
let reports = new Map();
let labels = {};
let knowledge = new Map();

function prepareReviewStore() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  // One-way, non-destructive migration of reviews created by earlier versions.
  if (!fs.existsSync(LABELS_FILE) && path.resolve(LEGACY_LABELS_FILE) !== path.resolve(LABELS_FILE) && fs.existsSync(LEGACY_LABELS_FILE)) {
    fs.copyFileSync(LEGACY_LABELS_FILE, LABELS_FILE);
    console.log(`Migrated existing reviews to ${LABELS_FILE}`);
  }
}

function readJsonLines(file) {
  return fs.readFileSync(file, 'utf8').split(/\r?\n/).filter(Boolean).map((line, index) => {
    try { return JSON.parse(line); }
    catch (error) { throw new Error(`Cannot parse ${path.basename(file)} line ${index + 1}: ${error.message}`); }
  });
}

function idFromTask(task, index) {
  const match = String(task.desp || '').match(/\bID-(\d+)\b/);
  return match ? Number(match[1]) : index + 1;
}

function titleFromTask(task) {
  const lines = String(task.desp || '').split(/\r?\n/).filter(Boolean);
  return lines[0] || `Bug ${task.id}`;
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function textFromKnowledge(value) {
  return String(value || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
}

function loadKnowledge() {
  knowledge = new Map();
  try {
    const entries = JSON.parse(fs.readFileSync(SOURCE.knowledgeFile, 'utf8'));
    if (!Array.isArray(entries)) return;
    for (const entry of entries) {
      if (!entry || typeof entry.name !== 'string' || knowledge.has(entry.name)) continue;
      knowledge.set(entry.name, { class: String(entry.class || 'symbol'), summary: textFromKnowledge(entry.summary), content: textFromKnowledge(entry.content) });
    }
  } catch (error) {
    if (error.code !== 'ENOENT') console.warn(`Knowledge documentation could not be loaded: ${error.message}`);
  }
}

// The task text contains locations in several forms. Add new analyzer formats here.
function sourceReferences(description) {
  const found = new Map();
  const add = (file, line, functionName, role) => {
    if (!file || !functionName || !/^[A-Za-z0-9_./+-]+\.[ch]$/.test(file)) return;
    const key = `${file}:${line}:${functionName}`;
    if (!found.has(key)) found.set(key, { file, line: Number(line), function: functionName, role, highlight_line: Number(line) });
  };
  const text = String(description || '');
  for (const match of text.matchAll(/([A-Za-z0-9_./+-]+\.[ch]):(\d+)\s+in function\s+([A-Za-z_][A-Za-z0-9_]*)/g)) add(match[1], match[2], match[3], 'reported location');
  for (const match of text.matchAll(/Call\s+([A-Za-z_][A-Za-z0-9_]*)\s+at\s+([A-Za-z0-9_./+-]+\.[ch]):(\d+)/g)) add(match[2], match[3], match[1], 'call chain');
  return [...found.values()];
}

function functionDefinitions(lines) {
  const ignored = new Set(['if', 'for', 'while', 'switch', 'return', 'sizeof']);
  const definitions = [];
  for (let start = 0; start < lines.length; start++) {
    const match = lines[start].match(/\b([A-Za-z_][A-Za-z0-9_]*)\s*\(/);
    if (!match || ignored.has(match[1])) continue;
    let open = -1, semicolon = -1;
    for (let probe = start; probe < Math.min(lines.length, start + 24); probe++) {
      if (lines[probe].includes('{')) { open = probe; break; }
      if (lines[probe].includes(';')) { semicolon = probe; break; }
    }
    if (open < 0 || semicolon >= 0) continue;
    let depth = 0, end = -1;
    for (let index = open; index < Math.min(lines.length, open + 1200); index++) {
      for (const char of lines[index]) { if (char === '{') depth++; if (char === '}') depth--; }
      if (depth === 0) { end = index; break; }
    }
    if (end >= 0) definitions.push({ name: match[1], start, end });
  }
  return definitions;
}

function mergeSourceSnippets(snippets) {
  const merged = new Map();
  for (const snippet of snippets) {
    const key = snippet.available ? `${snippet.file}\u0000${snippet.start_line}\u0000${snippet.end_line}\u0000${snippet.source}` : `${snippet.file}\u0000${snippet.line}\u0000${snippet.function}`;
    const existing = merged.get(key);
    if (!existing) {
      merged.set(key, { ...snippet, roles: [snippet.role], highlight_lines: [snippet.highlight_line].filter(Boolean), call_targets: snippet.call_target ? [snippet.call_target] : [] });
      continue;
    }
    if (!existing.roles.includes(snippet.role)) existing.roles.push(snippet.role);
    if (snippet.highlight_line && !existing.highlight_lines.includes(snippet.highlight_line)) existing.highlight_lines.push(snippet.highlight_line);
    if (snippet.call_target && !existing.call_targets.includes(snippet.call_target)) existing.call_targets.push(snippet.call_target);
  }
  return [...merged.values()];
}

function sourceSnippet(reference) {
  const root = `${SOURCE.sourceRoot}${path.sep}`;
  const file = path.resolve(SOURCE.sourceRoot, reference.file);
  const base = { ...reference, available: false, source: '', start_line: null, end_line: null };
  if (!file.startsWith(root) || !fs.existsSync(file)) return { ...base, message: 'Source file is unavailable in the configured source tree.' };
  const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/);
  const target = Math.max(0, Math.min(lines.length - 1, reference.line - 1));
  const definitions = functionDefinitions(lines);
  let definition;
  if (reference.role === 'call chain') {
    definition = definitions.filter((item) => item.start <= target && item.end >= target).sort((a, b) => b.start - a.start)[0];
  } else {
    const named = definitions.filter((item) => item.name === reference.function);
    definition = named.reduce((best, item) => !best || Math.abs(item.start - target) < Math.abs(best.start - target) ? item : best, null);
  }
  if (!definition) {
    const excerptStart = Math.max(0, target - 20), excerptEnd = Math.min(lines.length - 1, target + 20);
    return { ...base, knowledge: knowledge.get(reference.function) || null, available: true, source: lines.slice(excerptStart, excerptEnd + 1).join('\n'), start_line: excerptStart + 1, end_line: excerptEnd + 1, message: 'Function boundary was not found; showing lines around the reported location.' };
  }
  const callTarget = reference.role === 'call chain' ? reference.function : null;
  return { ...base, function: definition.name, call_target: callTarget, knowledge: knowledge.get(definition.name) || null, available: true, source: lines.slice(definition.start, definition.end + 1).join('\n'), start_line: definition.start + 1, end_line: definition.end + 1, message: null };
}

function loadData() {
  bugs = new Map();
  for (const [index, task] of readJsonLines(SOURCE.tasksFile).entries()) {
    const id = idFromTask(task, index);
    bugs.set(id, { id, type: task.type || 'unknown', description: task.desp || '', title: titleFromTask(task) });
  }
  reports = new Map();
  for (const name of fs.readdirSync(SOURCE.resultDir)) {
    const match = name.match(/^(\d+)_(True|False)\.md$/);
    if (!match) continue;
    const id = Number(match[1]);
    reports.set(id, {
      id,
      verified: match[2] === 'True',
      filename: name,
      analysis: fs.readFileSync(path.join(SOURCE.resultDir, name), 'utf8')
    });
  }
  try {
    labels = JSON.parse(fs.readFileSync(LABELS_FILE, 'utf8'));
    if (!labels || typeof labels !== 'object' || Array.isArray(labels)) labels = {};
  } catch (error) {
    if (error.code === 'ENOENT') labels = {};
    else throw error;
  }
  loadKnowledge();
}

function saveLabels() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  const temp = `${LABELS_FILE}.tmp`;
  fs.writeFileSync(temp, `${JSON.stringify(labels, null, 2)}\n`, 'utf8');
  fs.renameSync(temp, LABELS_FILE);
}

function reviewFor(id) {
  const value = labels[String(id)] || {};
  return {
    label: VALID_LABELS.has(value.label) ? value.label : 'unreviewed',
    fixed: value.fixed === true,
    review_confidence: REVIEW_LEVELS.has(value.review_confidence) ? value.review_confidence : null,
    security_impact: REVIEW_LEVELS.has(value.security_impact) ? value.security_impact : null,
    security_tags: normalizeTags(value.security_tags),
    reported_phase: REPORTED_PHASES.has(value.reported_phase) ? value.reported_phase : null,
    report_link: normalizeReportLink(value.report_link),
    // Old generic tags are retained as static-phase tags for existing reviews.
    static_tags: normalizeTags(value.static_tags || value.tags),
    llm_tags: normalizeTags(value.llm_tags),
    note: String(value.note || ''),
    updated_at: value.updated_at || null
  };
}

function normalizeTags(tags) {
  if (!Array.isArray(tags)) return [];
  return [...new Set(tags.map((tag) => String(tag).trim().replace(/\s+/g, ' ').slice(0, 64)).filter(Boolean))].slice(0, 30);
}

function normalizeReportLink(value) {
  const link = String(value || '').trim().slice(0, 2000);
  if (!link) return '';
  try {
    const url = new URL(link);
    return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
  } catch { return ''; }
}

function summary(id) {
  const bug = bugs.get(id) || { id, type: 'unknown', title: `Bug ${id}`, description: '' };
  const report = reports.get(id);
  return { id, type: bug.type, title: bug.title, verified: report ? report.verified : null, filename: report ? report.filename : null, review: reviewFor(id) };
}

function stats() {
  const output = { total: bugs.size, verified: 0, verified_true: 0, verified_false: 0, real: 0, not_real: 0, unsure: 0, unreviewed: 0, fixed: 0, true_positive: 0, false_positive: 0, true_negative: 0, false_negative: 0 };
  for (const id of bugs.keys()) {
    const report = reports.get(id);
    if (report) {
      output.verified++;
      report.verified ? output.verified_true++ : output.verified_false++;
    }
    const review = reviewFor(id);
    output[review.label]++;
    if (review.fixed) output.fixed++;
    if (report && review.label === 'real') report.verified ? output.true_positive++ : output.false_negative++;
    if (report && review.label === 'not_real') report.verified ? output.false_positive++ : output.true_negative++;
  }
  const decided = output.real + output.not_real;
  output.reviewed = decided;
  output.false_positive_rate = output.false_positive + output.true_negative ? output.false_positive / (output.false_positive + output.true_negative) : null;
  output.false_negative_rate = output.false_negative + output.true_positive ? output.false_negative / (output.false_negative + output.true_positive) : null;
  output.original_positive_ratio = output.verified ? output.verified_true / output.verified : null;
  output.confirmed_real_ratio = decided ? output.real / decided : null;
  return output;
}

function knownTags(tagClass) {
  const fields = { static: 'static_tags', llm: 'llm_tags', security: 'security_tags' };
  const field = fields[tagClass];
  if (!field) return [];
  const counts = new Map();
  for (const id of bugs.keys()) {
    const review = reviewFor(id);
    for (const tag of review[field]) counts.set(tag, (counts.get(tag) || 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([tag, count]) => ({ tag, count }));
}

function sendJson(res, status, body) {
  const text = JSON.stringify(body);
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': Buffer.byteLength(text), 'Cache-Control': 'no-store' });
  res.end(text);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let raw = '';
    req.setEncoding('utf8');
    req.on('data', (chunk) => { raw += chunk; if (raw.length > 1024 * 1024) { reject(new Error('Request body is too large')); req.destroy(); } });
    req.on('end', () => { try { resolve(raw ? JSON.parse(raw) : {}); } catch (error) { reject(new Error(`Invalid JSON: ${error.message}`)); } });
    req.on('error', reject);
  });
}

async function api(req, res, url) {
  const parts = url.pathname.split('/').filter(Boolean);
  if (parts[1] === 'stats' && req.method === 'GET') return sendJson(res, 200, stats());
  if (parts[1] === 'tags' && req.method === 'GET') {
    const tagClass = url.searchParams.get('class') || '';
    if (!['static', 'llm', 'security'].includes(tagClass)) return sendJson(res, 400, { error: 'Tag class must be static, llm, or security' });
    return sendJson(res, 200, { items: knownTags(tagClass) });
  }
  if (parts[1] === 'bug-types' && req.method === 'GET') {
    const counts = new Map();
    for (const id of bugs.keys()) {
      const type = String((bugs.get(id) || {}).type || 'unknown');
      counts.set(type, (counts.get(type) || 0) + 1);
    }
    return sendJson(res, 200, { items: [...counts.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([type, count]) => ({ type, count })) });
  }
  if (parts[1] === 'reload' && req.method === 'POST') { loadData(); return sendJson(res, 200, { ok: true, stats: stats() }); }
  if (parts[1] === 'bugs' && parts.length === 2 && req.method === 'GET') {
    const verified = url.searchParams.get('verified') || 'all';
    const label = url.searchParams.get('label') || 'all';
    const fixed = url.searchParams.get('fixed') || 'all';
    const reportedPhase = url.searchParams.get('reported_phase') || 'all';
    const tag = (url.searchParams.get('tag') || '').trim().toLowerCase();
    const types = url.searchParams.has('types') ? new Set((url.searchParams.get('types') || '').split(',').map((type) => type.trim()).filter(Boolean)) : null;
    const group = url.searchParams.get('group') || 'none';
    const q = (url.searchParams.get('q') || '').trim().toLowerCase();
    const page = Math.max(1, Number(url.searchParams.get('page') || 1));
    const pageSize = Math.min(200, Math.max(10, Number(url.searchParams.get('pageSize') || 50)));
    const all = [...bugs.keys()].sort((a, b) => a - b).filter((id) => {
      const item = summary(id);
      const hasReport = reports.has(id);
      const haystack = `${item.id} ${item.type} ${item.title} ${bugs.get(id)?.description || ''}`.toLowerCase();
      const phaseTags = [...item.review.static_tags, ...item.review.llm_tags, ...item.review.security_tags];
      const matchesAgentResult = verified === 'all' || (verified === 'unverified' ? !hasReport : hasReport && String(item.verified) === verified);
      return (!types || types.has(item.type)) && matchesAgentResult && (label === 'all' || item.review.label === label) && (fixed === 'all' || String(item.review.fixed) === fixed) && (reportedPhase === 'all' || item.review.reported_phase === reportedPhase) && (!tag || phaseTags.some((itemTag) => itemTag.toLowerCase().includes(tag))) && (!q || haystack.includes(q));
    });
    if (group === 'type') all.sort((left, right) => {
      const leftType = summary(left).type, rightType = summary(right).type;
      return leftType.localeCompare(rightType) || left - right;
    });
    const start = (page - 1) * pageSize;
    return sendJson(res, 200, { items: all.slice(start, start + pageSize).map(summary), total: all.length, page, pageSize, pages: Math.max(1, Math.ceil(all.length / pageSize)) });
  }
  if (parts[1] === 'bugs' && /^\d+$/.test(parts[2] || '') && parts.length === 3 && req.method === 'GET') {
    const id = Number(parts[2]);
    const bug = bugs.get(id);
    if (!bug) return sendJson(res, 404, { error: 'Static-analysis bug not found' });
    const report = reports.get(id) || null;
    return sendJson(res, 200, { bug, report, review: reviewFor(id), references: mergeSourceSnippets(sourceReferences(bug.description).map(sourceSnippet)) });
  }
  if (parts[1] === 'bugs' && /^\d+$/.test(parts[2] || '') && parts[3] === 'review' && req.method === 'PUT') {
    const id = Number(parts[2]);
    if (!bugs.has(id)) return sendJson(res, 404, { error: 'Static-analysis bug not found' });
    const body = await readBody(req);
    if (!VALID_LABELS.has(body.label) || typeof body.fixed !== 'boolean' || (body.reported_phase !== null && !REPORTED_PHASES.has(body.reported_phase)) || (body.review_confidence !== null && !REVIEW_LEVELS.has(body.review_confidence)) || (body.security_impact !== null && !REVIEW_LEVELS.has(body.security_impact))) return sendJson(res, 400, { error: 'Invalid review values' });
    if (String(body.report_link || '').trim() && !normalizeReportLink(body.report_link)) return sendJson(res, 400, { error: 'Report link must be a valid http(s) URL' });
    labels[String(id)] = {
      label: body.label,
      fixed: body.fixed,
      review_confidence: body.review_confidence,
      security_impact: body.security_impact,
      security_tags: normalizeTags(body.security_tags),
      reported_phase: body.reported_phase,
      report_link: normalizeReportLink(body.report_link),
      static_tags: normalizeTags(body.static_tags),
      llm_tags: normalizeTags(body.llm_tags),
      note: String(body.note || '').slice(0, 20000),
      updated_at: new Date().toISOString()
    };
    saveLabels();
    return sendJson(res, 200, { ok: true, review: reviewFor(id), stats: stats() });
  }
  return sendJson(res, 404, { error: 'Unknown API route' });
}

function staticFile(req, res, url) {
  const requested = decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname);
  const file = path.resolve(PUBLIC_DIR, `.${requested}`);
  if (!file.startsWith(`${path.resolve(PUBLIC_DIR)}${path.sep}`)) return sendJson(res, 403, { error: 'Forbidden' });
  fs.stat(file, (error, stat) => {
    if (error || !stat.isFile()) return sendJson(res, 404, { error: 'Not found' });
    const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.svg': 'image/svg+xml' };
    res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
    fs.createReadStream(file).pipe(res);
  });
}

prepareReviewStore();
loadData();
const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${HOST}:${PORT}`);
    if (url.pathname.startsWith('/api/')) return await api(req, res, url);
    if (req.method === 'GET') return staticFile(req, res, url);
    sendJson(res, 405, { error: 'Method not allowed' });
  } catch (error) {
    console.error(error);
    if (!res.headersSent) sendJson(res, 500, { error: error.message });
  }
});

server.on('error', (error) => {
  if (error.code === 'EADDRINUSE') {
    console.error(`BugConfirm could not start: http://${HOST}:${PORT} is already in use. Run ./bugconfirm.sh start to select a free local port.`);
  } else {
    console.error(`BugConfirm could not start: ${error.message}`);
  }
  process.exitCode = 1;
});

server.listen(PORT, HOST, () => console.log(`BugConfirm is running at http://${HOST}:${PORT} (localhost only)`));
