const http = require('http');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

const ROOT = __dirname;
const DATA_DIR = path.join(ROOT, 'data');
const PATCH_FILE = path.join(DATA_DIR, 'Patches', 'tasks.jsonl');
const TS_DIR = path.join(DATA_DIR, 'TSes');
const PUBLIC_DIR = path.join(ROOT, 'public');
const HOST = '127.0.0.1';
const PORT = Number(process.env.TYPESTATE_PORT || 8765);

const PATCH_KEYS = [
  'commit', 'parent', 'description', 'diff', 'bug_type', 'fixes', 'file',
  'function', 'before_code', 'after_code', 'mid_code', 'bad_version',
  'mid_version', 'good_version', 'mid_position', 'review_status', 'review_note'
];
const STATUS_LABELS = {
  pending: '待审核',
  correct: '正确',
  wrong: '错误',
  reviewed: '已审核',
  modified: '已修改'
};

let patches = [];
let patchByCommit = new Map();

function loadPatches() {
  const text = fs.readFileSync(PATCH_FILE, 'utf8');
  patches = text.split(/\r?\n/).filter(Boolean).map((line, index) => {
    try {
      const value = JSON.parse(line);
      return { ...value, _line: index };
    } catch (error) {
      throw new Error(`无法解析 tasks.jsonl 第 ${index + 1} 行: ${error.message}`);
    }
  });
  patchByCommit = new Map(patches.map((patch) => [patch.commit, patch]));
}

function hasTypestate(commit) {
  return fs.existsSync(path.join(TS_DIR, `${commit}.json`));
}

function readTypestate(commit) {
  const file = path.join(TS_DIR, `${commit}.json`);
  if (!fs.existsSync(file)) return null;
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (error) {
    return { __invalid: true, __message: error.message, __raw: fs.readFileSync(file, 'utf8') };
  }
}

function writePatchFile() {
  const output = patches.map(({ _line, ...patch }) => JSON.stringify(patch)).join('\n') + '\n';
  const tempFile = `${PATCH_FILE}.tmp`;
  fs.writeFileSync(tempFile, output, 'utf8');
  fs.copyFileSync(tempFile, PATCH_FILE);
  fs.unlinkSync(tempFile);
}

function safeCommit(value) {
  return typeof value === 'string' && /^[a-f0-9]{40}$/.test(value);
}

function jsonResponse(res, status, data) {
  const body = JSON.stringify(data);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    'Cache-Control': 'no-store'
  });
  res.end(body);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.setEncoding('utf8');
    req.on('data', (chunk) => {
      body += chunk;
      if (body.length > 30 * 1024 * 1024) {
        reject(new Error('请求内容过大'));
        req.destroy();
      }
    });
    req.on('end', () => {
      try { resolve(body ? JSON.parse(body) : {}); }
      catch (error) { reject(new Error(`JSON 格式错误: ${error.message}`)); }
    });
    req.on('error', reject);
  });
}

function summary(patch) {
  return {
    commit: patch.commit,
    parent: patch.parent,
    title: String(patch.description || '').split(/\r?\n/, 1)[0] || '无标题 patch',
    file: patch.file || '',
    function: patch.function || '',
    bug_type: Array.isArray(patch.bug_type) ? patch.bug_type : [],
    status: patch.review_status || 'pending',
    status_label: STATUS_LABELS[patch.review_status] || STATUS_LABELS.pending,
    has_typestate: hasTypestate(patch.commit),
    bad_version: patch.bad_version || '',
    good_version: patch.good_version || ''
  };
}

function getStats() {
  const stats = { total: patches.length, withTypestate: 0, pending: 0, correct: 0, wrong: 0, reviewed: 0, modified: 0 };
  for (const patch of patches) {
    if (hasTypestate(patch.commit)) stats.withTypestate += 1;
    const key = patch.review_status || 'pending';
    if (Object.prototype.hasOwnProperty.call(stats, key)) stats[key] += 1;
  }
  stats.missingTypestate = stats.total - stats.withTypestate;
  return stats;
}

async function handleApi(req, res, url) {
  const parts = url.pathname.split('/').filter(Boolean);
  if (parts[1] === 'stats' && req.method === 'GET') {
    return jsonResponse(res, 200, getStats());
  }
  if (parts[1] === 'patches' && parts.length === 2 && req.method === 'GET') {
    const q = (url.searchParams.get('q') || '').trim().toLowerCase();
    const status = url.searchParams.get('status') || 'all';
    const tsFilter = url.searchParams.get('typestate') || 'all';
    const page = Math.max(1, Number(url.searchParams.get('page') || 1));
    const pageSize = Math.min(2500, Math.max(10, Number(url.searchParams.get('pageSize') || 60)));
    const filtered = patches.filter((patch) => {
      const hasTs = hasTypestate(patch.commit);
      const haystack = [patch.commit, patch.description, patch.file, patch.function, ...(patch.bug_type || [])].join(' ').toLowerCase();
      return (!q || haystack.includes(q)) &&
        (status === 'all' || (patch.review_status || 'pending') === status) &&
        (tsFilter === 'all' || (tsFilter === 'yes' ? hasTs : !hasTs));
    });
    const start = (page - 1) * pageSize;
    return jsonResponse(res, 200, {
      items: filtered.slice(start, start + pageSize).map(summary),
      total: filtered.length,
      page,
      pageSize,
      pages: Math.max(1, Math.ceil(filtered.length / pageSize))
    });
  }
  if (parts[1] === 'patches' && parts.length === 3 && req.method === 'GET') {
    const commit = parts[2];
    if (!safeCommit(commit) || !patchByCommit.has(commit)) return jsonResponse(res, 404, { error: '找不到 patch' });
    const patch = patchByCommit.get(commit);
    return jsonResponse(res, 200, { patch: { ...patch, _line: undefined }, typestate: readTypestate(commit), has_typestate: hasTypestate(commit) });
  }
  if (parts[1] === 'patches' && parts.length === 3 && req.method === 'PUT') {
    const commit = parts[2];
    if (!safeCommit(commit) || !patchByCommit.has(commit)) return jsonResponse(res, 404, { error: '找不到 patch' });
    const body = await readBody(req);
    const current = patchByCommit.get(commit);
    const incoming = body.patch && typeof body.patch === 'object' ? body.patch : body;
    for (const key of PATCH_KEYS) {
      if (key !== 'commit' && Object.prototype.hasOwnProperty.call(incoming, key)) current[key] = incoming[key];
    }
    current.commit = commit;
    writePatchFile();
    return jsonResponse(res, 200, { ok: true, patch: { ...current, _line: undefined }, stats: getStats() });
  }
  if (parts[1] === 'typestates' && parts.length === 3 && req.method === 'PUT') {
    const commit = parts[2];
    if (!safeCommit(commit) || !patchByCommit.has(commit)) return jsonResponse(res, 404, { error: '找不到对应 patch' });
    const body = await readBody(req);
    const file = path.join(TS_DIR, `${commit}.json`);
    if (body.typestate === null || body.delete === true) {
      if (fs.existsSync(file)) fs.unlinkSync(file);
      return jsonResponse(res, 200, { ok: true, typestate: null, stats: getStats() });
    }
    if (!body.typestate || typeof body.typestate !== 'object' || Array.isArray(body.typestate)) {
      return jsonResponse(res, 400, { error: 'typestate 必须是 JSON 对象' });
    }
    fs.writeFileSync(file, `${JSON.stringify(body.typestate, null, 2)}\n`, 'utf8');
    return jsonResponse(res, 200, { ok: true, typestate: body.typestate, stats: getStats() });
  }
  return jsonResponse(res, 404, { error: '未知 API' });
}

function serveStatic(req, res, url) {
  let requestPath = url.pathname === '/' ? '/index.html' : url.pathname;
  requestPath = decodeURIComponent(requestPath);
  const file = path.resolve(PUBLIC_DIR, `.${requestPath}`);
  if (!file.startsWith(path.resolve(PUBLIC_DIR))) return jsonResponse(res, 403, { error: '禁止访问' });
  fs.stat(file, (error, stat) => {
    if (error || !stat.isFile()) return jsonResponse(res, 404, { error: '页面不存在' });
    const ext = path.extname(file);
    const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.svg': 'image/svg+xml' };
    res.writeHead(200, { 'Content-Type': types[ext] || 'application/octet-stream', 'Cache-Control': 'no-store' });
    fs.createReadStream(file).pipe(res);
  });
}

loadPatches();
const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${HOST}:${PORT}`);
    if (url.pathname.startsWith('/api/')) await handleApi(req, res, url);
    else if (req.method === 'GET') serveStatic(req, res, url);
    else jsonResponse(res, 405, { error: '只支持 GET 或 API 写入请求' });
  } catch (error) {
    console.error(error);
    if (!res.headersSent) jsonResponse(res, 500, { error: error.message });
  }
});

server.listen(PORT, HOST, () => {
  console.log(`TypeState Review running at http://${HOST}:${PORT}`);
  console.log('Local-only mode: this server binds to 127.0.0.1');
});
