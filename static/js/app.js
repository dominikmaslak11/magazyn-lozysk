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
  return { offline: "baza offline", internet: "internet", recznie: "ręcznie", ai: "AI" }[zrodlo] || zrodlo;
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
    card.style.marginLeft = (glebokosc * 24) + "px";
    // Sumy z gałęzi pokazujemy tylko wtedy, gdy różnią się od własnych - inaczej
    // przy liściach byłaby to ta sama liczba dwa razy.
    const licznik = dzieci.length && suma.sztuki !== wlasne
      ? `<span>W tej gałęzi: <b>${suma.pozycje}</b> poz. / <b>${suma.sztuki}</b> szt.</span>` +
        `<span>Wprost tutaj: <b>${wezel.pozycje}</b> / <b>${wlasne}</b></span>`
      : `<span>Pozycje: <b>${wezel.pozycje}</b></span><span>Sztuki: <b>${wlasne}</b></span>`;

    card.innerHTML = `
      <div class="row1">
        <span>
          ${dzieci.length ? `<button class="btn small" data-toggle="${wezel.id}">${zwiniety ? "▸" : "▾"}</button>` : ""}
          <span class="badge">${esc(wezel.poziom_typ)}</span>
        </span>
        <span class="shelf-counts">${licznik}</span>
      </div>
      <div class="fields">
        <label>Kolejność</label><input class="s-poziom" type="number" value="${wezel.poziom}">
        <label>Nazwa</label><input class="s-nazwa" value="${esc(wezel.nazwa)}">
        <label>D od [mm]</label><input class="s-dmin" inputmode="decimal" value="${wezel.d_min == null ? "" : wezel.d_min}" placeholder="—">
        <label>D do [mm]</label><input class="s-dmax" inputmode="decimal" value="${wezel.d_max == null ? "" : wezel.d_max}" placeholder="bez limitu">
        <label title="Puste = lokalizacja ogólna, dobierana po średnicy. Wpisany typ ma pierwszeństwo przed średnicą.">Tylko typy</label>
        <input class="s-typy" value="${esc(wezel.typy || "")}" placeholder="np. wstawkowe (UC)" list="listaTypow">
      </div>
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
        d_min: numOrNull(card.querySelector(".s-dmin").value),
        d_max: numOrNull(card.querySelector(".s-dmax").value),
        typy: card.querySelector(".s-typy").value.trim(),
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
