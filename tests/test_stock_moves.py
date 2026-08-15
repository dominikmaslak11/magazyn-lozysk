"""
Testy ruchów magazynowych (delta) zamiast nadpisywania ilości.

Sedno problemu, który to naprawia: ilość to LICZNIK. Reguła „kto ostatni zsynchronizuje,
ten wygrywa” jest w porządku dla nazwy czy uwag, ale przy liczniku po cichu gubi zmiany -
gdy jedna osoba weźmie offline 2 sztuki, a druga 1, jedna z tych zmian znika bez śladu.

Uruchomienie:
    python tests/test_stock_moves.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Każdy test dostaje własną, pustą bazę - inaczej testy zależałyby od kolejności.
_TMP = tempfile.mkdtemp(prefix="lozyska_test_")
import os
os.environ["LOZYSKA_DATA_DIR"] = _TMP

import database as db


def _swieza_baza():
    """Czysta baza na każdy test (kasujemy plik i budujemy schemat od nowa)."""
    if db.DB_PATH.exists():
        db.DB_PATH.unlink()
    db.init_db()


def _dto(bearing_id: str, **nadpisz) -> dict:
    baza = {
        "id": bearing_id, "symbol": "6205", "typ": "kulkowe zwykłe",
        "d": 25, "D": 52, "B": 15, "ilosc": 0, "regal_id": None,
        "reczny_przydzial": False, "zrodlo": "offline", "uwagi": "", "deleted_at": None,
    }
    baza.update(nadpisz)
    return baza


def test_dwie_osoby_offline_nie_gubia_sobie_zmian():
    """Scenariusz, który przed tą zmianą kończył się cichą utratą jednej ze zmian."""
    _swieza_baza()
    bid = db.add_bearing(symbol="6205", typ="", d=25, D=52, B=15, ilosc=10, zrodlo="offline")

    db.apply_sync_push([], [_dto(bid)], [], [{"id": "A", "bearing_id": bid, "delta": -2}])
    db.apply_sync_push([], [_dto(bid)], [], [{"id": "B", "bearing_id": bid, "delta": -1}])

    assert db.get_bearing(bid).ilosc == 7, "10 - 2 - 1 = 7"


def test_ponowna_wysylka_nie_liczy_dwa_razy():
    """Idempotencja: gdy odpowiedź serwera zginie, telefon wyśle ruch ponownie.
    Bez deduplikacji naprawa jednego błędu wprowadziłaby drugi."""
    _swieza_baza()
    bid = db.add_bearing(symbol="6205", typ="", d=25, D=52, B=15, ilosc=10, zrodlo="offline")
    ruch = [{"id": "powtorka", "bearing_id": bid, "delta": -3}]

    db.apply_sync_push([], [_dto(bid)], [], ruch)
    assert db.get_bearing(bid).ilosc == 7
    db.apply_sync_push([], [_dto(bid)], [], ruch)   # ta sama wysyłka jeszcze raz
    db.apply_sync_push([], [_dto(bid)], [], ruch)   # i jeszcze raz
    assert db.get_bearing(bid).ilosc == 7, "ruch o tym samym id wolno zastosować tylko raz"


def test_stan_nie_schodzi_ponizej_zera():
    _swieza_baza()
    bid = db.add_bearing(symbol="6205", typ="", d=25, D=52, B=15, ilosc=2, zrodlo="offline")
    db.apply_sync_push([], [_dto(bid)], [], [{"id": "x", "bearing_id": bid, "delta": -50}])
    assert db.get_bearing(bid).ilosc == 0, "magazyn nie ma ujemnego stanu"


def test_edycja_innych_pol_nie_rusza_ilosci():
    """Telefon wysyła całe łożysko przy każdej zmianie - ilość nie może się przy tym cofnąć."""
    _swieza_baza()
    bid = db.add_bearing(symbol="6205", typ="", d=25, D=52, B=15, ilosc=5, zrodlo="offline")
    db.apply_sync_push([], [_dto(bid, uwagi="zmienione", ilosc=999)], [], [])
    b = db.get_bearing(bid)
    assert b.uwagi == "zmienione"
    assert b.ilosc == 5, "ilość zmienia się WYŁĄCZNIE przez ruchy magazynowe"


def test_nowe_lozysko_dostaje_stan_z_ruchu():
    """Nowa pozycja startuje od zera, a stan początkowy przychodzi jako ruch -
    dzięki temu wszystkie zmiany ilości idą jedną drogą."""
    _swieza_baza()
    nowe_id = "nowe-lozysko-1"
    db.apply_sync_push([], [_dto(nowe_id, symbol="6008")], [],
                        [{"id": "start", "bearing_id": nowe_id, "delta": 4}])
    assert db.get_bearing(nowe_id).ilosc == 4


def test_ruchy_sa_zapisywane_jako_historia():
    _swieza_baza()
    bid = db.add_bearing(symbol="6205", typ="", d=25, D=52, B=15, ilosc=10, zrodlo="offline")
    db.apply_sync_push([], [_dto(bid)], [], [
        {"id": "r1", "bearing_id": bid, "delta": -2},
        {"id": "r2", "bearing_id": bid, "delta": +5},
    ])
    ruchy = db.get_stock_moves(bid)
    assert len(ruchy) == 2, f"oczekiwano 2 ruchów, jest {len(ruchy)}"
    assert sum(r.delta for r in ruchy) == 3
    assert db.get_bearing(bid).ilosc == 13


if __name__ == "__main__":
    testy = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    bledy = 0
    for t in testy:
        try:
            t()
            print(f"  OK   {t.__name__}")
        except AssertionError as e:
            bledy += 1
            print(f"  BŁĄD {t.__name__}: {e}")
    print(f"\n{len(testy) - bledy}/{len(testy)} testów przeszło")
    sys.exit(1 if bledy else 0)
