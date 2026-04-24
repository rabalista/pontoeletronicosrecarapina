// VERSION: 16.1 (Cargo-Fix) - 2026-01-31
const API_CANDIDATES = [
  "https://nga-postauditory-unharmonically.ngrok-free.dev",
  "http://10.131.248.233:5005",

  "https://background-dakota-rain-reuters.trycloudflare.com",
  "https://organic-friendly-ethics-jewish.trycloudflare.com",
  "https://platform-intelligence-fallen-conferencing.trycloudflare.com",
  "https://eggs-word-payday-molecules.trycloudflare.com",
  "https://workshops-liquid-respectively-injection.trycloudflare.com",
];

const BYPASS_HEADERS = {
  "Bypass-Tunnel-Reminder": "true",
  "X-Tunnel-Skip-Proxy-Warning": "true",
  "ngrok-skip-browser-warning": "true",
};

async function sha256(text) {
  const enc = new TextEncoder().encode(text);
  const hashBuffer = await crypto.subtle.digest("SHA-256", enc);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

// Polyfill for Promise.any (Critical for older iOS/Android)
if (!Promise.any) {
  Promise.any = function (promises) {
    return new Promise((resolve, reject) => {
      let errors = [];
      let pending = promises.length;
      if (pending === 0) return reject(new AggregateError([], "No promises"));

      promises.forEach(p => Promise.resolve(p).then(
        val => resolve(val),
        err => {
          errors.push(err);
          if (--pending === 0) reject(new (window.AggregateError || Error)(errors));
        }
      ));
    });
  };
}

function readStore(key, def) {
  try {
    const v = localStorage.getItem(key);
    if (v === "undefined") return def;
    return v ? JSON.parse(v) : def;
  } catch (_) {
    return def;
  }
}
function writeStore(key, obj) {
  try {
    localStorage.setItem(key, JSON.stringify(obj));
  } catch (_) { }
}

function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

function randomHex(len) {
  const arr = new Uint8Array(len);
  crypto.getRandomValues(arr);
  return Array.from(arr).map((b) => b.toString(16).padStart(2, "0")).join("");
}
function getOfflineUsers() {
  return readStore("offlineUsers", {});
}
function setOfflineUsers(users) {
  writeStore("offlineUsers", users);
}
function getOfflineQueue() {
  return readStore("offlineQueue", []);
}
function setOfflineQueue(q) {
  writeStore("offlineQueue", q);
}
async function offlineRegisterUser(name, matricula, password, cargo) {
  const users = getOfflineUsers();
  if (users[matricula]) return { ok: false, message: "Matrícula já existe offline" };
  const salt = randomHex(16);
  const hashed = await sha256(password + salt);
  users[matricula] = { name, role: "user", cargo: cargo || "Funcionario", salt, hash: hashed };
  setOfflineUsers(users);
  return { ok: true, message: "Cadastro offline realizado" };
}
async function offlineLogin(matricula, password) {
  const users = getOfflineUsers();
  const u = users[matricula];
  if (!u) return null;
  const hashed = await sha256(password + u.salt);
  if (hashed !== u.hash) return null;
  return { token: `offline:${matricula}`, role: u.role || "user", name: u.name || matricula, cargo: u.cargo || "Funcionario" };
}
function offlinePunchAdd(type, neighborhood, city, extra = {}) {
  const q = getOfflineQueue();
  const ts = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const tsStr = `${ts.getFullYear()}-${pad(ts.getMonth() + 1)}-${pad(ts.getDate())} ${pad(ts.getHours())}:${pad(ts.getMinutes())}:${pad(ts.getSeconds())}`;
  q.push({
    matricula: extra.matricula || null,
    type,
    timestamp: tsStr,
    neighborhood,
    city,
    latitude: extra.latitude,
    longitude: extra.longitude,
    accuracy: extra.accuracy,
    full_address: extra.full_address,
    transaction_id: extra.transaction_id || ('txn_off_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9))
  });
  setOfflineQueue(q);
  return { ok: true };
}
function offlineHistory(currentMatricula) {
  const q = getOfflineQueue();
  const now = new Date();
  const currentMonth = now.getMonth(); // 0-11
  const currentYear = now.getFullYear();

  const filtered = q.filter(r => {
    // timestamp format: YYYY-MM-DD HH:MM:SS
    // We can try to parse it, or just compare substrings
    try {
      // Replace space with T to make it ISO-like for safer parsing if needed, 
      // but YYYY-MM-DD HH:MM:SS usually parses in modern browsers or we can simple parse strings.
      const parts = r.timestamp.split(' ')[0].split('-');
      const rYear = parseInt(parts[0]);
      const rMonth = parseInt(parts[1]) - 1; // 0-based
      const sameMonth = rYear === currentYear && rMonth === currentMonth;
      const sameUser = !currentMatricula || r.matricula === currentMatricula;
      return sameMonth && sameUser;
    } catch (e) {
      return true; // Keep if parse fails to be safe
    }
  });

  return filtered.map((r) => ({
    type: r.type,
    timestamp: r.timestamp,
    neighborhood: r.neighborhood,
    city: r.city,
    latitude: r.latitude,
    longitude: r.longitude,
    accuracy: r.accuracy,
    full_address: r.full_address,
    pending: true
  }));
}
async function offlineSync(token) {
  const q = getOfflineQueue();
  let migrated = 0;
  const remain = [];
  for (const r of q) {
    try {
      const res = await apiFetch(`/api/punch`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          type: r.type,
          neighborhood: r.neighborhood,
          city: r.city,
          latitude: r.latitude,
          longitude: r.longitude,
          accuracy: r.accuracy,
          full_address: r.full_address,
          transaction_id: r.transaction_id
        }),
      });
      if (res.ok || res.status === 409) {
        migrated += 1;
      } else {
        remain.push(r);
      }
    } catch (_) {
      remain.push(r);
    }
  }
  setOfflineQueue(remain);
  return { migrated };
}
function offlineClearRecords(currentMatricula) {
  const q = getOfflineQueue();
  const remain = q.filter(r => r.matricula !== currentMatricula);
  setOfflineQueue(remain);
  return { ok: true };
}
// Configuração do Registro Digital (Descoberta Automática)
const DISCOVERY_ID = "b76e30fb7ce6ba9c";
const DISCOVERY_URL = `https://ntfy.sh/registroponto_${DISCOVERY_ID}/raw?poll=1&last=1`;

async function fetchFromDiscovery() {
  const user_id = DISCOVERY_ID;

  // Helper: Robust fetch with race timeout
  const robustFetch = async (url, timeoutMs) => {
    const controller = new AbortController();
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => {
        controller.abort();
        reject(new Error("Timeout"));
      }, timeoutMs)
    );
    try {
      const res = await Promise.race([
        fetch(url, { cache: "no-store", signal: controller.signal }),
        timeoutPromise
      ]);
      return res;
    } catch (e) {
      let errStatus = e.message || 'Error';
      if (e.name === 'AbortError') errStatus = 'TIMEOUT';
      if (errStatus.includes('Failed to fetch')) errStatus = 'FERA_PROTEC'; // Simplified for UI
      window.DISCOVERY_LOG = (window.DISCOVERY_LOG || "") + `[${errStatus}] `;
      console.warn("Discovery fetch failed:", url, e.message);
      return null;
    }
  };

  // Helper to extract and fix URLs from raw lines
  const parseSignal = (line) => {
    line = line.trim();
    if (!line) return null;
    if (line.includes('trycloudflare.com') || line.includes('serveousercontent.com')) {
      const match = line.match(/[a-zA-Z0-9.-]+\.(trycloudflare\.com|serveousercontent\.com)/);
      if (match) {
        let url = 'https://' + match[0];
        return url;
      }
    }
    return null;
  };

  // Triple-Shield Fetch (Fetch -> XHR -> Error)
  const shieldedLookup = async (lookupUrl) => {
    try {
      const res = await robustFetch(`${lookupUrl}&t=${Date.now()}`, 10000);
      if (res && res.ok) return await res.text();
    } catch (e) { }

    // XHR Fallback (bypasses some browser fetch-policies)
    return new Promise((resolve) => {
      const xhr = new XMLHttpRequest();
      xhr.open('GET', `${lookupUrl}&t=${Date.now()}`, true);
      xhr.timeout = 10000;
      xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) resolve(xhr.responseText);
        else if (xhr.readyState === 4) resolve(null);
      };
      xhr.onerror = () => resolve(null);
      xhr.ontimeout = () => resolve(null);
      xhr.send();
    });
  };

  // 1. Try Ntfy (Primary)
  try {
    const text = await shieldedLookup(DISCOVERY_URL);
    if (text) {
      const urls = text.split('\n').map(parseSignal).filter(Boolean);
      if (urls.length > 0) return urls[urls.length - 1];
    }
  } catch (e) { }

  // 1b. Try Ntfy (JSON Fallback)
  try {
    const jsonUrl = `https://ntfy.sh/registroponto_${DISCOVERY_ID}/json?poll=1&last=1&t=${Date.now()}`;
    const res = await robustFetch(jsonUrl, 10000);
    if (res && res.ok) {
      const text = await res.text();
      const urls = text.split('\n').filter(Boolean).map(line => {
        try {
          const obj = JSON.parse(line);
          return obj.message ? parseSignal(obj.message) : null;
        } catch (e) { return null; }
      }).filter(Boolean);
      if (urls.length > 0) return urls[urls.length - 1];
    }
  } catch (e) { }

  // 2. Try Dweet.io (Parallel Backup)
  try {
    const dweetUrl = `https://dweet.io/get/latest/dweet/for/registroponto_${DISCOVERY_ID}?t=${Date.now()}`;
    const res = await robustFetch(dweetUrl, 8000);
    if (res && res.ok) {
      const js = await res.json();
      if (js.with && js.with.length > 0 && js.with[0].content && js.with[0].content.api) {
        return parseSignal(js.with[0].content.api);
      }
    }
  } catch (e) { console.warn("Discovery dweet fail:", e); }

  return null;
}

async function isApiAvailable() {
  try {
    await window.API_READY;
    const res = await apiFetch(`/api/online`, { method: "GET" });
    const js = await res.json();
    return !!js.online;
  } catch (_) {
    return false;
  }
}

// Global Probe Function (Moved out of detectApiBase)
const probeXHR = (url, timeoutMs) => {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('GET', `${url}/api/online?cb=${Math.random()}`, true);
    Object.keys(BYPASS_HEADERS).forEach(key => {
      xhr.setRequestHeader(key, BYPASS_HEADERS[key]);
    });
    xhr.timeout = timeoutMs;
    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          try {
            const data = JSON.parse(xhr.responseText);
            if (data.online) resolve(url);
            else reject(new Error("OFFLINE"));
          } catch (e) { reject(new Error("JSON_ERR")); }
        } else {
          reject(new Error("STATUS_" + xhr.status));
        }
      }
    };
    xhr.onerror = () => reject(new Error("NETWORK_FAIL"));
    xhr.ontimeout = () => reject(new Error("TIMEOUT"));
    xhr.send();
  });
};

const probe = async (base, timeout) => {
  if (window.logRadar) window.logRadar(`Testando: ${base.split('.')[0].slice(-10)}...`);
  try {
    const res = await probeXHR(base, timeout);
    if (res) {
      if (window.logRadar) window.logRadar(`✅ OK: ${base.split('.')[0].slice(-5)}`);
      return res;
    }
  } catch (e) {
    if (window.logRadar) window.logRadar(`❌ ${e.message}: ${base.split('.')[0].slice(-5)}`);
  }
  throw new Error("fail");
};

async function detectApiBase() {
  const cached = readStore("api_base", null);
  const override = readStore("api_override", null);
  const queryApi = getQueryParam("api") || getQueryParam("api_base");

  // Freshness check: If override is from a previous day, ignore it
  const lastUpdate = parseInt(readStore("api_last_success", "0"));
  const isFresh = (Date.now() - lastUpdate) < (1000 * 60 * 30); // 30 minutes

  // v15.0: MAGIC LINK TOTAL TRUST (Current URL Query Param ONLY)
  if (queryApi) {
    writeStore("api_base", queryApi);
    writeStore("api_override", queryApi);
    writeStore("api_last_success", Date.now());
    window.API_BASE_URL = queryApi;

    // Save to history
    let hist = readStore("tunnel_history", []);
    if (!hist.includes(queryApi)) {
      hist.unshift(queryApi);
      writeStore("tunnel_history", hist.slice(0, 5));
    }

    return queryApi;
  }

  // Use override ONLY IF FRESH (prevent old tunnel persistence)
  if (override && isFresh) {
    window.API_BASE_URL = override;
    return override;
  }

  // Filter and prioritize
  let uniqueCandidates = [...new Set([
    cached,
    ...API_CANDIDATES
  ])].filter(Boolean);

  // Start Discovery in Background
  const discoveryPromise = fetchFromDiscovery();

  // Wave 0: History Shield (STRICTER PROBE)
  const history = readStore("tunnel_history", []);
  if (history.length > 0) {
    try {
      const historyWinner = await Promise.any(history.map(c => probe(c, 15000)));
      if (historyWinner) {
        writeStore("api_base", historyWinner);
        window.API_BASE_URL = historyWinner;
        return historyWinner;
      }
    } catch (e) { }
  }

  // Wave 1: Fast Probe (Force all candidates immediately in v14)
  if (window.logRadar) window.logRadar(`📡 Martelo v14: Testando ${uniqueCandidates.length} túneis...`);

  try {
    // FIX: Using Promise.any instead of Promise.race to ignore fast failures
    const fastWinner = await Promise.any(
      uniqueCandidates.map(c => probe(c, 20000))
    );
    if (fastWinner) {
      writeStore("api_base", fastWinner);
      writeStore("api_last_success", Date.now());
      window.API_BASE_URL = fastWinner;
      return fastWinner;
    }
  } catch (e) {
    if (window.logRadar) window.logRadar(`⚠️ Varredura inicial sem sucesso.`);
  }

  // Wave 2: Robust Parallel Probe - Extreme Timeout (30s) for slow 4G/Warm-up
  const knownCandidatesProbe = Promise.any(
    uniqueCandidates.map(c => probe(c, 30000))
  );

  // B. Probe Discovered Candidate (when it arrives)
  const discoveryProbe = discoveryPromise.then(async (discoveredUrl) => {
    if (discoveredUrl) {
      if (!uniqueCandidates.includes(discoveredUrl)) uniqueCandidates.push(discoveredUrl);
      return await probe(discoveredUrl, 30000);
    }
    throw new Error("No Discovery");
  });

  try {
    // Race known candidates vs discovery
    const winner = await Promise.any([knownCandidatesProbe, discoveryProbe]);
    if (winner) {
      writeStore("api_base", winner);
      window.API_BASE_URL = winner;
      return winner;
    }
  } catch (e) { }

  // Se nada funcionou, v10.0 NUNCA apaga o cached.
  // Apenas limpa se o reset for manual.
  return null;
}

async function apiFetch(path, options) {
  const tryFetch = async () => {
    const cached = readStore("api_base", null);
    const override = readStore("api_override", null);

    let bases = [...new Set([
      override,
      window.API_BASE_URL,
      cached,
      ...API_CANDIDATES
    ])].filter(Boolean);

    // v4.8: If NOT a GET request, we MUST run sequentially to avoid triplicating records
    const isGet = !options || !options.method || options.method === 'GET';

    if (isGet) {
      try {
        const firstWorkingBase = await Promise.any(bases.slice(0, 3).map(async (base) => {
          const url = `${base}${path}${path.includes('?') ? '&' : '?'}t=${Date.now()}`;
          const fetchOptions = { ...(options || {}), headers: { ...(options ? options.headers : {}), ...BYPASS_HEADERS } };
          const res = await fetchWithTimeout(url, fetchOptions, 8000);
          if (res.ok || res.status) return { base, res };
          throw new Error("fail");
        }));
        window.API_BASE_URL = firstWorkingBase.base;
        writeStore("api_base", firstWorkingBase.base);
        return firstWorkingBase.res;
      } catch (e) { }
    }

    // Fallback sequencial (mais seguro para POSTs) nos demais
    for (const base of bases) {
      try {
        const url = `${base}${path}${path.includes('?') ? '&' : '?'}t=${Date.now()}`;
        const fetchOptions = { ...(options || {}), headers: { ...(options ? options.headers : {}), ...BYPASS_HEADERS } };
        const res = await fetchWithTimeout(options && options.method !== 'GET' ? `${base}${path}` : url, fetchOptions, 15000);
        if (res.ok || res.status) {
          window.API_BASE_URL = base;
          writeStore("api_base", base);
          return res;
        }
      } catch (_) { continue; }
    }
    return null;
  };

  let result = await tryFetch();
  if (!result) {
    // Radar Mode: Perpetual Auto-Discovery
    window.startRadarMode = async (statusCallback) => {
      console.log("📡 Starting Radar Mode...");
      let attempts = 0;

      while (true) {
        attempts++;
        const log = (msg) => {
          if (statusCallback) statusCallback(`<strong>Tentativa ${attempts}</strong><br><small>${msg}</small>`);
        };
        log("Buscando sinal...");

        // 1. Try Discovery (Ntfy + Dweet)
        let discovered = null;
        let source = "";

        // Try Ntfy / Dweet
        log(`Consultando Registro... ${window.DISCOVERY_LOG || ''}`);
        window.DISCOVERY_LOG = ""; // Reset for next loop
        try {
          discovered = await fetchFromDiscovery();
        } catch (e) {
          log(`⚠️ Nuvem offline: ${e.message}`);
        }
        if (discovered) source = "Ntfy/Dweet";

        if (discovered) {
          log(`📡 Sinal: ${discovered.replace('https://', '')}...<br>Testando...`);
          try {
            const isWorking = await probe(discovered, 30000);
            if (isWorking) {
              if (window.logRadar) window.logRadar("✨ CONECTADO!");

              // SALVAR NO HISTÓRICO
              let hist = readStore("tunnel_history", []);
              if (!hist.includes(discovered)) {
                hist.unshift(discovered);
                writeStore("tunnel_history", hist.slice(0, 5));
              }

              writeStore("api_base", discovered);
              writeStore("api_last_success", Date.now());
              window.location.reload();
              return;
            }
          } catch (e) { }
        }

        // 2. RETRY CANDIDATES (v14.0: All parallel)
        log("🔍 Tentando todos os túneis conhecidos...");
        try {
          const winner = await Promise.race(API_CANDIDATES.map(c => probe(c, 20000)));
          if (winner) {
            writeStore("api_base", winner);
            writeStore("api_last_success", Date.now());
            window.location.reload();
            return;
          }
        } catch (e) { }

        log("🔍 Nenhum sinal. Reiniciando busca...");

        // 2. Try Local Fallback
        const local = "http://192.168.15.10:5005";
        try {
          if (await probe(local, 1000)) {
            localStorage.setItem('cached_api_base', local);
            window.location.reload();
            return;
          }
        } catch (e) { }

        // Wait 3s before retry
        await new Promise(r => setTimeout(r, 3000));
      }
    };

    // Check if we need to start radar immediately (if initialization failed)
    window.API_READY.catch(() => {
      console.warn("Initial connection failed. Waiting for UI to trigger Radar Mode.");
    });
    // Se falhou, tenta redetectar e tenta de novo
    const detected = await detectApiBase();
    if (detected) {
      window.API_BASE_URL = detected;
      result = await tryFetch();
    }
  }

  if (result) return result;
  throw new Error("API indisponível");
}

function fetchWithTimeout(resource, options, timeoutMs) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs || 10000);
  return fetch(resource, { ...(options || {}), signal: controller.signal }).finally(() => clearTimeout(id));
}

const initialApi = getQueryParam("api") || getQueryParam("api_base");
if (initialApi) {
  writeStore("api_override", initialApi);
  writeStore("api_base", initialApi);
  window.API_BASE_URL = initialApi;
}
window.API_READY = detectApiBase().then((b) => {
  window.API_BASE_URL = b;
  writeStore("api_base", b);
  window.apiFetch = apiFetch;
  window.sha256 = sha256;
  window.readStore = readStore;
  window.writeStore = writeStore;
  window.offline = {
    registerUser: offlineRegisterUser,
    login: offlineLogin,
    punchAdd: offlinePunchAdd,
    history: offlineHistory,
    sync: offlineSync,
    clear: offlineClearRecords,
    isApiAvailable,
  };
  window.DISCOVERY_LOG = "";

  window.setManualApi = function () {
    const raw = document.getElementById('manualApi').value.trim();
    if (!raw) return;
    let url = raw;
    if (!url.startsWith('http')) url = 'https://' + url;
    if (!url.includes('.')) return alert("Link inválido");

    writeStore("api_base", url);
    writeStore("api_override", url);
    writeStore("api_last_success", Date.now());
    alert("Link manual salvo! Recarregando...");
    window.location.reload();
  };

  window.clearCache = function () {
    localStorage.clear();
    sessionStorage.clear();
    window.location.href = window.location.pathname + '?reset=' + Date.now();
  };
  return b;
});

// Auto-reset if stuck
if (getQueryParam('reset')) {
  localStorage.removeItem('api_base');
  localStorage.removeItem('api_override');
}
