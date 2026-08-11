"""
Testy parsera pola wyszukiwania (search_query.py).

Przypadki są celowo IDENTYCZNE z SearchQueryTest.kt w appce Android - obie
implementacje muszą rozumieć ten sam zapis, bo opis składni w UI jest wspólny.

Uruchomienie:
    python tests/test_search_query.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from search_query import parse_dimensions


def test_pelne_wymiary():
    w = parse_dimensions("25x52x15")
    assert (w.d, w.D, w.B) == (25.0, 52.0, 15.0)


def test_dwa_wymiary_szerokosc_dowolna():
    w = parse_dimensions("25x52")
    assert (w.d, w.D, w.B) == (25.0, 52.0, None)


def test_puste_miejsca_oznaczaja_dowolny_wymiar():
    assert (parse_dimensions("x52").d, parse_dimensions("x52").D) == (None, 52.0)
    assert (parse_dimensions("25x").d, parse_dimensions("25x").D) == (25.0, None)
    w = parse_dimensions("x52x15")
    assert (w.d, w.D, w.B) == (None, 52.0, 15.0)


def test_spacje_dzialaja_jak_x():
    w = parse_dimensions("25 52 15")
    assert (w.d, w.D, w.B) == (25.0, 52.0, 15.0)


def test_ulamki_z_kropka_i_przecinkiem():
    assert parse_dimensions("20x47x15.25").B == 15.25
    assert parse_dimensions("20x47x15,25").B == 15.25


def test_wielka_litera_X_i_znak_mnozenia():
    assert parse_dimensions("25X52").D == 52.0
    assert parse_dimensions("25×52").D == 52.0


def test_pojedyncza_liczba_to_symbol():
    # Kluczowe rozróżnienie: "6205" musi trafić do szukania po symbolu.
    for s in ["6205", "25", "30204"]:
        assert parse_dimensions(s) is None, f"{s} powinno być traktowane jak symbol"


def test_tekst_i_smieci_to_nie_wymiary():
    for s in ["", "   ", "NU205", "UC 206", "x", "xx", "25x52x15x20", "abc x def"]:
        assert parse_dimensions(s) is None, f"{s!r} nie powinno być wymiarami"


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
