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

from search_query import TOLERANCE, parse_dimensions

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

SCHEMA_VERSION = 6  # v6 = przypisanie typów łożysk do lokalizacji (kolumna typy)

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


# Poziomy hierarchii. Każdy jest OPCJONALNY - regał może mieć od razu skrytki albo
# nie mieć nic pod sobą. Kolejność w tej krotce to tylko podpowiedź dla UI, nie reguła.
POZIOMY = ("regał", "półka", "szuflada", "skrytka")


@dataclass
class Shelf:
    """Węzeł drzewa lokalizacji: regał, półka, szuflada albo skrytka.

    Hierarchia jest KONFIGUROWALNA i niesymetryczna - jeden regał może mieć półki
    z szufladami, a inny nic pod sobą. Dlatego to jedna, samo-referencyjna tabela
    (parent_id), a nie osobna tabela na każdy poziom: inaczej "regał bez półek, ale
    ze skrytkami" wymagałby pustych rekordów-wypełniaczy.

    Łożysko wskazuje na DOWOLNY węzeł (bearings.regal_id) - można je położyć wprost
    na regale albo w konkretnej skrytce, bez zmiany schematu.
    """
    id: str
    nazwa: str
    poziom: int
    d_min: float | None
    d_max: float | None
    updated_at: str = ""
    deleted_at: str | None = None
    parent_id: str | None = None
    poziom_typ: str = "regał"
    # Typy łożysk, dla których ta lokalizacja jest przeznaczona (oddzielone przecinkami).
    # Puste = lokalizacja ogólna, dobierana wyłącznie po średnicy zewnętrznej.
    # Po co: średnica to nie jedyne kryterium - wstawkowe UC/ES mają duże obudowy i
    # w praktyce trzyma się je razem, niezależnie od D.
    typy: str = ""


@dataclass
class BarcodeAlias:
    """Skojarzenie kodu kreskowego z opakowania (zwykle EAN-13, czyli numer handlowy
    producenta) z symbolem łożyska.

    Po co: kod EAN na pudełku NIE zawiera oznaczenia łożyska, tylko numer produktu w
    systemie sprzedaży. Skan takiego kodu sam z siebie nie mówi nic o tym, co jest w
    środku. Zamiast korzystać z płatnych i niekompletnych baz GTIN, appka pyta
    użytkownika RAZ ("co to za łożysko?") i zapamiętuje odpowiedź tutaj - kolejne skany
    tego samego pudełka, na dowolnym zsynchronizowanym urządzeniu, rozpoznają je od razu.
    """
    id: str
    kod: str
    symbol: str
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
        # v2 -> v3: dołożenie tabeli aliasów kodów kreskowych. Sama tabela jest pusta i
        # niezależna od reszty danych, więc migracja jest bezpieczna i nie wymaga backupu.
        existing_tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "barcode_aliases" not in existing_tables:
            _create_barcode_aliases_table(conn)
        # v3 -> v4: dziennik ruchów magazynowych. Tabela jest pusta i niezależna od reszty,
        # więc migracja niczego nie rusza w istniejących danych.
        if "stock_moves" not in existing_tables:
            _create_stock_moves_table(conn)
        # v4 -> v5: hierarchia lokalizacji. Dokładamy kolumny do istniejącej tabeli
        # zamiast tworzyć nową - dzięki temu bearings.regal_id, synchronizacja i encja
        # Room działają dalej bez zmian, a dotychczasowe regały stają się korzeniami.
        shelf_cols = {r["name"] for r in conn.execute("PRAGMA table_info(shelves)")}
        if "parent_id" not in shelf_cols:
            _migrate_v4_to_v5(conn)
            shelf_cols.add("parent_id")
        # v5 -> v6: lokalizacja może być dedykowana konkretnym typom łożysk.
        if "typy" not in shelf_cols:
            conn.execute("ALTER TABLE shelves ADD COLUMN typy TEXT NOT NULL DEFAULT ''")
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
            deleted_at TEXT,
            parent_id TEXT REFERENCES shelves(id) ON DELETE SET NULL,
            poziom_typ TEXT NOT NULL DEFAULT 'regał',
            typy TEXT NOT NULL DEFAULT ''
        )
    """)
    # UWAGA: celowo BEZ unikalnego indeksu na `poziom`. Przy hierarchii numer poziomu
    # powtarza się między gałęziami (półka 1 w regale A i półka 1 w regale B), więc
    # taki indeks blokowałby dodawanie dzieci.
    conn.execute("CREATE INDEX idx_shelves_parent ON shelves(parent_id)")
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


def _create_barcode_aliases_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE barcode_aliases (
            id TEXT PRIMARY KEY,
            kod TEXT NOT NULL,
            symbol TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        )
    """)
    # Jeden aktywny alias na kod - powtórne przypisanie nadpisuje poprzednie (patrz set_barcode_alias).
    conn.execute("CREATE UNIQUE INDEX idx_barcode_aliases_kod ON barcode_aliases(kod) WHERE deleted_at IS NULL")


def _migrate_v4_to_v5(conn: sqlite3.Connection) -> None:
    """Płaska lista regałów -> drzewo lokalizacji. Istniejące regały zostają korzeniami."""
    conn.execute("ALTER TABLE shelves ADD COLUMN parent_id TEXT REFERENCES shelves(id) ON DELETE SET NULL")
    conn.execute("ALTER TABLE shelves ADD COLUMN poziom_typ TEXT NOT NULL DEFAULT 'regał'")
    # Unikalny indeks na `poziom` musi zniknąć: w drzewie numery powtarzają się
    # między gałęziami, więc blokowałby dodawanie półek i skrytek.
    conn.execute("DROP INDEX IF EXISTS idx_shelves_poziom")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shelves_parent ON shelves(parent_id)")


def _create_stock_moves_table(conn: sqlite3.Connection) -> None:
    """Dziennik ruchów magazynowych (przyjęcia/wydania sztuk).

    Po co osobna tabela, skoro ilość jest już w `bearings`: ilość to LICZNIK, a licznika
    nie wolno synchronizować regułą "kto ostatni, ten lepszy". Gdy jedna osoba weźmie
    offline 2 sztuki, a druga 1, nadpisywanie wartością bezwzględną gubi jedną ze zmian
    bez śladu. Dlatego telefony wysyłają RÓŻNICE (-2, -1), a serwer je sumuje.

    `id` jest nadawane przez urządzenie i służy do DEDUPLIKACJI: jeśli odpowiedź serwera
    zginie po drodze i telefon wyśle ten sam ruch ponownie, drugi raz go nie zastosujemy.
    Bez tego naprawa jednego błędu (gubienie zmian) wprowadziłaby drugi (podwójne liczenie).
    """
    conn.execute("""
        CREATE TABLE stock_moves (
            id TEXT PRIMARY KEY,
            bearing_id TEXT NOT NULL,
            delta INTEGER NOT NULL,
            zrodlo TEXT DEFAULT '',
            applied_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX idx_stock_moves_bearing ON stock_moves(bearing_id, applied_at)")


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


def get_shelf(shelf_id: str) -> Shelf | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM shelves WHERE id=? AND deleted_at IS NULL", (shelf_id,)).fetchone()
    conn.close()
    return _row_to_shelf(row) if row else None


def add_shelf(nazwa: str, parent_id: str | None = None, poziom_typ: str = "regał",
               d_min: float | None = None, d_max: float | None = None, typy: str = "") -> str:
    """Dodaje węzeł lokalizacji. `parent_id=None` tworzy nowy regał (korzeń).

    Poziom (liczba) służy już tylko do sortowania w obrębie rodzeństwa - przy
    hierarchii to numer kolejny, nie globalna pozycja.
    """
    conn = get_connection()
    with conn:
        nastepny = conn.execute(
            "SELECT COALESCE(MAX(poziom), 0) + 1 FROM shelves WHERE deleted_at IS NULL "
            "AND parent_id IS ?", (parent_id,)).fetchone()[0]
        node_id = new_id()
        conn.execute(
            "INSERT INTO shelves (id, nazwa, poziom, d_min, d_max, updated_at, deleted_at, "
            "parent_id, poziom_typ, typy) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)",
            (node_id, nazwa, nastepny, d_min, d_max, now_iso(), parent_id, poziom_typ, (typy or "").strip()),
        )
    conn.close()
    return node_id


def delete_shelf(shelf_id: str) -> int:
    """Kasuje węzeł WRAZ Z POTOMKAMI (miękko). Łożyska nie znikają - tracą tylko
    przypisanie, żeby skasowanie półki nigdy nie kasowało zawartości magazynu.
    Zwraca liczbę skasowanych węzłów."""
    conn = get_connection()
    ts = now_iso()
    do_skasowania: list[str] = []
    with conn:
        kolejka = [shelf_id]
        while kolejka:
            biezacy = kolejka.pop()
            do_skasowania.append(biezacy)
            kolejka += [r["id"] for r in conn.execute(
                "SELECT id FROM shelves WHERE parent_id=? AND deleted_at IS NULL", (biezacy,))]
        for wid in do_skasowania:
            conn.execute("UPDATE bearings SET regal_id=NULL, updated_at=? WHERE regal_id=?", (ts, wid))
            conn.execute("UPDATE shelves SET deleted_at=?, updated_at=? WHERE id=?", (ts, ts, wid))
    conn.close()
    return len(do_skasowania)


def shelf_path(shelf_id: str | None, wezly: dict[str, Shelf] | None = None) -> str:
    """Czytelna ścieżka lokalizacji, np. "Regał 3 › Półka 2 › Szuflada 1"."""
    if not shelf_id:
        return ""
    if wezly is None:
        wezly = {s.id: s for s in get_shelves()}
    czesci: list[str] = []
    biezacy = shelf_id
    # Limit chroni przed zapętleniem, gdyby dane kiedykolwiek były niespójne.
    for _ in range(10):
        w = wezly.get(biezacy)
        if w is None:
            break
        czesci.append(w.nazwa)
        if not w.parent_id:
            break
        biezacy = w.parent_id
    return " › ".join(reversed(czesci))


def update_shelf(shelf_id: str, nazwa: str, poziom: int, d_min: float | None,
                  d_max: float | None, typy: str | None = None) -> None:
    conn = get_connection()
    with conn:
        if typy is None:
            conn.execute(
                "UPDATE shelves SET nazwa=?, poziom=?, d_min=?, d_max=?, updated_at=? WHERE id=?",
                (nazwa, poziom, d_min, d_max, now_iso(), shelf_id),
            )
        else:
            conn.execute(
                "UPDATE shelves SET nazwa=?, poziom=?, d_min=?, d_max=?, typy=?, updated_at=? WHERE id=?",
                (nazwa, poziom, d_min, d_max, typy.strip(), now_iso(), shelf_id),
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


def suggest_shelf_id(outer_diameter: float | None, typ: str | None = None) -> str | None:
    """Dobiera lokalizację dla łożyska.

    Kolejność kryteriów - typ jest WAŻNIEJSZY niż średnica, bo w praktyce trzyma się
    razem całe rodziny (wstawkowe UC/ES mają duże obudowy i leżą osobno niezależnie
    od D, tak samo bywa z igiełkowymi czy oporowymi):

      1. lokalizacja dedykowana temu typowi ORAZ pasująca zakresem D,
      2. lokalizacja dedykowana temu typowi (bez zakresu D albo D nieznane),
      3. lokalizacja ogólna (bez przypisanych typów) pasująca zakresem D,
      4. skrajna lokalizacja ogólna, gdy średnica wypada poza wszystkie zakresy.

    Dzięki temu wystarczy oznaczyć jedną półkę jako "wstawkowe (UC)", żeby wszystkie
    UC i ES lądowały razem, a reszta magazynu dalej sortowała się po średnicy.
    """
    wszystkie = get_shelves()
    if not wszystkie:
        return None

    def w_zakresie(s: Shelf) -> bool:
        if outer_diameter is None:
            return False
        lo = s.d_min if s.d_min is not None else float("-inf")
        hi = s.d_max if s.d_max is not None else float("inf")
        return lo <= outer_diameter < hi

    def ma_typ(s: Shelf) -> bool:
        if not typ or not s.typy:
            return False
        chciane = {t.strip().casefold() for t in s.typy.split(",") if t.strip()}
        return typ.strip().casefold() in chciane

    dedykowane = [s for s in wszystkie if ma_typ(s)]
    # 1) typ + średnica
    for s in dedykowane:
        if w_zakresie(s):
            return s.id
    # 2) sam typ - najgłębsza lokalizacja wygrywa (skrytka jest konkretniejsza niż regał)
    if dedykowane:
        wgId = {x.id: x for x in wszystkie}
        def glebokosc(s: Shelf) -> int:
            g, b, krok = 0, s.parent_id, 0
            while b and krok < 10:
                g += 1; b = wgId.get(b).parent_id if wgId.get(b) else None; krok += 1
            return g
        return max(dedykowane, key=glebokosc).id

    ogolne = [s for s in wszystkie if not s.typy]
    if outer_diameter is None:
        return None
    # 3) ogólna w zakresie
    for s in ogolne:
        if w_zakresie(s):
            return s.id
    # 4) poza zakresami - przypnij do skrajnej ogólnej
    if not ogolne:
        return None
    najwiekszy = max(ogolne, key=lambda s: s.poziom)
    najmniejszy = min(ogolne, key=lambda s: s.poziom)
    return najwiekszy.id if outer_diameter >= (najwiekszy.d_min or 0) else najmniejszy.id


def reassign_all_auto() -> int:
    """Przelicza regał_id dla wszystkich łożysk BEZ ręcznej ingerencji. Zwraca liczbę zmienionych."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, D_out, typ FROM bearings WHERE reczny_przydzial = 0 AND deleted_at IS NULL"
    ).fetchall()
    changed = 0
    with conn:
        for row in rows:
            new_shelf = suggest_shelf_id(row["D_out"], row["typ"])
            conn.execute("UPDATE bearings SET regal_id=?, updated_at=? WHERE id=?",
                         (new_shelf, now_iso(), row["id"]))
            changed += 1
    conn.close()
    return changed


# --------------------------------------------------------------- łożyska ----

def get_bearings(search: str = "") -> list[Bearing]:
    """Jedno pole wyszukiwania obsługuje dwa pytania: "czy mam 6205?" (po symbolu)
    i "czy mam coś 25x52?" (po wymiarach). O tym, które to jest, decyduje sam zapis -
    patrz search_query.py (i SearchQuery.kt po stronie appki)."""
    conn = get_connection()
    wymiary = parse_dimensions(search) if search else None

    if wymiary is not None:
        rows = conn.execute(
            "SELECT * FROM bearings WHERE deleted_at IS NULL"
            "  AND (:d IS NULL OR (d IS NOT NULL AND d BETWEEN :d - :tol AND :d + :tol))"
            "  AND (:D IS NULL OR (D_out IS NOT NULL AND D_out BETWEEN :D - :tol AND :D + :tol))"
            "  AND (:B IS NULL OR (B IS NOT NULL AND B BETWEEN :B - :tol AND :B + :tol))"
            " ORDER BY symbol",
            {"d": wymiary.d, "D": wymiary.D, "B": wymiary.B, "tol": TOLERANCE},
        ).fetchall()
    elif search:
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
        regal_id = suggest_shelf_id(D, typ)
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
        regal_id = suggest_shelf_id(D, typ)
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
    klucze = row.keys()
    return Shelf(
        id=row["id"], nazwa=row["nazwa"], poziom=row["poziom"], d_min=row["d_min"], d_max=row["d_max"],
        updated_at=row["updated_at"], deleted_at=row["deleted_at"],
        parent_id=row["parent_id"] if "parent_id" in klucze else None,
        poziom_typ=(row["poziom_typ"] if "poziom_typ" in klucze else None) or "regał",
        typy=(row["typy"] if "typy" in klucze else None) or "",
    )


@dataclass
class StockMove:
    """Pojedynczy ruch magazynowy: ile sztuk przybyło (+) albo ubyło (-)."""
    id: str
    bearing_id: str
    delta: int
    zrodlo: str
    applied_at: str


def get_stock_moves(bearing_id: str | None = None, limit: int = 200) -> list[StockMove]:
    """Historia ruchów - dla całego magazynu albo jednego łożyska, od najnowszych."""
    conn = get_connection()
    if bearing_id:
        rows = conn.execute(
            "SELECT * FROM stock_moves WHERE bearing_id=? ORDER BY applied_at DESC, rowid DESC LIMIT ?",
            (bearing_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM stock_moves ORDER BY applied_at DESC, rowid DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [StockMove(r["id"], r["bearing_id"], r["delta"], r["zrodlo"] or "", r["applied_at"])
            for r in rows]


def apply_local_move(bearing_id: str, delta: int, zrodlo: str = "web") -> None:
    """Zmiana stanu z poziomu serwera (wersja webowa) - też przez dziennik ruchów,
    żeby historia była kompletna niezależnie od tego, gdzie zmieniono ilość."""
    conn = get_connection()
    with conn:
        ts = now_iso()
        conn.execute(
            "INSERT INTO stock_moves (id, bearing_id, delta, zrodlo, applied_at) VALUES (?, ?, ?, ?, ?)",
            (new_id(), bearing_id, int(delta), zrodlo, ts),
        )
        conn.execute("UPDATE bearings SET ilosc = MAX(0, ilosc + ?), updated_at=? WHERE id=?",
                      (int(delta), ts, bearing_id))
    conn.close()


def _row_to_alias(row: sqlite3.Row) -> BarcodeAlias:
    return BarcodeAlias(
        id=row["id"], kod=row["kod"], symbol=row["symbol"],
        updated_at=row["updated_at"], deleted_at=row["deleted_at"],
    )


# ------------------------------------------- aliasy kodów kreskowych (opakowania) ----

def normalize_barcode(raw: str) -> str:
    """Kody z różnych skanerów potrafią przyjść z białymi znakami - porównujemy je
    zawsze po tej samej, znormalizowanej postaci."""
    return raw.strip()


def get_barcode_aliases() -> list[BarcodeAlias]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM barcode_aliases WHERE deleted_at IS NULL ORDER BY symbol").fetchall()
    conn.close()
    return [_row_to_alias(r) for r in rows]


def find_symbol_by_barcode(kod: str) -> str | None:
    """Zwraca symbol łożyska skojarzony z kodem z opakowania albo None, jeśli nieznany."""
    conn = get_connection()
    row = conn.execute(
        "SELECT symbol FROM barcode_aliases WHERE kod=? AND deleted_at IS NULL",
        (normalize_barcode(kod),),
    ).fetchone()
    conn.close()
    return row["symbol"] if row else None


def set_barcode_alias(kod: str, symbol: str) -> str:
    """Zapamiętuje (albo aktualizuje) skojarzenie kod -> symbol. Zwraca id rekordu."""
    kod = normalize_barcode(kod)
    symbol = symbol.strip()
    conn = get_connection()
    with conn:
        row = conn.execute(
            "SELECT id FROM barcode_aliases WHERE kod=? AND deleted_at IS NULL", (kod,)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE barcode_aliases SET symbol=?, updated_at=? WHERE id=?",
                (symbol, now_iso(), row["id"]),
            )
            alias_id = row["id"]
        else:
            alias_id = new_id()
            conn.execute(
                "INSERT INTO barcode_aliases (id, kod, symbol, updated_at, deleted_at) VALUES (?, ?, ?, ?, NULL)",
                (alias_id, kod, symbol, now_iso()),
            )
    conn.close()
    return alias_id


def delete_barcode_alias(alias_id: str) -> None:
    """Kasowanie miękkie - nagrobek propaguje się przy synchronizacji na inne urządzenia."""
    conn = get_connection()
    with conn:
        ts = now_iso()
        conn.execute("UPDATE barcode_aliases SET deleted_at=?, updated_at=? WHERE id=?", (ts, ts, alias_id))
    conn.close()


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
    aliases = [_row_to_alias(r) for r in conn.execute("SELECT * FROM barcode_aliases")]
    conn.close()
    return {
        "server_time": now_iso(),
        "shelves": [asdict(s) for s in shelves],
        "bearings": [asdict(b) for b in bearings],
        "barcode_aliases": [asdict(a) for a in aliases],
    }


def apply_sync_push(shelves_in: list[dict], bearings_in: list[dict],
                     aliases_in: list[dict] | None = None,
                     moves_in: list[dict] | None = None) -> None:
    """Przyjmuje rekordy zmienione lokalnie na urządzeniu klienckim i bezwarunkowo
    je zapisuje (upsert po id), stemplując je czasem serwera."""
    conn = get_connection()
    ts = now_iso()
    with conn:
        for s in shelves_in:
            exists = conn.execute("SELECT 1 FROM shelves WHERE id=?", (s["id"],)).fetchone()
            if exists:
                # parent_id/poziom_typ aktualizujemy TYLKO gdy klient je przysłał - starszy
                # klient ich nie zna i nie może przez to spłaszczyć hierarchii do zera.
                if "parent_id" in s or "poziom_typ" in s:
                    conn.execute(
                        "UPDATE shelves SET nazwa=?, poziom=?, d_min=?, d_max=?, updated_at=?, "
                        "deleted_at=?, parent_id=?, poziom_typ=?, typy=? WHERE id=?",
                        (s["nazwa"], s["poziom"], s.get("d_min"), s.get("d_max"), ts,
                         s.get("deleted_at"), s.get("parent_id"), s.get("poziom_typ") or "regał",
                         s.get("typy") or "", s["id"]),
                    )
                else:
                    conn.execute(
                        "UPDATE shelves SET nazwa=?, poziom=?, d_min=?, d_max=?, updated_at=?, deleted_at=? WHERE id=?",
                        (s["nazwa"], s["poziom"], s.get("d_min"), s.get("d_max"), ts, s.get("deleted_at"), s["id"]),
                    )
            else:
                conn.execute(
                    "INSERT INTO shelves (id, nazwa, poziom, d_min, d_max, updated_at, deleted_at, "
                    "parent_id, poziom_typ, typy) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (s["id"], s["nazwa"], s["poziom"], s.get("d_min"), s.get("d_max"), ts,
                     s.get("deleted_at"), s.get("parent_id"), s.get("poziom_typ") or "regał",
                     s.get("typy") or ""),
                )
        for b in bearings_in:
            exists = conn.execute("SELECT 1 FROM bearings WHERE id=?", (b["id"],)).fetchone()
            if exists:
                # UWAGA: celowo NIE nadpisujemy `ilosc`. Ilość to licznik i zmienia się
                # wyłącznie przez ruchy magazynowe (patrz moves_in niżej) - inaczej dwie
                # osoby edytujące offline gubiłyby sobie nawzajem zmiany stanu.
                conn.execute(
                    "UPDATE bearings SET symbol=?, typ=?, d=?, D_out=?, B=?, regal_id=?, "
                    "reczny_przydzial=?, zrodlo=?, uwagi=?, updated_at=?, deleted_at=? WHERE id=?",
                    (b["symbol"], b.get("typ", ""), b.get("d"), b.get("D"), b.get("B"),
                     b.get("regal_id"), int(b.get("reczny_przydzial", False)), b.get("zrodlo", "recznie"),
                     b.get("uwagi", ""), ts, b.get("deleted_at"), b["id"]),
                )
            else:
                # Nowe łożysko startuje od zera - jego stan początkowy przyjdzie jako ruch
                # magazynowy, dzięki czemu wszystkie zmiany ilości idą jedną, spójną drogą.
                conn.execute(
                    "INSERT INTO bearings (symbol, typ, d, D_out, B, ilosc, regal_id, reczny_przydzial, "
                    "zrodlo, uwagi, updated_at, deleted_at, id) VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?)",
                    (b["symbol"], b.get("typ", ""), b.get("d"), b.get("D"), b.get("B"),
                     b.get("regal_id"), int(b.get("reczny_przydzial", False)), b.get("zrodlo", "recznie"),
                     b.get("uwagi", ""), ts, b.get("deleted_at"), b["id"]),
                )

        # Ruchy magazynowe stosujemy PO wstawieniu łożysk, żeby ruch dotyczący nowo
        # utworzonej pozycji miał już do czego się odnieść.
        for m in (moves_in or []):
            move_id = m.get("id")
            if not move_id:
                continue
            # Deduplikacja: ten sam ruch wysłany ponownie (np. po zerwanym połączeniu)
            # nie może zostać policzony drugi raz.
            if conn.execute("SELECT 1 FROM stock_moves WHERE id=?", (move_id,)).fetchone():
                continue
            delta = int(m.get("delta", 0))
            bearing_id = m.get("bearing_id")
            if not bearing_id:
                continue
            conn.execute(
                "INSERT INTO stock_moves (id, bearing_id, delta, zrodlo, applied_at) VALUES (?, ?, ?, ?, ?)",
                (move_id, bearing_id, delta, m.get("zrodlo", ""), ts),
            )
            # Stan nie schodzi poniżej zera - to magazyn, nie konto bankowe.
            conn.execute(
                "UPDATE bearings SET ilosc = MAX(0, ilosc + ?), updated_at=? WHERE id=?",
                (delta, ts, bearing_id),
            )
        for a in (aliases_in or []):
            exists = conn.execute("SELECT 1 FROM barcode_aliases WHERE id=?", (a["id"],)).fetchone()
            if exists:
                conn.execute(
                    "UPDATE barcode_aliases SET kod=?, symbol=?, updated_at=?, deleted_at=? WHERE id=?",
                    (normalize_barcode(a["kod"]), a["symbol"], ts, a.get("deleted_at"), a["id"]),
                )
            else:
                # Ten sam kod mógł zostać skojarzony niezależnie na dwóch telefonach offline
                # (różne id, ten sam kod). Unikalny indeks dotyczy tylko rekordów żywych, więc
                # starsze skojarzenie chowamy jako nagrobek zamiast wywalać się na konflikcie.
                if a.get("deleted_at") is None:
                    conn.execute(
                        "UPDATE barcode_aliases SET deleted_at=?, updated_at=? WHERE kod=? AND deleted_at IS NULL",
                        (ts, ts, normalize_barcode(a["kod"])),
                    )
                conn.execute(
                    "INSERT INTO barcode_aliases (id, kod, symbol, updated_at, deleted_at) VALUES (?, ?, ?, ?, ?)",
                    (a["id"], normalize_barcode(a["kod"]), a["symbol"], ts, a.get("deleted_at")),
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
