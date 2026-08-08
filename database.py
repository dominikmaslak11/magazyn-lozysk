"""
Warstwa dostępu do danych (SQLite) dla magazynu łożysk.

Dwie tabele:
  - shelves  (regały): 9 regałów, każdy ma "poziom" (1 = najniższy/na dole,
    9 = najwyższy/na górze) oraz zakres średnicy zewnętrznej [d_min, d_max),
    który decyduje o automatycznym przydziale.
  - bearings (łożyska): symbol, typ, wymiary, ilość, przypisany regał oraz
    flaga reczny_przydzial - gdy ustawiona, automatyczne przeliczanie regałów
    NIE rusza danego łożyska (ręczna ingerencja użytkownika ma pierwszeństwo).

ID rekordów to UUID (tekst), nie liczby - dzięki temu telefony mogą tworzyć
nowe łożyska OFFLINE bez ryzyka kolizji identyfikatorów przy późniejszej
synchronizacji z serwerem (patrz sync_state()/apply_sync_push() niżej).

Kasowanie jest "miękkie" (kolumna deleted_at) - dzięki temu skasowanie
łożyska na jednym urządzeniu poprawnie propaguje się przy synchronizacji do
pozostałych urządzeń zamiast zniknąć tylko lokalnie.

Plik bazy danych leży CELOWO poza katalogiem z kodem aplikacji (patrz DB_DIR
poniżej), żeby aktualizacja/podmiana plików programu nigdy go nie nadpisała
ani nie skasowała. Dodatkowo dostępne są funkcje eksportu/importu - do robienia
kopii zapasowych i przenoszenia danych między urządzeniami/instalacjami.
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

# Lokalizacja danych - domyślnie w katalogu domowym użytkownika, poza kodem
# aplikacji, żeby `git pull` / podmiana plików nigdy nie ruszyły bazy.
# Można nadpisać zmienną środowiskową LOZYSKA_DATA_DIR (przydatne np. przy
# uruchamianiu kilku instancji albo w kontenerze).
DB_DIR = Path(os.environ.get("LOZYSKA_DATA_DIR", str(Path.home() / ".lozyska_data")))
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "lozyska.db"
BACKUP_DIR = DB_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
MAX_AUTO_BACKUPS = 20

SCHEMA_VERSION = 2  # v2 = UUID id + updated_at/deleted_at (obsługa synchronizacji)

# Domyślne, edytowalne w GUI zakresy średnicy zewnętrznej (mm) dla 9 regałów.
# poziom 1 = regał najniższy (duże łożyska), poziom 9 = najwyższy (małe łożyska).
DEFAULT_SHELVES = [
    (1, "Regał 1 (dół)", 200.0, None),
    (2, "Regał 2", 150.0, 200.0),
    (3, "Regał 3", 115.0, 150.0),
    (4, "Regał 4", 90.0, 115.0),
    (5, "Regał 5", 72.0, 90.0),
    (6, "Regał 6", 55.0, 72.0),
    (7, "Regał 7", 42.0, 55.0),
    (8, "Regał 8", 30.0, 42.0),
    (9, "Regał 9 (góra)", 0.0, 30.0),
]


@dataclass
class Bearing:
    id: str
    symbol: str
    typ: str
    d: float | None
    D: float | None
    B: float | None
    ilosc: int
    regal_id: str | None
    reczny_przydzial: bool
    zrodlo: str
    uwagi: str
    updated_at: str = ""
    deleted_at: str | None = None


@dataclass
class Shelf:
    id: str
    nazwa: str
    poziom: int
    d_min: float | None
    d_max: float | None
    updated_at: str = ""
    deleted_at: str | None = None


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# --------------------------------------------------------------- schemat ----

def init_db() -> None:
    conn = get_connection()
    with conn:
        existing_tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "bearings" not in existing_tables:
            _create_v2_schema(conn)
            _seed_default_shelves(conn)
        else:
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(bearings)")}
            if "updated_at" not in cols:
                _migrate_v1_to_v2(conn)
    conn.close()


def _create_v2_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE shelves (
            id TEXT PRIMARY KEY,
            nazwa TEXT NOT NULL,
            poziom INTEGER NOT NULL,
            d_min REAL,
            d_max REAL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        )
    """)
    conn.execute("CREATE UNIQUE INDEX idx_shelves_poziom ON shelves(poziom) WHERE deleted_at IS NULL")
    conn.execute("""
        CREATE TABLE bearings (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            typ TEXT DEFAULT 'kulkowe zwykłe',
            d REAL,
            D_out REAL,
            B REAL,
            ilosc INTEGER NOT NULL DEFAULT 0,
            regal_id TEXT REFERENCES shelves(id) ON DELETE SET NULL,
            reczny_przydzial INTEGER NOT NULL DEFAULT 0,
            zrodlo TEXT DEFAULT 'recznie',
            uwagi TEXT DEFAULT '',
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        )
    """)


def _seed_default_shelves(conn: sqlite3.Connection) -> None:
    ts = now_iso()
    conn.executemany(
        "INSERT INTO shelves (id, nazwa, poziom, d_min, d_max, updated_at, deleted_at) "
        "VALUES (?, ?, ?, ?, ?, ?, NULL)",
        [(new_id(), nazwa, poziom, d_min, d_max, ts) for poziom, nazwa, d_min, d_max in DEFAULT_SHELVES],
    )


def _migrate_v1_to_v2(conn: sqlite3.Connection) -> None:
    """Migruje starą bazę (id = liczba całkowita, bez updated_at/deleted_at) na schemat v2 (UUID).

    Uruchamia się automatycznie, dokładnie raz, przy pierwszym starcie serwera po
    aktualizacji. Robi pełny, spójny backup pliku bazy PRZED migracją (patrz make_backup),
    więc w razie czegokolwiek złego oryginalne dane są odzyskiwalne.
    """
    conn.commit()
    make_backup(label="przed-migracja-v2")

    conn.execute("ALTER TABLE shelves RENAME TO shelves_v1")
    conn.execute("ALTER TABLE bearings RENAME TO bearings_v1")
    _create_v2_schema(conn)

    ts = now_iso()
    id_map: dict[int, str] = {}
    for row in conn.execute("SELECT * FROM shelves_v1"):
        uid = new_id()
        id_map[row["id"]] = uid
        conn.execute(
            "INSERT INTO shelves (id, nazwa, poziom, d_min, d_max, updated_at, deleted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, NULL)",
            (uid, row["nazwa"], row["poziom"], row["d_min"], row["d_max"], ts),
        )

    for row in conn.execute("SELECT * FROM bearings_v1"):
        old_regal = row["regal_id"]
        new_regal = id_map.get(old_regal) if old_regal is not None else None
        conn.execute(
            "INSERT INTO bearings (id, symbol, typ, d, D_out, B, ilosc, regal_id, "
            "reczny_przydzial, zrodlo, uwagi, updated_at, deleted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
            (new_id(), row["symbol"], row["typ"] or "", row["d"], row["D_out"], row["B"],
             row["ilosc"], new_regal, row["reczny_przydzial"], row["zrodlo"], row["uwagi"], ts),
        )

    conn.execute("DROP TABLE shelves_v1")
    conn.execute("DROP TABLE bearings_v1")


# ---------------------------------------------------------------- regały ----

def get_shelves() -> list[Shelf]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM shelves WHERE deleted_at IS NULL ORDER BY poziom DESC"
    ).fetchall()
    conn.close()
    return [_row_to_shelf(r) for r in rows]


def update_shelf(shelf_id: str, nazwa: str, poziom: int, d_min: float | None, d_max: float | None) -> None:
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE shelves SET nazwa=?, poziom=?, d_min=?, d_max=?, updated_at=? WHERE id=?",
            (nazwa, poziom, d_min, d_max, now_iso(), shelf_id),
        )
    conn.close()


def shelf_counts() -> dict[str, tuple[int, int]]:
    """regal_id -> (liczba pozycji, suma sztuk)"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT regal_id, COUNT(*) AS pozycje, COALESCE(SUM(ilosc), 0) AS sztuki "
        "FROM bearings WHERE regal_id IS NOT NULL AND deleted_at IS NULL GROUP BY regal_id"
    ).fetchall()
    conn.close()
    return {r["regal_id"]: (r["pozycje"], r["sztuki"]) for r in rows}


def suggest_shelf_id(outer_diameter: float | None) -> str | None:
    """Dobiera regał na podstawie średnicy zewnętrznej D wg bieżących zakresów."""
    if outer_diameter is None:
        return None
    shelves = get_shelves()  # posortowane poziom malejąco: od największego do najmniejszego
    for shelf in shelves:
        lo = shelf.d_min if shelf.d_min is not None else float("-inf")
        hi = shelf.d_max if shelf.d_max is not None else float("inf")
        if lo <= outer_diameter < hi:
            return shelf.id
    # poza zdefiniowanymi zakresami: przypnij do skrajnego regału
    if not shelves:
        return None
    biggest = max(shelves, key=lambda s: s.poziom)
    smallest = min(shelves, key=lambda s: s.poziom)
    return biggest.id if outer_diameter >= (biggest.d_min or 0) else smallest.id


def reassign_all_auto() -> int:
    """Przelicza regał_id dla wszystkich łożysk BEZ ręcznej ingerencji. Zwraca liczbę zmienionych."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, D_out FROM bearings WHERE reczny_przydzial = 0 AND deleted_at IS NULL"
    ).fetchall()
    changed = 0
    with conn:
        for row in rows:
            new_shelf = suggest_shelf_id(row["D_out"])
            conn.execute("UPDATE bearings SET regal_id=?, updated_at=? WHERE id=?",
                         (new_shelf, now_iso(), row["id"]))
            changed += 1
    conn.close()
    return changed


# --------------------------------------------------------------- łożyska ----

def get_bearings(search: str = "") -> list[Bearing]:
    conn = get_connection()
    if search:
        rows = conn.execute(
            "SELECT * FROM bearings WHERE deleted_at IS NULL AND symbol LIKE ? ORDER BY symbol",
            (f"%{search}%",),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM bearings WHERE deleted_at IS NULL ORDER BY symbol").fetchall()
    conn.close()
    return [_row_to_bearing(r) for r in rows]


def get_bearing(bearing_id: str) -> Bearing | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM bearings WHERE id=? AND deleted_at IS NULL", (bearing_id,)).fetchone()
    conn.close()
    return _row_to_bearing(row) if row else None


def add_bearing(symbol: str, typ: str, d: float | None, D: float | None, B: float | None,
                 ilosc: int, zrodlo: str, uwagi: str = "",
                 regal_id: str | None = None, reczny_przydzial: bool = False) -> str:
    if regal_id is None and not reczny_przydzial:
        regal_id = suggest_shelf_id(D)
    bearing_id = new_id()
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO bearings (id, symbol, typ, d, D_out, B, ilosc, regal_id, "
            "reczny_przydzial, zrodlo, uwagi, updated_at, deleted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
            (bearing_id, symbol, typ, d, D, B, ilosc, regal_id, int(reczny_przydzial), zrodlo, uwagi, now_iso()),
        )
    conn.close()
    return bearing_id


def update_bearing(bearing_id: str, symbol: str, typ: str, d: float | None, D: float | None, B: float | None,
                    ilosc: int, zrodlo: str, uwagi: str,
                    regal_id: str | None, reczny_przydzial: bool) -> None:
    if not reczny_przydzial:
        regal_id = suggest_shelf_id(D)
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE bearings SET symbol=?, typ=?, d=?, D_out=?, B=?, ilosc=?, regal_id=?, "
            "reczny_przydzial=?, zrodlo=?, uwagi=?, updated_at=? WHERE id=?",
            (symbol, typ, d, D, B, ilosc, regal_id, int(reczny_przydzial), zrodlo, uwagi, now_iso(), bearing_id),
        )
    conn.close()


def delete_bearing(bearing_id: str) -> None:
    """Kasowanie jest miękkie (deleted_at), żeby poprawnie propagowało się przy synchronizacji."""
    conn = get_connection()
    with conn:
        conn.execute("UPDATE bearings SET deleted_at=?, updated_at=? WHERE id=?",
                     (now_iso(), now_iso(), bearing_id))
    conn.close()


def _row_to_bearing(row: sqlite3.Row) -> Bearing:
    return Bearing(
        id=row["id"], symbol=row["symbol"], typ=row["typ"] or "", d=row["d"], D=row["D_out"], B=row["B"],
        ilosc=row["ilosc"], regal_id=row["regal_id"],
        reczny_przydzial=bool(row["reczny_przydzial"]), zrodlo=row["zrodlo"], uwagi=row["uwagi"],
        updated_at=row["updated_at"], deleted_at=row["deleted_at"],
    )


def _row_to_shelf(row: sqlite3.Row) -> Shelf:
    return Shelf(
        id=row["id"], nazwa=row["nazwa"], poziom=row["poziom"], d_min=row["d_min"], d_max=row["d_max"],
        updated_at=row["updated_at"], deleted_at=row["deleted_at"],
    )


# ------------------------------------------------------------- synchronizacja ----
#
# Model: serwer (ten plik) jest jedynym centralnym węzłem ("hub"). Telefony mają
# lokalną kopię (Room/SQLite) i synchronizują się WYŁĄCZNIE przez serwer, nigdy
# bezpośrednio między sobą.
#
# Algorytm (patrz też Android: SyncEngine.kt):
#   1. Telefon wysyła (push) rekordy, które ZMIENIŁ LOKALNIE od swojej ostatniej
#      udanej synchronizacji (porównanie wyłącznie względem WŁASNEGO zegara -
#      nigdy względem zegara serwera, żeby uniknąć problemów z rozjazdem czasu
#      między urządzeniami).
#   2. Serwer bezwarunkowo nadpisuje swój stan przychodzącymi rekordami (upsert
#      po ID) i znaczy je WŁASNYM znacznikiem czasu (updated_at = teraz na
#      serwerze). To celowo prosta reguła "kto ostatni dotrze do serwera,
#      wygrywa" - dla magazynu łożysk edytowanego przez kilka osób to w pełni
#      wystarczające, bez budowania UI do ręcznego rozstrzygania konfliktów.
#   3. Serwer odsyła PEŁNY bieżący stan (włącznie z rekordami skasowanymi -
#      "nagrobki" z deleted_at, żeby kasowanie poprawnie propagowało się na
#      inne urządzenia).
#   4. Telefon podmienia swoją lokalną kopię 1:1 na to, co dostał (proste i
#      odporne na błędy - przy setkach rekordów kompletnie tanie).

def sync_state() -> dict:
    """Pełny stan (WŁĄCZNIE ze skasowanymi - nagrobki) do zsynchronizowania z klientem."""
    conn = get_connection()
    shelves = [_row_to_shelf(r) for r in conn.execute("SELECT * FROM shelves")]
    bearings = [_row_to_bearing(r) for r in conn.execute("SELECT * FROM bearings")]
    conn.close()
    return {
        "server_time": now_iso(),
        "shelves": [asdict(s) for s in shelves],
        "bearings": [asdict(b) for b in bearings],
    }


def apply_sync_push(shelves_in: list[dict], bearings_in: list[dict]) -> None:
    """Przyjmuje rekordy zmienione lokalnie na urządzeniu klienckim i bezwarunkowo
    je zapisuje (upsert po id), stemplując je czasem serwera."""
    conn = get_connection()
    ts = now_iso()
    with conn:
        for s in shelves_in:
            exists = conn.execute("SELECT 1 FROM shelves WHERE id=?", (s["id"],)).fetchone()
            if exists:
                conn.execute(
                    "UPDATE shelves SET nazwa=?, poziom=?, d_min=?, d_max=?, updated_at=?, deleted_at=? WHERE id=?",
                    (s["nazwa"], s["poziom"], s.get("d_min"), s.get("d_max"), ts, s.get("deleted_at"), s["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO shelves (id, nazwa, poziom, d_min, d_max, updated_at, deleted_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (s["id"], s["nazwa"], s["poziom"], s.get("d_min"), s.get("d_max"), ts, s.get("deleted_at")),
                )
        for b in bearings_in:
            exists = conn.execute("SELECT 1 FROM bearings WHERE id=?", (b["id"],)).fetchone()
            values_common = (
                b["symbol"], b.get("typ", ""), b.get("d"), b.get("D"), b.get("B"), b.get("ilosc", 0),
                b.get("regal_id"), int(b.get("reczny_przydzial", False)), b.get("zrodlo", "recznie"),
                b.get("uwagi", ""), ts, b.get("deleted_at"),
            )
            if exists:
                conn.execute(
                    "UPDATE bearings SET symbol=?, typ=?, d=?, D_out=?, B=?, ilosc=?, regal_id=?, "
                    "reczny_przydzial=?, zrodlo=?, uwagi=?, updated_at=?, deleted_at=? WHERE id=?",
                    values_common + (b["id"],),
                )
            else:
                conn.execute(
                    "INSERT INTO bearings (symbol, typ, d, D_out, B, ilosc, regal_id, reczny_przydzial, "
                    "zrodlo, uwagi, updated_at, deleted_at, id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    values_common + (b["id"],),
                )
    conn.close()


# --------------------------------------------------- backup / eksport / import ----

def make_backup(label: str = "auto") -> Path:
    """Robi spójną kopię pliku bazy (bezpieczną nawet przy równoczesnym zapisie) do backups/."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"lozyska_{timestamp}_{label}.db"
    src_conn = sqlite3.connect(DB_PATH)
    dest_conn = sqlite3.connect(dest)
    with dest_conn:
        src_conn.backup(dest_conn)
    src_conn.close()
    dest_conn.close()
    _prune_old_backups()
    return dest


def _prune_old_backups() -> None:
    backups = sorted(BACKUP_DIR.glob("lozyska_*.db"), key=lambda p: p.stat().st_mtime)
    while len(backups) > MAX_AUTO_BACKUPS:
        backups.pop(0).unlink(missing_ok=True)


def list_backups() -> list[dict]:
    backups = sorted(BACKUP_DIR.glob("lozyska_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"nazwa": p.name, "rozmiar_kb": round(p.stat().st_size / 1024, 1),
              "data": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")} for p in backups]


def export_db_snapshot(dest_path: str | Path) -> Path:
    """Eksportuje spójną kopię całej bazy (.db) - do pobrania/skopiowania gdziekolwiek."""
    dest_path = Path(dest_path)
    src_conn = sqlite3.connect(DB_PATH)
    dest_conn = sqlite3.connect(dest_path)
    with dest_conn:
        src_conn.backup(dest_conn)
    src_conn.close()
    dest_conn.close()
    return dest_path


def export_json_dict() -> dict:
    """Eksport w czytelnym formacie JSON (łatwy do przejrzenia/scalenia ręcznie)."""
    return {
        "wersja": 2,
        "eksport_z_dnia": now_iso(),
        "regaly": [asdict(s) for s in get_shelves()],
        "lozyska": [asdict(b) for b in get_bearings()],
    }


def import_db_file(src_path: str | Path) -> None:
    """Nadpisuje bieżącą bazę zawartością pliku .db. Robi backup przed nadpisaniem."""
    make_backup(label="przed-importem")
    src_conn = sqlite3.connect(src_path)
    dest_conn = sqlite3.connect(DB_PATH)
    with dest_conn:
        src_conn.backup(dest_conn)
    src_conn.close()
    dest_conn.close()


def import_json_dict(data: dict, mode: str = "zastap") -> tuple[int, int]:
    """Importuje dane z eksportu JSON.

    mode="zastap"  - czyści obecne łożyska i regały, wstawia z pliku,
    mode="dolacz"  - dopisuje łożyska z pliku jako nowe pozycje (regały bez zmian).
    Zwraca (liczba_regalow, liczba_lozysk) zaimportowanych.
    """
    make_backup(label="przed-importem-json")
    conn = get_connection()
    shelves_data = data.get("regaly", [])
    bearings_data = data.get("lozyska", [])
    ts = now_iso()

    with conn:
        if mode == "zastap":
            conn.execute("DELETE FROM bearings")
            conn.execute("DELETE FROM shelves")
            for s in shelves_data:
                conn.execute(
                    "INSERT INTO shelves (id, nazwa, poziom, d_min, d_max, updated_at, deleted_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, NULL)",
                    (s.get("id") or new_id(), s["nazwa"], s["poziom"], s["d_min"], s["d_max"], ts),
                )
        for b in bearings_data:
            conn.execute(
                "INSERT INTO bearings (id, symbol, typ, d, D_out, B, ilosc, regal_id, "
                "reczny_przydzial, zrodlo, uwagi, updated_at, deleted_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                (new_id(), b["symbol"], b.get("typ", ""), b["d"], b["D"], b["B"], b["ilosc"],
                 b.get("regal_id"), int(b.get("reczny_przydzial", False)), b.get("zrodlo", "recznie"),
                 b.get("uwagi", ""), ts),
            )
    conn.close()
    return len(shelves_data), len(bearings_data)


def reset_to_defaults() -> None:
    """Kasuje wszystkie łożyska i przywraca domyślne 9 regałów. Robi backup przed czyszczeniem."""
    make_backup(label="przed-resetem")
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM bearings")
        conn.execute("DELETE FROM shelves")
        _seed_default_shelves(conn)
    conn.close()
