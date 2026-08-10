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
MIN_CLIENT_VERSION = "1.1.0"


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
    if db.get_bearing(bearing_id) is None:
        abort(404)
    db.update_bearing(
        bearing_id, symbol=payload["symbol"], typ=payload.get("typ", ""),
        d=payload.get("d"), D=payload.get("D"), B=payload.get("B"),
        ilosc=int(payload.get("ilosc", 0)), zrodlo=payload.get("zrodlo", SOURCE_MANUAL),
        uwagi=payload.get("uwagi", ""), regal_id=payload.get("regal_id"),
        reczny_przydzial=bool(payload.get("reczny_przydzial", False)),
    )
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
                     _to_float(payload.get("d_min")), _to_float(payload.get("d_max")))
    return jsonify({"ok": True})


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
                        payload.get("barcode_aliases", []))
    return jsonify(_with_version(db.sync_state()))


# --------------------------------------- aliasy kodów kreskowych (opakowania) ----

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
        "reczny_przydzial": b.reczny_przydzial, "zrodlo": b.zrodlo, "uwagi": b.uwagi,
    }


def _shelf_to_dict(s: db.Shelf, counts: dict[int, tuple[int, int]]) -> dict:
    pozycje, sztuki = counts.get(s.id, (0, 0))
    return {
        "id": s.id, "nazwa": s.nazwa, "poziom": s.poziom,
        "d_min": s.d_min, "d_max": s.d_max, "pozycje": pozycje, "sztuki": sztuki,
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
