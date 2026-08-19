"""Testy rachunku pojemności półek (pojemnosc.py)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pojemnosc import (  # noqa: E402
    ODSTEP_MM,
    REZERWA_NAD_STOSEM_MM,
    obciazenie_polki,
    powierzchnia_pozycji,
    proponowany_podzial,
    warstwy_w_stosie,
)


def test_stos_nie_wyzszy_niz_szerszy():
    # 6203: D=40, B=12. Prześwit 21 cm zmieściłby 13 sztuk na wysokość, ale taki
    # stos (16 cm przy 4 cm średnicy) przewraca się przy pierwszym dotknięciu.
    assert warstwy_w_stosie(40, 12, 210) == 3, "ogranicza stabilność, nie prześwit"
    # Ta sama sztuka na wyższej półce - nadal 3, bo ogranicza szerokość podstawy.
    assert warstwy_w_stosie(40, 12, 1420) == 3


def test_niska_polka_ogranicza_stos():
    # 6020: D=150, B=24. Stabilność pozwoliłaby na 6 sztuk, ale prześwit 10 cm
    # minus zapas na rękę zostawia miejsce tylko na 2.
    assert warstwy_w_stosie(150, 24, 100) == 2
    assert warstwy_w_stosie(150, 24, 1420) == 6, "tu ogranicza już tylko stabilność"


def test_lozysko_ktore_sie_nie_miesci():
    # Prześwit 6 cm, łożysko szerokie na 2.4 cm: 60 - 50 (zapas na rękę) = 10 mm < 24 mm.
    assert warstwy_w_stosie(150, 24, 60) == 0, "nie wejdzie nawet jedna sztuka z zapasem"


def test_zbyt_duza_srednica_nie_wchodzi_w_glebokosc():
    p = powierzchnia_pozycji("6020", D=150, B=24, ilosc=1,
                              szerokosc_mm=880, glebokosc_mm=100, wysokosc_mm=300)
    assert not p.miesci_sie
    assert "głębokości" in p.powod


def test_powierzchnia_uwzglednia_odstep_na_reke():
    # Jedna sztuka 6203 (D=40) zajmuje kwadrat o boku 40 + odstęp.
    p = powierzchnia_pozycji("6203", D=40, B=12, ilosc=1,
                              szerokosc_mm=880, glebokosc_mm=500, wysokosc_mm=210)
    assert p.miesci_sie and p.stosy == 1
    assert p.powierzchnia_mm2 == (40 + ODSTEP_MM) ** 2


def test_sztuki_ukladaja_sie_w_stosy():
    # 11 sztuk 6203 przy 3 warstwach w stosie = 4 stosy (ostatni niepełny).
    p = powierzchnia_pozycji("6203", D=40, B=12, ilosc=11,
                              szerokosc_mm=880, glebokosc_mm=500, wysokosc_mm=210)
    assert p.warstwy == 3 and p.stosy == 4


def test_brak_srednicy_nie_zgaduje():
    # Bez D nie ma z czego liczyć - mówimy o tym wprost zamiast podstawiać zmyśloną wartość.
    p = powierzchnia_pozycji("???", D=None, B=12, ilosc=5,
                              szerokosc_mm=880, glebokosc_mm=500, wysokosc_mm=210)
    assert p.powierzchnia_mm2 == 0 and "brak średnicy" in p.powod


def test_polka_bez_wymiarow_nie_ma_pojemnosci():
    o = obciazenie_polki("x", "Półka", None, None, None, [("6203", 40, 12, 5)])
    assert not o.znane_wymiary and o.procent == 0, "niezmierzonej półki nie zgadujemy"


def test_zapelnienie_i_prog_ciasno():
    # Półka 20 x 20 cm: powierzchnia użyteczna 200*200*0.85 = 34 000 mm².
    # Cztery stosy 6203 po (40+30)² = 4 900 mm² każdy = 19 600 mm² -> 57.6%.
    o = obciazenie_polki("x", "Półka", 200, 200, 210, [("6203", 40, 12, 11)])
    assert 57 < o.procent < 58
    assert not o.ciasno
    # Dołożenie 6020 (D=150) przekracza próg ciasnoty.
    o2 = obciazenie_polki("x", "Półka", 200, 200, 210, [("6203", 40, 12, 11), ("6020", 150, 24, 1)])
    assert o2.ciasno and o2.procent > 85


def test_niemieszczace_nie_licza_sie_do_zapelnienia():
    o = obciazenie_polki("x", "Półka", 880, 100, 300, [("6020", 150, 24, 2)])
    assert o.zajete_mm2 == 0 and len(o.niemieszczace) == 1


def test_proponowany_podzial_wysokiej_przestrzeni():
    # 142 cm prześwitu przy najwyższym sensownym stosie 15 cm: mieści się 7 poziomów.
    ile, rozstaw = proponowany_podzial(1420, 150)
    assert ile == 7
    assert rozstaw > 150 + REZERWA_NAD_STOSEM_MM - 1

    # Przestrzeń mniejsza niż jeden stos zostaje jedną półką.
    assert proponowany_podzial(150, 400)[0] == 1


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
