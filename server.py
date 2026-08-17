"""
Magazyn Łożysk - serwer webowy (Flask).

Uruchomienie:
    python server.py
Domyślnie nasłuchuje na 0.0.0.0:8420, więc jest dostępny z telefonu w tej
samej sieci Wi-Fi pod adresem http://<adres-IP-komputera>:8420
"""
from __future__ import annotations

import hashlib
import io
import os
import secrets
import tempfile
from dataclasses import asdict
from pathlib import Path

from flask import (Flask, abort, jsonify, redirect, render_template, request,
                    send_file, session, url_for)

import ai_assist
import database as db
import lookup
from bearing_data import ALL_TYPES, SOURCE_MANUAL
from pdf_labels import build_bearing_qr_labels_pdf, build_shelf_labels_pdf

app = Flask(__name__)

# ------------------------------------------------------------ autoryzacja ----
#
# Serwer jest chroniony pojedynczym, współdzielonym tokenem. To celowo prosty model,
# dopasowany do tego, czym ta appka jest: prywatnym magazynem jednej osoby/warsztatu,
# a nie systemem wielu kont z rolami.
#
# Token leży w ~/.lozyska_data/token.txt (obok bazy, POZA katalogiem z kodem, żeby
# git pull nigdy go nie nadpisał) i generuje się sam przy pierwszym starcie.
#
# Jak trafia w żądaniu (dowolny z trzech sposobów):
#   * nagłówek  X-Auth-Token: <token>     <- tego używa appka Android
#   * nagłówek  Authorization: Bearer <token>
#   * ciasteczko sesji, po zalogowaniu przez stronę /login (wersja webowa)
#
# Świadome wyjątki (bez tokenu):
#   * /api/version - appka musi móc sprawdzić zgodność wersji ZANIM się uwierzytelni,
#     a i tak nie wycieka stąd nic poza numerem wersji,
#   * pliki statyczne, manifest i service worker - to nie są dane, tylko sama appka,
#   * /login - inaczej nie dałoby się zalogować.
#
# Wyłączenie (np. w pełni zaufana sieć domowa): LOZYSKA_AUTH_DISABLED=1.

AUTH_DISABLED = os.environ.get("LOZYSKA_AUTH_DISABLED", "") == "1"
TOKEN_PATH = db.DB_DIR / "token.txt"
# Ścieżki dostępne bez tokenu (patrz komentarz wyżej).
PUBLIC_ENDPOINTS = {"api_version", "login", "static", "manifest", "service_worker"}


def _load_or_create_token() -> str:
    """Czyta token z pliku; przy pierwszym uruchomieniu generuje nowy i zapisuje."""
    if TOKEN_PATH.exists():
        existing = TOKEN_PATH.read_text().strip()
        if existing:
            return existing
    token = secrets.token_urlsafe(24)
    TOKEN_PATH.write_text(token + "\n")
    # Token to sekret - plik tylko dla właściciela (bez znaczenia na Windows, stąd best-effort).
    try:
        os.chmod(TOKEN_PATH, 0o600)
    except OSError:
        pass
    return token


AUTH_TOKEN = _load_or_create_token()
# Klucz sesji jest wyprowadzony z tokenu, więc jest stały między restartami (nie wylogowuje
# przeglądarki przy każdym starcie), a jednocześnie unieważnia się razem ze zmianą tokenu.
app.secret_key = hashlib.sha256(("sesja:" + AUTH_TOKEN).encode()).digest()


def _token_from_request() -> str | None:
    header = request.headers.get("X-Auth-Token")
    if header:
        return header.strip()
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


@app.before_request
def _require_token():
    if AUTH_DISABLED or request.endpoint in PUBLIC_ENDPOINTS:
        return None
    # compare_digest zamiast == : porównanie w stałym czasie, żeby nie dało się
    # zgadywać tokenu mierząc czas odpowiedzi.
    supplied = _token_from_request()
    if supplied and secrets.compare_digest(supplied, AUTH_TOKEN):
        return None
    if session.get("auth") and secrets.compare_digest(str(session.get("auth")), AUTH_TOKEN):
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "Brak autoryzacji - podaj token (nagłówek X-Auth-Token)."}), 401
    return redirect(url_for("login", next=request.path))


@app.route("/login", methods=["GET", "POST"])
def login():
    if AUTH_DISABLED:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        supplied = (request.form.get("token") or "").strip()
        if secrets.compare_digest(supplied, AUTH_TOKEN):
            session["auth"] = AUTH_TOKEN
            session.permanent = True
            return redirect(request.args.get("next") or url_for("index"))
        error = "Nieprawidłowy token."
    return render_template("login.html", error=error), (401 if error else 200)


@app.route("/logout")
def logout():
    session.pop("auth", None)
    return redirect(url_for("login"))


# ----------------------------------------------------------------- wersja ----
# Pojedyncze źródło prawdy: plik VERSION w katalogu repo. MIN_CLIENT_VERSION
# to najstarsza wersja appki Android, która wciąż potrafi bezpiecznie
# zsynchronizować się z tym serwerem - podnieś ją ręcznie tylko wtedy, gdy
# robisz zmianę w formacie/API synchronizacji, która łamie starsze appki.
# Appka Android porównuje to ze swoim BuildConfig.VERSION_NAME przy każdej
# synchronizacji i blokuje zapis lokalny, jeśli jest za stara (patrz
# android-offline/.../sync/VersionCheck.kt).
APP_VERSION = (Path(__file__).parent / "VERSION").read_text().strip()
MIN_CLIENT_VERSION = "1.2.0"


def _with_version(payload: dict) -> dict:
    payload["server_version"] = APP_VERSION
    payload["min_client_version"] = MIN_CLIENT_VERSION
    return payload


@app.route("/api/version")
def api_version():
    return jsonify(_with_version({}))


# ------------------------------------------------------------------- strona ----

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/manifest.json")
def manifest():
    return app.send_static_file("manifest.json")


@app.route("/service-worker.js")
def service_worker():
    resp = app.send_static_file("service-worker.js")
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


# --------------------------------------------------------------------- API ----

@app.route("/api/types")
def api_types():
    return jsonify(ALL_TYPES)


@app.route("/api/bearings")
def api_bearings_list():
    search = request.args.get("search", "")
    bearings = db.get_bearings(search)
    shelves = {s.id: s for s in db.get_shelves()}
    return jsonify([_bearing_to_dict(b, shelves) for b in bearings])


@app.route("/api/bearings", methods=["POST"])
def api_bearings_add():
    payload = request.get_json(force=True)
    new_id = db.add_bearing(
        symbol=payload["symbol"], typ=payload.get("typ", ""),
        d=payload.get("d"), D=payload.get("D"), B=payload.get("B"),
        ilosc=int(payload.get("ilosc", 0)), zrodlo=payload.get("zrodlo", SOURCE_MANUAL),
        uwagi=payload.get("uwagi", ""), regal_id=payload.get("regal_id"),
        reczny_przydzial=bool(payload.get("reczny_przydzial", False)),
    )
    return jsonify({"id": new_id}), 201


@app.route("/api/bearings/<bearing_id>", methods=["PUT"])
def api_bearings_update(bearing_id):
    payload = request.get_json(force=True)
    biezace = db.get_bearing(bearing_id)
    if biezace is None:
        abort(404)
    nowa_ilosc = int(payload.get("ilosc", 0))
    # Ilość zmieniamy przez dziennik ruchów, nie wartością bezwzględną - dzięki temu
    # historia jest kompletna niezależnie od tego, czy zmiana przyszła z przeglądarki,
    # czy z telefonu, a reguła "ilość zmienia się WYŁĄCZNIE ruchami" nie ma wyjątków.
    db.update_bearing(
        bearing_id, symbol=payload["symbol"], typ=payload.get("typ", ""),
        d=payload.get("d"), D=payload.get("D"), B=payload.get("B"),
        ilosc=biezace.ilosc, zrodlo=payload.get("zrodlo", SOURCE_MANUAL),
        uwagi=payload.get("uwagi", ""), regal_id=payload.get("regal_id"),
        reczny_przydzial=bool(payload.get("reczny_przydzial", False)),
    )
    if nowa_ilosc != biezace.ilosc:
        db.apply_local_move(bearing_id, nowa_ilosc - biezace.ilosc, zrodlo="web")
    return jsonify({"ok": True})


@app.route("/api/bearings/<bearing_id>", methods=["DELETE"])
def api_bearings_delete(bearing_id):
    if db.get_bearing(bearing_id) is None:
        abort(404)
    db.delete_bearing(bearing_id)
    return jsonify({"ok": True})


@app.route("/api/lookup/symbol")
def api_lookup_symbol():
    symbol = request.args.get("symbol", "")
    result = lookup.lookup_by_symbol(symbol)
    return jsonify({
        "symbol": result.symbol, "d": result.d, "D": result.D, "B": result.B,
        "source": result.source, "typ": result.typ, "note": result.note,
    })


@app.route("/api/lookup/dimensions")
def api_lookup_dimensions():
    d = _to_float(request.args.get("d"))
    D = _to_float(request.args.get("D"))
    B = _to_float(request.args.get("B"))
    candidates = lookup.lookup_by_dimensions(d, D, B)
    result = [{"symbol": s, "d": bd, "D": bD, "B": bB, "typ": typ} for s, bd, bD, bB, typ in candidates[:8]]
    if not result:
        online_symbol = lookup.online_lookup_by_dimensions(d, D, B)
        if online_symbol:
            result = [{"symbol": online_symbol, "d": d, "D": D, "B": B, "typ": None, "online": True}]
    return jsonify(result)


@app.route("/api/shelves")
def api_shelves_list():
    shelves = db.get_shelves()
    counts = db.shelf_counts()
    return jsonify([_shelf_to_dict(s, counts) for s in shelves])


@app.route("/api/shelves/<shelf_id>", methods=["PUT"])
def api_shelves_update(shelf_id):
    payload = request.get_json(force=True)
    db.update_shelf(shelf_id, payload["nazwa"], int(payload["poziom"]),
                     _to_float(payload.get("d_min")), _to_float(payload.get("d_max")),
                     typy=payload.get("typy"))
    return jsonify({"ok": True})


@app.route("/api/shelves", methods=["POST"])
def api_shelves_add():
    """Dodaje węzeł lokalizacji: regał (bez rodzica) albo półkę/szufladę/skrytkę."""
    payload = request.get_json(force=True)
    nazwa = (payload.get("nazwa") or "").strip()
    if not nazwa:
        abort(400, "Podaj nazwę lokalizacji.")
    parent_id = payload.get("parent_id") or None
    if parent_id and db.get_shelf(parent_id) is None:
        abort(400, "Nadrzędna lokalizacja nie istnieje.")
    node_id = db.add_shelf(
        nazwa=nazwa, parent_id=parent_id,
        poziom_typ=(payload.get("poziom_typ") or "regał"),
        d_min=payload.get("d_min"), d_max=payload.get("d_max"),
        typy=payload.get("typy", ""),
    )
    return jsonify({"id": node_id}), 201


@app.route("/api/shelves/<shelf_id>", methods=["DELETE"])
def api_shelves_delete(shelf_id):
    """Kasuje lokalizację wraz z potomkami. Łożyska zostają - tracą tylko przypisanie."""
    if db.get_shelf(shelf_id) is None:
        abort(404)
    return jsonify({"usunietych": db.delete_shelf(shelf_id)})


@app.route("/api/shelves/reassign", methods=["POST"])
def api_shelves_reassign():
    changed = db.reassign_all_auto()
    return jsonify({"changed": changed})


# ---------------------------------------------------- synchronizacja (telefony) ----

@app.route("/api/sync/state")
def api_sync_state():
    """Pełny stan (włącznie ze skasowanymi rekordami - nagrobki) do zaciągnięcia przez klienta."""
    return jsonify(_with_version(db.sync_state()))


@app.route("/api/sync/push", methods=["POST"])
def api_sync_push():
    """Przyjmuje rekordy zmienione lokalnie na urządzeniu i odsyła pełny, zmergowany stan
    (patrz opis algorytmu w database.py nad sync_state/apply_sync_push)."""
    payload = request.get_json(force=True)
    db.apply_sync_push(payload.get("shelves", []), payload.get("bearings", []),
                        payload.get("barcode_aliases", []), payload.get("stock_moves", []))
    return jsonify(_with_version(db.sync_state()))


# --------------------------------------- aliasy kodów kreskowych (opakowania) ----

@app.route("/api/ai/available")
def api_ai_available():
    """Czy podpowiedzi AI są skonfigurowane - UI chowa przycisk, gdy nie ma kluczy."""
    return jsonify({"available": ai_assist.is_available()})


@app.route("/api/ai/lookup", methods=["POST"])
def api_ai_lookup():
    """Pyta modele AI o wymiary łożyska spoza katalogu.

    Wysyłamy do modeli WYŁĄCZNIE samo oznaczenie - nigdy stanu magazynu. Odpowiedzi
    przechodzą tę samą walidację co wyniki z wyszukiwarki (kod otworu ISO 15 +
    geometria), a wynik jest zawsze propozycją do zatwierdzenia przez człowieka.
    """
    payload = request.get_json(force=True)
    symbol = (payload.get("symbol") or "").strip()
    if not symbol:
        abort(400, "Podaj oznaczenie łożyska.")
    wynik = ai_assist.lookup(symbol)
    return jsonify({
        "symbol": wynik.symbol,
        "d": wynik.d, "D": wynik.D, "B": wynik.B, "typ": wynik.typ,
        "zgodnych": wynik.zgodnych, "odpytanych": wynik.odpytanych,
        "znaleziono": wynik.znaleziono,
        "uwaga": wynik.uwaga,
        "zrodlo": "ai",
        "odpowiedzi": [
            {"dostawca": o.dostawca, "d": o.d, "D": o.D, "B": o.B,
             "pewnosc": o.pewnosc, "blad": o.blad, "odrzucona": o.odrzucona}
            for o in wynik.odpowiedzi
        ],
    })


@app.route("/api/ai/chat", methods=["POST"])
def api_ai_chat():
    """Asystent-czat o magazynie. Domyślnie najnowszy Claude.

    UWAGA na prywatność: do modelu trafia zwięzły spis magazynu (symbole, wymiary,
    ilości, regały), bo bez niego asystent nie odpowie na pytania w stylu "czy mam
    coś 25x52". Można to wyłączyć polem bez_magazynu. Klucze API zostają na serwerze.
    """
    payload = request.get_json(force=True)
    wiadomosci = payload.get("wiadomosci") or []
    if not isinstance(wiadomosci, list) or not wiadomosci:
        abort(400, "Brak wiadomości.")
    wynik = ai_assist.chat(
        wiadomosci,
        dostawca=payload.get("dostawca"),
        bez_magazynu=bool(payload.get("bez_magazynu", False)),
    )
    return jsonify(wynik)


@app.route("/api/ai/providers")
def api_ai_providers():
    dostepni = sorted(ai_assist.load_keys())
    return jsonify({
        "dostawcy": dostepni,
        "domyslny": ai_assist.CZAT_DOMYSLNY if ai_assist.CZAT_DOMYSLNY in dostepni
                    else (dostepni[0] if dostepni else None),
        "modele": {d: ai_assist.CZAT_MODELE.get(d) for d in dostepni},
    })


@app.route("/api/suggestions")
def api_suggestions():
    """Podpowiedzi przełożenia łożysk - deterministyczne, bez udziału AI."""
    min_sztuk = int(request.args.get("min_sztuk", 1))
    sugestie = db.sugestie_przeniesien(min_sztuk=min_sztuk)
    return jsonify([asdict(s) for s in sugestie])


@app.route("/api/consolidation")
def api_consolidation():
    """Łożyska rozbite na kilka wpisów lub kilka lokalizacji - deterministycznie."""
    return jsonify([asdict(s) for s in db.sugestie_scalenia()])


@app.route("/api/consolidation/merge", methods=["POST"])
def api_consolidation_merge():
    """Scala wszystkie wpisy danego symbolu w jeden. Sztuki idą przez dziennik ruchów."""
    payload = request.get_json(force=True)
    symbol = (payload.get("symbol") or "").strip()
    if not symbol:
        abort(400, "Podaj symbol.")
    return jsonify(db.scal_lozyska(symbol, payload.get("cel_id")))


@app.route("/api/inconsistencies")
def api_inconsistencies():
    """Pozycje wymagające fizycznego przeliczenia (stan bez pokrycia w dzienniku)."""
    return jsonify([asdict(n) for n in db.niezgodnosci_stanu()])


@app.route("/api/inconsistencies/confirm", methods=["POST"])
def api_inconsistencies_confirm():
    """Zatwierdza wynik przeliczenia - różnica idzie do dziennika jako inwentaryzacja."""
    payload = request.get_json(force=True)
    bid = payload.get("bearing_id")
    if not bid or payload.get("ilosc") is None:
        abort(400, "Podaj bearing_id i ilosc.")
    wynik = db.potwierdz_stan(bid, int(payload["ilosc"]))
    if not wynik.get("ok"):
        abort(404)
    return jsonify(wynik)


@app.route("/api/stock-moves")
def api_stock_moves():
    """Historia ruchów magazynowych (przyjęcia/wydania). Bez parametru - cały magazyn."""
    bearing_id = request.args.get("bearing_id")
    shelves = {sh.id: sh for sh in db.get_shelves()}
    symbole = {b.id: b.symbol for b in db.get_bearings()}
    return jsonify([
        {**asdict(m), "symbol": symbole.get(m.bearing_id, "(usunięte)")}
        for m in db.get_stock_moves(bearing_id)
    ])


@app.route("/api/barcode-aliases")
def api_barcode_aliases():
    return jsonify([asdict(a) for a in db.get_barcode_aliases()])


@app.route("/api/barcode-lookup/<path:kod>")
def api_barcode_lookup(kod):
    """Zwraca symbol łożyska skojarzony z kodem z opakowania (albo null, gdy nieznany)."""
    return jsonify({"kod": kod, "symbol": db.find_symbol_by_barcode(kod)})


@app.route("/api/barcode-aliases", methods=["POST"])
def api_barcode_alias_set():
    payload = request.get_json(force=True)
    kod = (payload.get("kod") or "").strip()
    symbol = (payload.get("symbol") or "").strip()
    if not kod or not symbol:
        abort(400, "Wymagane pola: kod, symbol")
    return jsonify({"id": db.set_barcode_alias(kod, symbol), "kod": kod, "symbol": symbol})


@app.route("/api/barcode-aliases/<alias_id>", methods=["DELETE"])
def api_barcode_alias_delete(alias_id):
    db.delete_barcode_alias(alias_id)
    return jsonify({"ok": True})


# ------------------------------------------------------- backup / eksport / import ----

@app.route("/api/backups")
def api_backups():
    return jsonify(db.list_backups())


@app.route("/api/export/db")
def api_export_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    db.export_db_snapshot(tmp_path)
    data = tmp_path.read_bytes()
    tmp_path.unlink(missing_ok=True)
    return send_file(io.BytesIO(data), mimetype="application/x-sqlite3",
                      as_attachment=True, download_name="lozyska_backup.db")


@app.route("/api/export/json")
def api_export_json():
    data = db.export_json_dict()
    buf = io.BytesIO(__import__("json").dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
    return send_file(buf, mimetype="application/json",
                      as_attachment=True, download_name="lozyska_export.json")


@app.route("/api/export/shelf-labels-pdf")
def api_export_shelf_labels_pdf():
    pdf_bytes = build_shelf_labels_pdf()
    return send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf",
                      as_attachment=True, download_name="etykiety_regalow.pdf")


@app.route("/api/export/bearing-qr-labels-pdf")
def api_export_bearing_qr_labels_pdf():
    """Arkusz naklejek z kodami QR (jedna na łożysko) - do wycięcia i naklejenia.
    Zeskanowanie takiej naklejki appką Android otwiera łożysko z gotowym symbolem."""
    pdf_bytes = build_bearing_qr_labels_pdf()
    return send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf",
                      as_attachment=True, download_name="naklejki_qr_lozysk.pdf")


@app.route("/api/import/db", methods=["POST"])
def api_import_db():
    file = request.files.get("file")
    if not file:
        abort(400, "Brak pliku")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = Path(tmp.name)
    try:
        _validate_sqlite_bearings_db(tmp_path)
        db.import_db_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    return jsonify({"ok": True})


@app.route("/api/import/json", methods=["POST"])
def api_import_json():
    payload = request.get_json(force=True)
    mode = request.args.get("mode", "zastap")
    shelves_n, bearings_n = db.import_json_dict(payload, mode=mode)
    return jsonify({"regaly": shelves_n, "lozyska": bearings_n})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    db.reset_to_defaults()
    return jsonify({"ok": True})


# ---------------------------------------------------------------- helpery ----

def _bearing_to_dict(b: db.Bearing, shelves: dict[int, db.Shelf]) -> dict:
    shelf = shelves.get(b.regal_id)
    return {
        "id": b.id, "symbol": b.symbol, "typ": b.typ, "d": b.d, "D": b.D, "B": b.B,
        "ilosc": b.ilosc, "regal_id": b.regal_id,
        "regal_nazwa": shelf.nazwa if shelf else None,
        "sciezka": db.shelf_path(b.regal_id, shelves) if b.regal_id else None,
        "reczny_przydzial": b.reczny_przydzial, "zrodlo": b.zrodlo, "uwagi": b.uwagi,
    }


def _shelf_to_dict(s: db.Shelf, counts: dict[int, tuple[int, int]]) -> dict:
    pozycje, sztuki = counts.get(s.id, (0, 0))
    return {
        "id": s.id, "nazwa": s.nazwa, "poziom": s.poziom,
        "d_min": s.d_min, "d_max": s.d_max, "pozycje": pozycje, "sztuki": sztuki,
        "parent_id": s.parent_id, "poziom_typ": s.poziom_typ, "typy": s.typy,
    }


def _to_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def _validate_sqlite_bearings_db(path: Path) -> None:
    import sqlite3
    try:
        conn = sqlite3.connect(path)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
    except sqlite3.Error:
        abort(400, "To nie jest poprawny plik bazy SQLite.")
    if not {"bearings", "shelves"}.issubset(tables):
        abort(400, "Plik nie wygląda na kopię bazy Magazynu Łożysk (brak wymaganych tabel).")


def main():
    db.init_db()
    db.make_backup(label="start-serwera")
    port = int(os.environ.get("LOZYSKA_PORT", "8420"))

    print("=" * 62)
    if AUTH_DISABLED:
        print("  UWAGA: autoryzacja WYŁĄCZONA (LOZYSKA_AUTH_DISABLED=1).")
        print("  Każdy w tej sieci ma pełny dostęp do danych bez tokenu.")
    else:
        print("  Token dostępu (wpisz go w przeglądarce i w appce na telefonie):")
        print()
        print(f"      {AUTH_TOKEN}")
        print()
        print(f"  Zapisany w: {TOKEN_PATH}")
        print("  Zmiana tokenu: skasuj ten plik i zrestartuj serwer (wtedy trzeba")
        print("  wpisać nowy token na wszystkich urządzeniach).")
    print("=" * 62)

    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
