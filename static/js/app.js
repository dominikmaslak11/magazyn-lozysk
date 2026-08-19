"use strict";

const state = {
  bearings: [],
  sugestie: {},
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
  // Podpowiedzi przełożenia liczy serwer deterministycznie (bez AI) - jeśli padną,
  // lista łożysk i tak ma się wyświetlić.
  try {
    const lista = await api("/api/suggestions");
    state.sugestie = Object.fromEntries(lista.map((s) => [s.bearing_id, s]));
  } catch (_) { state.sugestie = {}; }
  try { renderScalenia(await api("/api/consolidation")); } catch (_) {}
  try { renderNiezgodnosci(await api("/api/inconsistencies")); } catch (_) {}
  try { renderAlerty(await api("/api/stock-alerts")); } catch (_) {}
  renderBearings();
}

function badgeClass(zrodlo) {
  return { offline: "offline", internet: "internet", recznie: "recznie" }[zrodlo] || "recznie";
}
function badgeLabel(zrodlo) {
  return { offline: "baza offline", internet: "internet", recznie: "ręcznie", ai: "AI" }[zrodlo] || zrodlo;
}

function renderBearings() {
  const grid = $("#bearingsGrid");
  grid.innerHTML = "";
  $("#bearingsEmpty").style.display = state.bearings.length ? "none" : "block";

  for (const b of state.bearings) {
    const card = document.createElement("div");
    card.className = "card bearing-card";
    const sug = state.sugestie[b.id];
    const znacznikWeryfikacji = b.do_weryfikacji
      ? '<span class="badge" style="background:#c25e00;color:#fff">do sprawdzenia</span>' : "";
    if (sug) {
      card.style.borderLeft = "5px solid #e0a92b";
      card.style.background = "color-mix(in srgb, #e0a92b 8%, transparent)";
    }
    // PEŁNA ścieżka ("Regał 2 › Półka 2"), nie sama nazwa węzła: nazwy półek powtarzają
    // się między regałami, więc samo "Półka 2" nie mówi, gdzie iść po to łożysko.
    const regalTxt = b.sciezka
      ? b.sciezka + (b.bufor ? " — tymczasowo" : "") + (b.reczny_przydzial ? " (ręcznie)" : "")
      : "bez lokalizacji";
    card.innerHTML = `
      <div class="row1">
        <span class="symbol">${esc(b.symbol)}</span>
        <span class="badge ${badgeClass(b.zrodlo)}">${badgeLabel(b.zrodlo)}</span>${znacznikWeryfikacji}
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
        <span class="shelf-tag" style="font-weight:600">📍 ${esc(regalTxt)}</span>
        <span>${esc(b.uwagi || "")}</span>
      </div>
      ${sug ? `<div class="meta-row" style="color:#8a6400">
        <span>⚠ Potrzebna interwencja: przenieś ${sug.ilosc} szt. do <b>${esc(sug.sugerowana)}</b>
        — ${esc(sug.powod)}${sug.reczny ? " (pozycja ustawiona ręcznie)" : ""}</span>
        <button class="btn small" data-move="${b.id}" data-cel="${sug.sugerowana_id}">Przenieś</button>
      </div>` : ""}
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
  grid.querySelectorAll("[data-move]").forEach((btn) =>
    btn.addEventListener("click", () => przeniesLozysko(btn.dataset.move, btn.dataset.cel)));
}

const KOLOR_ALERTU = { brak: "#c1402e", pilne: "#e0a92b", nadmiar: "#6b7280" };

function renderAlerty(lista) {
  const box = $("#alertyBox");
  if (!lista || !lista.length) { box.innerHTML = ""; return; }
  box.innerHTML = lista.map((a) => `
    <div class="card" style="border-left:5px solid ${KOLOR_ALERTU[a.poziom]}">
      <div class="row1">
        <span><b>${a.poziom === "nadmiar" ? "ℹ" : "⚠"} ${esc(a.symbol)}</b>
          <span class="badge">${a.poziom === "brak" ? "brak na stanie"
            : a.poziom === "pilne" ? "poniżej minimum" : "nadmiar"}</span></span>
        <span>${a.ilosc} szt. (min ${a.stan_min} / opt ${a.stan_opt})</span>
      </div>
      <div class="meta-row"><span>${esc(a.komunikat)}</span>
        <span>${esc(a.lokalizacja)}</span></div>
    </div>`).join("");
}

function renderNiezgodnosci(lista) {
  const box = $("#niezgodnosciBox");
  if (!lista || !lista.length) { box.innerHTML = ""; return; }
  box.innerHTML = lista.map((n) => `
    <div class="card" style="border-left:5px solid #c1402e">
      <div class="row1"><span><b>⚠ Potrzebne przeliczenie: ${esc(n.symbol)}</b></span>
        <span>różnica ${n.roznica > 0 ? "+" : ""}${n.roznica} szt.</span></div>
      <div class="meta-row"><span>${esc(n.komunikat)}</span></div>
      <div class="card-actions">
        <input type="number" min="0" class="policzona" data-for="${n.bearing_id}"
               placeholder="ile faktycznie?" style="width:150px">
        <button class="btn small primary" data-count="${n.bearing_id}">Zatwierdź przeliczenie</button>
      </div>
    </div>`).join("");
  box.querySelectorAll("[data-count]").forEach((b) =>
    b.addEventListener("click", () => zatwierdzPrzeliczenie(b.dataset.count)));
}

async function zatwierdzPrzeliczenie(id) {
  const pole = document.querySelector(`.policzona[data-for="${id}"]`);
  const ile = parseInt(pole.value, 10);
  if (isNaN(ile) || ile < 0) { toast("Wpisz policzoną liczbę sztuk."); return; }
  const r = await api("/api/inconsistencies/confirm", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bearing_id: id, ilosc: ile }),
  });
  toast(`Zapisano ${r.ilosc} szt. (korekta ${r.korekta > 0 ? "+" : ""}${r.korekta} w dzienniku).`);
  loadBearings();
}

function renderScalenia(lista) {
  const box = $("#scaleniaBox");
  if (!lista || !lista.length) { box.innerHTML = ""; return; }
  box.innerHTML = lista.map((s) => {
    const gdzie = s.wpisy.map((w) => `${w.ilosc} szt. w ${esc(w.lokalizacja)}`).join(" + ");
    const etykieta = s.rodzaj === "duplikat" ? "Zdublowany wpis" : "Rozproszone po lokalizacjach";
    return `<div class="card" style="border-left:5px solid #c1402e">
      <div class="row1"><span><b>⚠ ${etykieta}: ${esc(s.symbol)}</b></span>
        <span>${s.lacznie} szt. łącznie</span></div>
      <div class="meta-row"><span>${gdzie} — ${esc(s.powod)}</span></div>
      <div class="card-actions">
        <button class="btn small primary" data-merge="${esc(s.symbol)}" data-cel="${s.cel_id || ""}">
          Scal w jeden wpis${s.rodzaj === "rozproszone" ? " (" + esc(s.cel) + ")" : ""}</button>
      </div>
    </div>`;
  }).join("");
  box.querySelectorAll("[data-merge]").forEach((b) =>
    b.addEventListener("click", () => scalLozyska(b.dataset.merge, b.dataset.cel)));
}

async function scalLozyska(symbol, celId) {
  if (!confirm(`Scalić wszystkie wpisy "${symbol}" w jeden?\n\n` +
               "Sztuki zostaną zsumowane przez dziennik ruchów - nic nie zniknie.")) return;
  const r = await api("/api/consolidation/merge", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, cel_id: celId || null }),
  });
  toast(`Scalono ${symbol}: ${r.lacznie} szt. w ${r.lokalizacja}.`);
  loadBearings();
}

async function przeniesLozysko(id, celId) {
  const b = state.bearings.find((x) => x.id === id);
  if (!b) return;
  await api(`/api/bearings/${id}`, {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      symbol: b.symbol, typ: b.typ, d: b.d, D: b.D, B: b.B, ilosc: b.ilosc,
      zrodlo: b.zrodlo, uwagi: b.uwagi, regal_id: celId, reczny_przydzial: true,
    }),
  });
  toast(`Przeniesiono ${b.symbol}.`);
  loadBearings();
}

async function deleteBearing(id) {
  const b = state.bearings.find((x) => x.id === id);
  if (!confirm(`Usunąć łożysko ${b ? b.symbol : ""}?`)) return;
  await api(`/api/bearings/${id}`, { method: "DELETE" });
  toast("Usunięto łożysko.");
  loadBearings();
}

// --------------------------------------------------------- modal łożyska ----

function fillTypeSelectRaw(selectEl, selected) {
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
  if ($("#f_weryfikacja")) $("#f_weryfikacja").checked = !!(b && b.do_weryfikacji);
  $("#f_symbol").value = b ? b.symbol : "";
  $("#f_d").value = b && b.d != null ? b.d : "";
  $("#f_D").value = b && b.D != null ? b.D : "";
  $("#f_B").value = b && b.B != null ? b.B : "";
  $("#f_ilosc").value = b ? b.ilosc : 1;
  $("#f_uwagi").value = b ? b.uwagi || "" : "";
  $("#f_stan_min").value = b && b.stan_min ? b.stan_min : "";
  $("#f_stan_opt").value = b && b.stan_opt ? b.stan_opt : "";
  $("#f_zapotrzebowanie").value = b && b.zapotrzebowanie ? b.zapotrzebowanie : "";

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
    ai: "Źródło danych: modele AI (propozycja - zweryfikuj suwmiarką)",
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

async function askAI() {
  const symbol = $("#f_symbol").value.trim();
  if (!symbol) { toast("Wpisz symbol łożyska."); return; }
  const btn = $("#btnAskAI");
  btn.disabled = true; btn.textContent = "Pytam modele...";
  try {
    const r = await api("/api/ai/lookup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol }),
    });
    if (r.znaleziono) {
      $("#f_d").value = r.d; $("#f_D").value = r.D; $("#f_B").value = r.B;
      if (r.typ) fillTypeSelect($("#f_typ"), r.typ);
      state.chosenSource = "ai";
      setSourceNote("ai");
      toast(`AI: ${r.zgodnych} z ${r.odpytanych} modeli zgodnych. ${r.uwaga}`);
    } else {
      toast(r.uwaga || "Modele nie znają tego oznaczenia.");
    }
  } catch (e) {
    toast("Zapytanie do AI nieudane: " + e.message);
  } finally {
    btn.disabled = false; btn.textContent = "Zapytaj AI";
  }
}

const czat = { historia: [] };

function renderChat() {
  const log = $("#chatLog");
  if (!czat.historia.length) {
    log.innerHTML = '<div class="row"><span>Brak wiadomości. Zadaj pytanie poniżej.</span></div>';
    return;
  }
  log.innerHTML = czat.historia.map((w) => {
    const kto = w.role === "user" ? "Ty" : "Asystent";
    const tresc = esc(w.content).replace(/\n/g, "<br>");
    return `<div class="row" style="display:block"><strong>${kto}:</strong><br>${tresc}</div>`;
  }).join("");
  log.scrollTop = log.scrollHeight;
}

async function chatSend() {
  const input = $("#chatInput");
  const tekst = input.value.trim();
  if (!tekst) return;
  czat.historia.push({ role: "user", content: tekst });
  input.value = "";
  renderChat();

  const btn = $("#btnChatSend");
  btn.disabled = true; btn.textContent = "Myślę...";
  try {
    const r = await api("/api/ai/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ wiadomosci: czat.historia, dostawca: $("#aiProvider").value }),
    });
    if (r.blad) {
      toast("Asystent: " + r.blad);
      czat.historia.pop();
    } else {
      czat.historia.push({ role: "assistant", content: r.odpowiedz });
    }
  } catch (e) {
    toast("Asystent nieosiągalny: " + e.message);
    czat.historia.pop();
  } finally {
    btn.disabled = false; btn.textContent = "Wyślij";
    renderChat();
  }
}

async function initChat() {
  try {
    const r = await api("/api/ai/providers");
    if (!r.dostawcy.length) return;
    $("#aiProvider").innerHTML = r.dostawcy.map((d) =>
      `<option value="${esc(d)}" ${d === r.domyslny ? "selected" : ""}>${esc(d)} (${esc(r.modele[d] || "")})</option>`
    ).join("");
    $("#btnChatSend").addEventListener("click", chatSend);
    $("#btnChatClear").addEventListener("click", () => { czat.historia = []; renderChat(); });
    $("#chatInput").addEventListener("keydown", (e) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) chatSend();
    });
    renderChat();
  } catch (_) { /* brak AI - zakładka pozostaje pusta */ }
}

async function initAI() {
  try {
    const r = await api("/api/ai/available");
    if (r.available) $("#btnAskAI").style.display = "inline-block";
  } catch (_) { /* brak AI - przycisk zostaje ukryty */ }
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

  // Progi zapisujemy osobnym wywołaniem - to decyzja zaopatrzeniowa, oddzielona od
  // danych technicznych łożyska (patrz ustaw_progi w database.py).
  const doWeryfikacji = $("#f_weryfikacja") ? $("#f_weryfikacja").checked : false;
  const progi = {
    stan_min: parseInt($("#f_stan_min").value || "0", 10),
    stan_opt: parseInt($("#f_stan_opt").value || "0", 10),
    zapotrzebowanie: parseInt($("#f_zapotrzebowanie").value || "0", 10),
  };

  let bearingId = state.editingId;
  if (state.editingId) {
    await api(`/api/bearings/${state.editingId}`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    toast("Zapisano zmiany.");
  } else {
    const r = await api("/api/bearings", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    bearingId = r.id;
    toast("Dodano łożysko.");
  }
  if (bearingId) {
    await api(`/api/bearings/${bearingId}/weryfikacja`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ do_weryfikacji: doWeryfikacji }),
    });
    await api(`/api/bearings/${bearingId}/progi`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(progi),
    });
  }
  closeBearingModal();
  loadBearings();
}

// ---------------------------------------------------------------- regały ----

async function loadShelves() {
  state.shelves = await api("/api/shelves");
  renderShelves();
}

const POZIOMY_PODRZEDNE = { "regał": "półka", "półka": "szuflada", "szuflada": "skrytka", "skrytka": "skrytka" };

async function addShelfNode(parentId, poziomTyp) {
  const nazwa = prompt(`Nazwa (${poziomTyp}):`);
  if (!nazwa || !nazwa.trim()) return;
  await api("/api/shelves", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nazwa: nazwa.trim(), parent_id: parentId, poziom_typ: poziomTyp }),
  });
  toast("Dodano " + poziomTyp + ".");
  loadShelves();
}

async function deleteShelfNode(id, nazwa) {
  if (!confirm(`Usunąć "${nazwa}" wraz ze wszystkim, co jest pod spodem?\n\n` +
               "Łożyska NIE zostaną skasowane - stracą tylko przypisanie do lokalizacji.")) return;
  const r = await api(`/api/shelves/${id}`, { method: "DELETE" });
  toast(`Usunięto ${r.usunietych} lokalizacji.`);
  loadShelves();
}

// Który regał jest pokazany i które gałęzie są zwinięte - zapamiętane między wizytami.
const widokRegalow = {
  wybrany: localStorage.getItem("wybranyRegal") || "",
  zwiniete: new Set(JSON.parse(localStorage.getItem("zwinieteWezly") || "[]")),
};

function zapiszWidok() {
  localStorage.setItem("wybranyRegal", widokRegalow.wybrany);
  localStorage.setItem("zwinieteWezly", JSON.stringify([...widokRegalow.zwiniete]));
}

/** Sumy Z CAŁEJ GAŁĘZI - regał ma pokazywać ile leży w nim łącznie, także w skrytkach. */
function sumyGalezi(wezel, wszystkie) {
  let pozycje = wezel.pozycje, sztuki = wezel.sztuki;
  for (const dziecko of wszystkie.filter((w) => w.parent_id === wezel.id)) {
    const s = sumyGalezi(dziecko, wszystkie);
    pozycje += s.pozycje; sztuki += s.sztuki;
  }
  return { pozycje, sztuki };
}

function maDzieci(id, wszystkie) {
  return wszystkie.some((w) => w.parent_id === id);
}

// Krótkie wyjaśnienie typu tam, gdzie się go wybiera. Dopisane dla serii wstawkowych,
// bo UC208 i ES208 mają ten sam otwór i tę samą średnicę zewnętrzną (40x80 mm) i bez
// podpowiedzi nie da się ich odróżnić z samej nazwy typu.
const OPISY_TYPOW = {
  "wstawkowe (UC)": "Do opraw; kulista powierzchnia zewnętrzna (samonastawne w oprawie). " +
    "Mocowane DWOMA WKRĘTAMI dociskowymi, szeroki pierścień wewnętrzny.",
  "wstawkowe (ES)": "Do opraw; kulista powierzchnia zewnętrzna (samonastawne w oprawie). " +
    "Mocowane MIMOŚRODOWYM PIERŚCIENIEM zaciskowym, węższy pierścień wewnętrzny niż UC.",
  "wstawkowe (RAE/INA)": "INA/Schaeffler; liczba w oznaczeniu to WPROST otwór w mm " +
    "(RAE35 = 35 mm). UWAGA: RAE ma pierścień zewnętrzny WALCOWY, a GRAE KULISTY - " +
    "tylko GRAE kompensuje niewspółosiowość wału.",
  "stożkowe calowe (Timken)": "Numeracja calowa - z oznaczenia NIE da się odczytać otworu. " +
    "Często sam pierścień (cone albo cup), sprawdź, czy masz komplet.",
};

function podepnijOpisTypu() {
  const sel = document.getElementById("f_typ");
  if (sel && !sel.dataset.opisPodpiety) {
    sel.addEventListener("change", pokazOpisTypu);
    sel.dataset.opisPodpiety = "1";
  }
}

function pokazOpisTypu() {
  podepnijOpisTypu();
  const el = document.getElementById("opisTypu");
  if (!el) return;
  el.textContent = OPISY_TYPOW[document.getElementById("f_typ").value] || "";
}

function renderShelves() {
  const list = $("#shelvesList");
  const wszystkie = state.shelves;
  const korzenie = wszystkie.filter((w) => !w.parent_id).sort((a, b) => b.poziom - a.poziom);

  // Lista wyboru regału; "" = wszystkie.
  const picker = $("#shelfPicker");
  if (picker) {
    if (widokRegalow.wybrany && !wszystkie.some((w) => w.id === widokRegalow.wybrany)) {
      widokRegalow.wybrany = "";      // wybrany regał zniknął (skasowany)
    }
    picker.innerHTML = `<option value="">— wszystkie regały —</option>` +
      korzenie.map((r) => {
        const s = sumyGalezi(r, wszystkie);
        return `<option value="${r.id}" ${r.id === widokRegalow.wybrany ? "selected" : ""}>` +
               `${esc(r.nazwa)} (${s.pozycje} poz. / ${s.sztuki} szt.)</option>`;
      }).join("");
  }

  list.innerHTML = "";
  const doPokazania = widokRegalow.wybrany
    ? korzenie.filter((r) => r.id === widokRegalow.wybrany)
    : korzenie;

  if (!doPokazania.length) {
    list.innerHTML = '<div class="row"><span>Brak regałów. Dodaj pierwszy przyciskiem „+ Nowy regał”.</span></div>';
    return;
  }

  const rysuj = (wezel, glebokosc) => {
    const dzieci = wszystkie.filter((w) => w.parent_id === wezel.id).sort((a, b) => b.poziom - a.poziom);
    const zwiniety = widokRegalow.zwiniete.has(wezel.id);
    const podrzedny = POZIOMY_PODRZEDNE[wezel.poziom_typ] || "skrytka";
    const suma = sumyGalezi(wezel, wszystkie);
    const wlasne = wezel.sztuki;

    const card = document.createElement("div");
    card.className = "card shelf-card";
    card.dataset.id = wezel.id;
    // Zakresy średnic zniknęły z formularza (magazyn opisujemy wymiarami półek), ale
    // nadal jadą przy zapisie - inaczej edycja nazwy kasowałaby je po cichu.
    card.dataset.dmin = wezel.d_min == null ? "" : wezel.d_min;
    card.dataset.dmax = wezel.d_max == null ? "" : wezel.d_max;
    card.style.marginLeft = (glebokosc * 24) + "px";
    // Sumy z gałęzi pokazujemy tylko wtedy, gdy różnią się od własnych - inaczej
    // przy liściach byłaby to ta sama liczba dwa razy.
    const licznik = dzieci.length && suma.sztuki !== wlasne
      ? `<span>W tej gałęzi: <b>${suma.pozycje}</b> poz. / <b>${suma.sztuki}</b> szt.</span>` +
        `<span>Wprost tutaj: <b>${wezel.pozycje}</b> / <b>${wlasne}</b></span>`
      : `<span>Pozycje: <b>${wezel.pozycje}</b></span><span>Sztuki: <b>${wlasne}</b></span>`;

    // Zapełnienie liczone z wymiarów półki (patrz pojemnosc.py). Pokazujemy je tylko
    // dla półek ZMIERZONYCH - przy pozostałych nie ma z czego liczyć.
    const proc = wezel.zajete_procent;
    const zajetosc = proc == null ? "" :
      `<span class="zajetosc" style="color:${proc >= 100 ? "#b3261e" : proc >= 85 ? "#8a6d00" : "inherit"}">` +
      `Zajęte: <b>${proc}%</b></span>`;
    const nieMiesci = (wezel.niemieszczace || []).length
      ? `<div class="hint" style="color:#b3261e">Nie mieści się: ` +
        wezel.niemieszczace.map((n) => `${esc(n.symbol)} (${esc(n.powod)})`).join("; ") + `</div>`
      : "";

    card.innerHTML = `
      <div class="row1">
        <span>
          ${dzieci.length ? `<button class="btn small" data-toggle="${wezel.id}">${zwiniety ? "▸" : "▾"}</button>` : ""}
          <span class="badge">${esc(wezel.poziom_typ)}</span>
          ${wezel.bufor ? '<span class="badge" style="background:#e0a92b;color:#1a1a1a">bufor</span>' : ""}
        </span>
        <span class="shelf-counts">${licznik}${zajetosc}</span>
      </div>
      <div class="fields">
        <label>Kolejność</label><input class="s-poziom" type="number" value="${wezel.poziom}">
        <label>Nazwa</label><input class="s-nazwa" value="${esc(wezel.nazwa)}">
        <label title="Zmierz miarą. Puste = nie liczymy pojemności tej półki.">Szerokość [cm]</label>
        <input class="s-szer" inputmode="decimal" value="${wezel.szerokosc_cm == null ? "" : wezel.szerokosc_cm}" placeholder="—">
        <label>Głębokość [cm]</label>
        <input class="s-glab" inputmode="decimal" value="${wezel.glebokosc_cm == null ? "" : wezel.glebokosc_cm}" placeholder="—">
        <label title="Prześwit do następnej półki, nie grubość deski.">Prześwit [cm]</label>
        <input class="s-wys" inputmode="decimal" value="${wezel.wysokosc_cm == null ? "" : wezel.wysokosc_cm}" placeholder="—">
        <label title="Miejsce odkładcze na czas liczenia. Bufor bywa przepełniony i to nie jest błąd, więc appka o tym nie alarmuje - i nigdy nie kieruje tam łożysk na stałe.">Bufor</label>
        <label class="bufor-label"><input class="s-bufor" type="checkbox" ${wezel.bufor ? "checked" : ""}> miejsce tymczasowe</label>
        <label title="Puste = lokalizacja ogólna, dobierana po średnicy. Wpisany typ ma pierwszeństwo przed średnicą.">Tylko typy</label>
        <input class="s-typy" value="${esc(wezel.typy || "")}" placeholder="np. wstawkowe (UC)" list="listaTypow">
      </div>
      ${nieMiesci}
      <div class="card-actions">
        <button class="btn small" data-add="${wezel.id}" data-typ="${esc(podrzedny)}">+ ${esc(podrzedny)}</button>
        <button class="btn small danger" data-delnode="${wezel.id}" data-nazwa="${esc(wezel.nazwa)}">Usuń</button>
      </div>
    `;
    list.appendChild(card);
    if (!zwiniety) dzieci.forEach((d) => rysuj(d, glebokosc + 1));
  };
  doPokazania.forEach((r) => rysuj(r, 0));

  list.querySelectorAll("[data-add]").forEach((b) =>
    b.addEventListener("click", () => addShelfNode(b.dataset.add, b.dataset.typ)));
  list.querySelectorAll("[data-delnode]").forEach((b) =>
    b.addEventListener("click", () => deleteShelfNode(b.dataset.delnode, b.dataset.nazwa)));
  list.querySelectorAll("[data-toggle]").forEach((b) =>
    b.addEventListener("click", () => {
      const id = b.dataset.toggle;
      widokRegalow.zwiniete.has(id) ? widokRegalow.zwiniete.delete(id) : widokRegalow.zwiniete.add(id);
      zapiszWidok(); renderShelves();
    }));
}

async function saveShelves() {
  const cards = $$("#shelvesList .shelf-card");
  try {
    for (const card of cards) {
      const id = card.dataset.id;
      const payload = {
        nazwa: card.querySelector(".s-nazwa").value.trim(),
        poziom: parseInt(card.querySelector(".s-poziom").value, 10),
        d_min: numOrNull(card.dataset.dmin),
        d_max: numOrNull(card.dataset.dmax),
        typy: card.querySelector(".s-typy").value.trim(),
        szerokosc_cm: numOrNull(card.querySelector(".s-szer").value),
        glebokosc_cm: numOrNull(card.querySelector(".s-glab").value),
        wysokosc_cm: numOrNull(card.querySelector(".s-wys").value),
        bufor: card.querySelector(".s-bufor").checked,
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
  const dl = document.createElement("datalist");
  dl.id = "listaTypow";
  dl.innerHTML = state.types.map((t) => `<option value="${esc(t)}">`).join("");
  document.body.appendChild(dl);

  $("#searchInput").addEventListener("input", debounce(loadBearings, 250));
  $("#addBearingBtn").addEventListener("click", () => openBearingModal(null));
  $("#btnCancelBearing").addEventListener("click", closeBearingModal);
  $("#bearingOverlay").addEventListener("click", (e) => { if (e.target.id === "bearingOverlay") closeBearingModal(); });
  $("#btnFetchBySymbol").addEventListener("click", fetchBySymbol);
  $("#btnFetchByDims").addEventListener("click", fetchByDimensions);
  $("#btnAskAI").addEventListener("click", askAI);
  initAI();
  initChat();
  $("#btnSaveBearing").addEventListener("click", saveBearing);
  $("#btnDeleteBearing").addEventListener("click", async () => {
    if (state.editingId) { await deleteBearing(state.editingId); closeBearingModal(); }
  });

  $("#saveShelvesBtn").addEventListener("click", saveShelves);
  $("#reassignBtn").addEventListener("click", reassignAll);
  $("#btnAddRoot").addEventListener("click", () => addShelfNode(null, "regał"));
  $("#shelfPicker").addEventListener("change", (e) => {
    widokRegalow.wybrany = e.target.value; zapiszWidok(); renderShelves();
  });
  $("#btnExpandAll").addEventListener("click", () => {
    widokRegalow.zwiniete.clear(); zapiszWidok(); renderShelves();
  });
  $("#btnCollapseAll").addEventListener("click", () => {
    state.shelves.forEach((w) => widokRegalow.zwiniete.add(w.id));
    zapiszWidok(); renderShelves();
  });

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


// Opis typu musi nadążać za KAŻDĄ zmianą typu - także tą automatyczną, z rozpoznania
// symbolu - a nie tylko za ręcznym wyborem z listy. Dlatego opakowujemy funkcję
// wypełniającą listę, zamiast wieszać się wyłącznie na zdarzeniu "change".
function fillTypeSelect(select, value) {
  fillTypeSelectRaw(select, value);
  if (select && select.id === "f_typ") pokazOpisTypu();
}
