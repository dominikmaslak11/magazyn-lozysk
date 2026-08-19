"""Czy wszystkie cztery miejsca rozpoznające oznaczenia mówią to samo.

Rozpoznawanie serii żyje w czterech plikach: regułach po stronie serwera
(bearing_types.py), normalizacji symbolu (lookup.py) i ich portach 1:1 na telefon
(BearingTypeClassifier.kt, Repository.kt). Dwa razy zdarzyło się, że seria trafiła
do jednego, a nie trafiła do drugiego - i program po cichu podstawiał wymiary
zupełnie innego łożyska. Ten plik pilnuje, żeby to się nie powtórzyło.

Pliki Kotlina czytamy JAKO TEKST. To brzydkie, ale wyłapuje dokładnie ten błąd,
który realnie wystąpił - i jest tańsze niż utrzymywanie generatora kodu.
"""

import re
import sys
from pathlib import Path

KATALOG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG))

from bearing_types import bore_from_symbol, classify_symbol  # noqa: E402
from lookup import _LETTER_PREFIXES, normalize_symbol  # noqa: E402
from serie_lozysk import (BRAK_REGULY, KOD_ISO, SERIE, WPROST_MM,  # noqa: E402
                           przedrostki_wszystkie)

KOTLIN_KLASYFIKATOR = (KATALOG / "android-offline/app/src/main/java/pl/lozyska/offline"
                        / "BearingTypeClassifier.kt").read_text(encoding="utf-8")
KOTLIN_REPOZYTORIUM = (KATALOG / "android-offline/app/src/main/java/pl/lozyska/offline/data"
                        / "Repository.kt").read_text(encoding="utf-8")

# Przedrostki czysto liczbowe (jak calowe 37431A) nie są regułą prefiksową - typ
# biorą z katalogu, więc nie ma ich w tabelach reguł.
LITEROWE = [p for p in przedrostki_wszystkie() if p[0].isalpha()]


def test_kazdy_przedrostek_daje_zadeklarowany_typ():
    """Reguły serwera muszą zgadzać się z rejestrem co do jednego."""
    bledy = []
    for seria in SERIE:
        for p in seria.przedrostki:
            if not p[0].isalpha():
                continue
            symbol = f"{p}208"
            rozpoznany = classify_symbol(symbol)
            if rozpoznany != seria.typ:
                bledy.append(f"{symbol}: rejestr mówi {seria.typ!r}, reguły {rozpoznany!r}")
    assert not bledy, "Rozjazd reguł z rejestrem:\n  " + "\n  ".join(bledy)


def test_zadna_seria_nie_redukuje_sie_do_golych_cyfr():
    """NAJWAŻNIEJSZY test tego pliku - pilnuje błędu, który wystąpił trzy razy.

    NU205 -> "205", ES208 -> "208", EX.208.G2 -> "208". Za każdym razem program
    podstawiał wymiary innego łożyska o tym samym otworze i tej samej średnicy
    zewnętrznej, więc wynik wyglądał wiarygodnie - nie zgadzała się szerokość.
    """
    bledy = []
    for p in LITEROWE:
        for symbol in (f"{p}208", f"{p}.208.G2", f"{p} 208"):
            wynik = normalize_symbol(symbol)
            if not wynik.startswith(p):
                bledy.append(f"{symbol!r} -> {wynik!r} (zgubiony przedrostek {p})")
    assert not bledy, "Przedrostek gubiony przy normalizacji:\n  " + "\n  ".join(bledy)


def test_regula_otworu_zgodna_z_rejestrem():
    for seria in SERIE:
        for p in seria.przedrostki:
            if not p[0].isalpha():
                continue
            if seria.otwor == KOD_ISO:
                assert bore_from_symbol(f"{p}208") == 40.0, f"{p}208 wg ISO to otwór 40 mm"
            elif seria.otwor == WPROST_MM:
                assert bore_from_symbol(f"{p}35") == 35.0, f"{p}35 to otwór 35 mm wprost"
            elif seria.otwor == BRAK_REGULY:
                assert bore_from_symbol(f"{p}208") is None, (
                    f"{p}208: w tej serii kod otworu NIE obowiązuje, "
                    f"a program coś policzył")


def test_telefon_zna_te_same_przedrostki():
    """Port na telefon musi znać każdą serię z rejestru - inaczej to samo łożysko
    dostanie inny typ w zależności od tego, gdzie je dodano."""
    brakujace = [p for p in LITEROWE if f'"{p}"' not in KOTLIN_REPOZYTORIUM
                  and f"|{p}|" not in KOTLIN_KLASYFIKATOR
                  and f"({p}|" not in KOTLIN_KLASYFIKATOR
                  and f"|{p})" not in KOTLIN_KLASYFIKATOR
                  and f"^({p})" not in KOTLIN_KLASYFIKATOR]
    assert not brakujace, (
        "Przedrostki znane serwerowi, ale nieznane telefonowi: " + ", ".join(brakujace))


def test_telefon_traktuje_kropke_jak_separator():
    """SNR zapisuje oznaczenia jako "EX.208.G2" - kropka musi być separatorem
    po OBU stronach, inaczej telefon zredukuje to do gołego "208"."""
    assert re.search(r'SEPARATORS\s*=\s*Regex\("\[[^"]*\\\.?[^"]*\.', KOTLIN_KLASYFIKATOR) \
        or "\\\\-_/." in KOTLIN_KLASYFIKATOR or "-_/." in KOTLIN_KLASYFIKATOR, \
        "BearingTypeClassifier.kt: kropka nie jest separatorem"
    assert "[\\s\\-_./]" in KOTLIN_REPOZYTORIUM or "-_./" in KOTLIN_REPOZYTORIUM, \
        "Repository.kt: kropka nie jest separatorem przy normalizacji symbolu"


def test_serwer_zna_wszystkie_przedrostki_z_rejestru():
    brakujace = [p for p in LITEROWE if p not in _LETTER_PREFIXES]
    assert not brakujace, ("Przedrostki z rejestru nieobecne w lookup._LETTER_PREFIXES: "
                            + ", ".join(brakujace))


def test_nazwa_marki_nie_udaje_przedrostka():
    """Regresja: po dodaniu przedrostka "N" (łożyska walcowe N208) normalizacja
    zaczęła czytać "NTN 6205" jako "N6205" - końcowe N marki wyglądało jak seria.

    Ratuje granica słowa w dopasowaniu. Bez tego testu błąd wróciłby przy pierwszym
    dopisaniu krótkiego przedrostka.
    """
    for zapis, oczekiwany in (
        ("NTN 6205", "6205"), ("NACHI 6205", "6205"), ("NSK 6205", "6205"),
        ("SKF 6205", "6205"), ("ZVL 6205", "6205"), ("6205 NR", "6205"),
        ("N208", "N208"), ("NU205", "NU205"),
    ):
        assert normalize_symbol(zapis) == oczekiwany, (
            f"{zapis!r} -> {normalize_symbol(zapis)!r}, oczekiwano {oczekiwany!r}")


def test_kazda_seria_ma_zrodlo():
    """Wpis bez źródła to wiedza "z pamięci" - a tej w tym pliku nie trzymamy."""
    bez = [s.przedrostki[0] for s in SERIE if not s.zrodlo.strip()]
    assert not bez, "Serie bez podanego źródła: " + ", ".join(bez)


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
