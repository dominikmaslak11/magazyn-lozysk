"use strict";

const state = {
  bearings: [],
  shelves: [],
  types: [],
  editingId: null,
  chosenSource: "recznie",
  chosenTyp: "",
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

// ------------------------------------------------------------- motyw ----

function initTheme() {
  const saved = localStorage.getItem("theme");
  if (saved) document.documentElement.setAttribute("data-theme", saved);
  $("#themeToggle").addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
  });
}

// -------------------------------------------------------------- toast ----

let toastTimer = null;
function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 3200);
}

// --------------------------------------------------------------- tabs ----

function initTabs() {
  $$(".tab").forEach((tab) => {
    tab.addEventListener("click", () => showView(tab.dataset.view));
  });
  $("#dataTabBtn").addEventListener("click", () => showView("data"));
}

function showView(name) {
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === name));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${name}`));
  $("#addBearingBtn").style.display = name === "bearings" ? "flex" : "none";
  if (name === "shelves") loadShelves();
  if (name === "data") { loadBackups(); loadAliases(); loadMoves(); }
}

// --------------------------------------------------------------- API -----

async function api(path, opts) {
  const resp = await fetch(path, opts);
  if (!resp.ok) {
    let msg = `Błąd ${resp.status}`;
    try { msg = (await resp.json()).message || msg; } catch (_) {}
    throw new Error(msg);
  }
  const ct = resp.headers.get("content-type") || "";
  return ct.includes("application/json") ? resp.json() : resp;
}

// ---------------------------------------------------------- łożyska -----

async function loadBearings() {
  const search = $("#searchInput").value.trim();
  const url = "/api/bearings" + (search ? `?search=${encodeURIComponent(search)}` : "");
  state.bearings = await api(url);
  renderBearings();
}

function badgeClass(zrodlo) {
  return { offline: "offline", internet: "internet", recznie: "recznie" }[zrodlo] || "recznie";
}
function badgeLabel(zrodlo) {
  return { offline: "baza offline", internet: "internet", recznie: "ręcznie" }[zrodlo] || zrodlo;
}

function renderBearings() {
  const grid = $("#bearingsGrid");
  grid.innerHTML = "";
  $("#bearingsEmpty").style.display = state.bearings.length ? "none" : "block";

  for (const b of state.bearings) {
    const card = document.createElement("div");
    card.className = "card bearing-card";
    const regalTxt = b.regal_nazwa ? b.regal_nazwa + (b.reczny_przydzial ? " (ręcznie)" : "") : "—";
    card.innerHTML = `
      <div class="row1">
        <span class="symbol">${esc(b.symbol)}</span>
        <span class="badge ${badgeClass(b.zrodlo)}">${badgeLabel(b.zrodlo)}</span>
      </div>
      <div class="dims">
        <span>d <b>${fmt(b.d)}</b> mm</span>
        <span>D <b>${fmt(b.D)}</b> mm</span>
        <span>B <b>${fmt(b.B)}</b> mm</span>
      </div>
      <div class="meta-row">
        <span>${esc(b.typ || "")}</span>
        <span>Ilość: <b style="color:var(--text)">${b.ilosc}</b></span>
      </div>
      <div class="meta-row">
        <span class="shelf-tag">${esc(regalTxt)}</span>
        <span>${esc(b.uwagi || "")}</span>
      </div>
      <div class="card-actions">
        <button class="btn small" data-edit="${b.id}">Edytuj</button>
        <button class="btn small danger" data-del="${b.id}">Usuń</button>
      </div>
    `;
    grid.appendChild(card);
  }

  grid.querySelectorAll("[data-edit]").forEach((btn) =>
    btn.addEventListener("click", () => openBearingModal(btn.dataset.edit)));
  grid.querySelectorAll("[data-del]").forEach((btn) =>
    btn.addEventListener("click", () => deleteBearing(btn.dataset.del)));
}

async function deleteBearing(id) {
  const b = state.bearings.find((x) => x.id === id);
  if (!confirm(`Usunąć łożysko ${b ? b.symbol : ""}?`)) return;
  await api(`/api/bearings/${id}`, { method: "DELETE" });
  toast("Usunięto łożysko.");
  loadBearings();
}

// --------------------------------------------------------- modal łożyska ----

function fillTypeSelect(selectEl, selected) {
  selectEl.innerHTML = state.types.map((t) =>
    `<option value="${esc(t)}" ${t === selected ? "selected" : ""}>${esc(t)}</option>`).join("");
}

function fillShelfSelect(selectEl, selectedShelfId, forceManual) {
  const autoOpt = `<option value="auto" ${!forceManual ? "selected" : ""}>Auto (na podstawie średnicy D)</option>`;
  const opts = state.shelves.map((s) => {
    const lo = s.d_min == null ? "0" : s.d_min;
    const hi = s.d_max == null ? "∞" : s.d_max;
    const label = `${s.nazwa} (poziom ${s.poziom}, D: ${lo}-${hi} mm)`;
    const sel = forceManual && s.id === selectedShelfId ? "selected" : "";
    return `<option value="${s.id}" ${sel}>${esc(label)}</option>`;
  }).join("");
  selectEl.innerHTML = autoOpt + opts;
}

function openBearingModal(id) {
  state.editingId = id || null;
  const b = id ? state.bearings.find((x) => x.id === id) : null;

  $("#bearingModalTitle").textContent = b ? "Edytuj łożysko" : "Dodaj łożysko";
  $("#btnDeleteBearing").style.display = b ? "inline-block" : "none";

  fillTypeSelect($("#f_typ"), b ? b.typ : state.types[0]);
  $("#f_symbol").value = b ? b.symbol : "";
  $("#f_d").value = b && b.d != null ? b.d : "";
  $("#f_D").value = b && b.D != null ? b.D : "";
  $("#f_B").value = b && b.B != null ? b.B : "";
  $("#f_ilosc").value = b ? b.ilosc : 1;
  $("#f_uwagi").value = b ? b.uwagi || "" : "";

  state.chosenSource = b ? b.zrodlo : "recznie";
  setSourceNote(state.chosenSource);

  fillShelfSelect($("#f_regal"), b ? b.regal_id : null, b ? b.reczny_przydzial : false);

  $("#bearingOverlay").classList.add("open");
}

function closeBearingModal() {
  $("#bearingOverlay").classList.remove("open");
  state.editingId = null;
}

function setSourceNote(source) {
  const labels = {
    offline: "Źródło danych: baza offline (pewne)",
    internet: "Źródło danych: internet (orientacyjne - zweryfikuj suwmiarką)",
    recznie: "Źródło danych: wpisane ręcznie",
  };
  $("#sourceNote").textContent = labels[source] || `Źródło danych: ${source}`;
}

async function fetchBySymbol() {
  const symbol = $("#f_symbol").value.trim();
  if (!symbol) { toast("Wpisz symbol łożyska."); return; }
  const result = await api(`/api/lookup/symbol?symbol=${encodeURIComponent(symbol)}`);
  $("#f_symbol").value = result.symbol || symbol;
  if (result.d != null) {
    $("#f_d").value = result.d;
    $("#f_D").value = result.D;
    $("#f_B").value = result.B;
  }
  if (result.typ) fillTypeSelect($("#f_typ"), result.typ);
  state.chosenSource = result.source;
  setSourceNote(result.source);
  if (result.note) toast(result.note);
}

async function fetchByDimensions() {
  const d = $("#f_d").value, D = $("#f_D").value, B = $("#f_B").value;
  if (!d && !D && !B) { toast("Wpisz przynajmniej jeden wymiar (d, D lub B)."); return; }
  const params = new URLSearchParams();
  if (d) params.set("d", d);
  if (D) params.set("D", D);
  if (B) params.set("B", B);
  const candidates = await api(`/api/lookup/dimensions?${params}`);
  if (!candidates.length) { toast("Nie znaleziono pasującego symbolu."); return; }
  const first = candidates[0];
  $("#f_symbol").value = first.symbol;
  $("#f_d").value = first.d;
  $("#f_D").value = first.D;
  $("#f_B").value = first.B;
  if (first.typ) fillTypeSelect($("#f_typ"), first.typ);
  state.chosenSource = first.online ? "internet" : "offline";
  setSourceNote(state.chosenSource);
  if (candidates.length > 1) {
    const inne = candidates.slice(1, 6).map((c) => c.symbol).join(", ");
    toast(`Wybrano ${first.symbol}. Inne pasujące: ${inne}`);
  } else if (first.online) {
    toast(`Propozycja z internetu: ${first.symbol}. Zweryfikuj przed zapisem.`);
  }
}

async function saveBearing() {
  const symbol = $("#f_symbol").value.trim();
  if (!symbol) { toast("Symbol łożyska jest wymagany."); return; }

  const shelfChoice = $("#f_regal").value;
  const reczny = shelfChoice !== "auto";
  const payload = {
    symbol,
    typ: $("#f_typ").value,
    d: numOrNull($("#f_d").value),
    D: numOrNull($("#f_D").value),
    B: numOrNull($("#f_B").value),
    ilosc: parseInt($("#f_ilosc").value || "0", 10),
    zrodlo: state.chosenSource,
    uwagi: $("#f_uwagi").value.trim(),
    regal_id: reczny ? shelfChoice : null,
    reczny_przydzial: reczny,
  };

  if (state.editingId) {
    await api(`/api/bearings/${state.editingId}`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    toast("Zapisano zmiany.");
  } else {
    await api("/api/bearings", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    toast("Dodano łożysko.");
  }
  closeBearingModal();
  loadBearings();
}

// ---------------------------------------------------------------- regały ----

async function loadShelves() {
  state.shelves = await api("/api/shelves");
  renderShelves();
}

function renderShelves() {
  const list = $("#shelvesList");
  list.innerHTML = "";
  for (const s of state.shelves) {
    const card = document.createElement("div");
    card.className = "card shelf-card";
    card.dataset.id = s.id;
    card.innerHTML = `
      <div class="fields">
        <label>Poziom</label><input class="s-poziom" type="number" value="${s.poziom}">
        <label>Nazwa</label><input class="s-nazwa" value="${esc(s.nazwa)}">
        <label>D od [mm]</label><input class="s-dmin" inputmode="decimal" value="${s.d_min == null ? "" : s.d_min}">
        <label>D do [mm]</label><input class="s-dmax" inputmode="decimal" value="${s.d_max == null ? "" : s.d_max}" placeholder="bez limitu">
      </div>
      <div class="shelf-counts">
        <span>Pozycje: <b>${s.pozycje}</b></span>
        <span>Sztuki: <b>${s.sztuki}</b></span>
      </div>
    `;
    list.appendChild(card);
  }
}

async function saveShelves() {
  const cards = $$("#shelvesList .shelf-card");
  try {
    for (const card of cards) {
      const id = card.dataset.id;
      const payload = {
        nazwa: card.querySelector(".s-nazwa").value.trim(),
        poziom: parseInt(card.querySelector(".s-poziom").value, 10),
        d_min: numOrNull(card.querySelector(".s-dmin").value),
        d_max: numOrNull(card.querySelector(".s-dmax").value),
      };
      await api(`/api/shelves/${id}`, {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
    }
    toast("Zapisano zmiany w regałach.");
    loadShelves();
  } catch (e) {
    toast("Błąd zapisu: " + e.message);
  }
}

async function reassignAll() {
  await saveShelves();
  const res = await api("/api/shelves/reassign", { method: "POST" });
  toast(`Przeliczono przydział dla ${res.changed} łożysk.`);
  loadShelves();
}

// ------------------------------------------------------------------ dane ----

async function loadBackups() {
  const backups = await api("/api/backups");
  const list = $("#backupsList");
  if (!backups.length) {
    list.innerHTML = '<div class="row"><span>Brak kopii zapasowych.</span></div>';
    return;
  }
  list.innerHTML = backups.map((b) =>
    `<div class="row"><span>${esc(b.nazwa)}</span><span>${b.data} · ${b.rozmiar_kb} KB</span></div>`
  ).join("");
}

async function loadAliases() {
  const aliases = await api("/api/barcode-aliases");
  const list = $("#aliasesList");
  if (!aliases.length) {
    list.innerHTML = '<div class="row"><span>Brak zapamiętanych kodów.</span></div>';
    return;
  }
  list.innerHTML = aliases.map((a) =>
    `<div class="row"><span><code>${esc(a.kod)}</code> → <strong>${esc(a.symbol)}</strong></span>` +
    `<button class="btn danger" data-alias-id="${esc(a.id)}">Usuń</button></div>`
  ).join("");
  list.querySelectorAll("button[data-alias-id]").forEach((btn) => {
    btn.addEventListener("click", () => deleteAlias(btn.dataset.aliasId));
  });
}

async function deleteAlias(id) {
  if (!confirm("Usunąć to skojarzenie? Przy następnym skanie appka zapyta o nie ponownie.")) return;
  await api(`/api/barcode-aliases/${id}`, { method: "DELETE" });
  toast("Skojarzenie usunięte.");
  await loadAliases();
}

async function loadMoves() {
  const moves = await api("/api/stock-moves");
  const list = $("#movesList");
  if (!moves.length) {
    list.innerHTML = '<div class="row"><span>Brak ruchów.</span></div>';
    return;
  }
  list.innerHTML = moves.slice(0, 50).map((m) => {
    const znak = m.delta > 0 ? `+${m.delta}` : `${m.delta}`;
    const kiedy = (m.applied_at || "").slice(0, 16).replace("T", " ");
    const skad = m.zrodlo === "web" ? "komputer" : "telefon";
    return `<div class="row"><span><strong>${esc(m.symbol)}</strong> ${znak} szt.</span>` +
           `<span>${kiedy} · ${skad}</span></div>`;
  }).join("");
}

async function importDbFile() {
  const input = $("#importDbFile");
  if (!input.files.length) { toast("Wybierz plik .db"); return; }
  if (!confirm("To CAŁKOWICIE zastąpi bieżącą bazę danych (backup zostanie zrobiony automatycznie). Kontynuować?")) return;
  const formData = new FormData();
  formData.append("file", input.files[0]);
  await api("/api/import/db", { method: "POST", body: formData });
  toast("Zaimportowano bazę.");
  input.value = "";
  loadBackups();
  loadBearings();
  loadShelves();
}

async function importJsonFile(mode) {
  const input = $("#importJsonFile");
  if (!input.files.length) { toast("Wybierz plik .json"); return; }
  const label = mode === "zastap" ? "zastąpi bieżące dane" : "dopisze pozycje jako nowe";
  if (!confirm(`Import ${label}. Kontynuować?`)) return;
  const text = await input.files[0].text();
  let data;
  try { data = JSON.parse(text); } catch (e) { toast("Niepoprawny plik JSON."); return; }
  const res = await api(`/api/import/json?mode=${mode}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
  });
  toast(`Zaimportowano: ${res.regaly} regałów, ${res.lozyska} łożysk.`);
  input.value = "";
  loadBackups();
  loadBearings();
  loadShelves();
}

// --------------------------------------------------------------- helpery ----

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function fmt(v) { return v == null ? "—" : (Number.isInteger(v) ? v : v); }
function numOrNull(v) {
  if (v === "" || v === null || v === undefined) return null;
  const n = parseFloat(String(v).replace(",", "."));
  return Number.isNaN(n) ? null : n;
}

// ----------------------------------------------------------------- init ----

async function init() {
  initTheme();
  initTabs();

  state.types = await api("/api/types");

  $("#searchInput").addEventListener("input", debounce(loadBearings, 250));
  $("#addBearingBtn").addEventListener("click", () => openBearingModal(null));
  $("#btnCancelBearing").addEventListener("click", closeBearingModal);
  $("#bearingOverlay").addEventListener("click", (e) => { if (e.target.id === "bearingOverlay") closeBearingModal(); });
  $("#btnFetchBySymbol").addEventListener("click", fetchBySymbol);
  $("#btnFetchByDims").addEventListener("click", fetchByDimensions);
  $("#btnSaveBearing").addEventListener("click", saveBearing);
  $("#btnDeleteBearing").addEventListener("click", async () => {
    if (state.editingId) { await deleteBearing(state.editingId); closeBearingModal(); }
  });

  $("#saveShelvesBtn").addEventListener("click", saveShelves);
  $("#reassignBtn").addEventListener("click", reassignAll);

  $("#importDbFile").addEventListener("change", importDbFile);
  $("#importJsonReplace").addEventListener("click", () => importJsonFile("zastap"));
  $("#importJsonAppend").addEventListener("click", () => importJsonFile("dolacz"));

  await loadBearings();

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/service-worker.js").catch(() => {});
  }
}

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

document.addEventListener("DOMContentLoaded", init);
