"""Rejestr serii łożysk: jedno miejsce, w którym zapisujemy, czego się nauczyliśmy.

Po co to jest: rozpoznawanie oznaczeń żyje w CZTERECH plikach - regułach typu i regule
otworu po stronie serwera (bearing_types.py), normalizacji symbolu (lookup.py) oraz
ich portach 1:1 na telefon (BearingTypeClassifier.kt, Repository.kt). Dwa razy zdarzyło
się, że seria trafiła do jednego, a nie trafiła do drugiego - i program po cichu
podstawiał wymiary zupełnie innego łożyska (NU205 -> "205", ES208 -> "208",
EX.208.G2 -> "208"). Za każdym razem wyglądało to wiarygodnie, bo otwór i średnica
zewnętrzna się zgadzały; nie zgadzała się szerokość.

Ten plik jest SPECYFIKACJĄ, nie implementacją. Testy (tests/test_spojnosc_regul.py)
sprawdzają, czy wszystkie cztery miejsca zgadzają się z tym, co tu zapisano - także
plik Kotlina, czytany jako tekst. Dodanie nowej serii to jeden wpis tutaj plus
uzupełnienie reguł; test powie, czego brakuje i gdzie.

KAŻDY wpis ma ŹRÓDŁO. Nie dopisujemy serii "z pamięci" ani z odpowiedzi modelu AI -
sklepy i modele mylą się w sposób, który wygląda przekonująco (dla serii ES modele
podawały szerokości 38, 19 i 20 mm dla kolejnych rozmiarów tej samej serii, a sklep RS
opisuje RAE jako "spherical", choć Schaeffler pisze "cylindrical").
"""

from __future__ import annotations

from dataclasses import dataclass

from bearing_data import (TYP_IGIELKOWE, TYP_OPOROWE, TYP_SKOSNE, TYP_STOZKOWE_CALOWE,
                           TYP_WALCOWE, TYP_WSTAWKOWE, TYP_WSTAWKOWE_ES, TYP_WSTAWKOWE_EX,
                           TYP_WSTAWKOWE_RAE)

# Sposób, w jaki z oznaczenia czyta się średnicę otworu.
KOD_ISO = "kod ISO"          # dwie ostatnie cyfry x 5 mm (6205 -> 25 mm)
WPROST_MM = "wprost w mm"    # liczba to milimetry (RAE35 -> 35 mm)
BRAK_REGULY = "brak reguły"  # numeracja calowa/producencka - tylko z katalogu


@dataclass(frozen=True)
class Seria:
    """Jedna rodzina oznaczeń, której program nauczył się rozpoznawać."""
    przedrostki: tuple[str, ...]
    typ: str
    otwor: str
    zrodlo: str          # skąd wiemy - konkretny katalog, nie "z internetu"
    notatka: str = ""


# Kolejność w krotce `przedrostki` MA ZNACZENIE tam, gdzie jedno jest początkiem
# drugiego (UCFL przed UC, ESP przed ES) - inaczej krótsze połknęłoby dłuższe.
SERIE: tuple[Seria, ...] = (
    Seria(
        ("UCFL", "UCFC", "UCPH", "UCP", "UCF", "UCT", "UCX", "UC", "UK", "SB", "SA", "CSA",
         "USFE", "US", "UEL", "UEM", "YEL", "YET", "YAR"),
        TYP_WSTAWKOWE, KOD_ISO,
        "eshop.ntn-snr.com (US208G2), katalog UC200",
        "Wstawkowe mocowane WKRĘTAMI dociskowymi. UC208: pierścień wewnętrzny 49,2 mm.",
    ),
    Seria(
        ("ESPA", "ESP", "ES"),
        TYP_WSTAWKOWE_ES, KOD_ISO,
        "eshop.ntn-snr.com/en/product/ES208G2-SNR/ES208G2",
        "SNR. Kulista powierzchnia zewnętrzna, MIMOŚRODOWY pierścień zaciskowy. "
        "ES208: pierścień wewnętrzny 30,2 mm, z zaciskowym 43,7 mm, zewnętrzny 18 mm.",
    ),
    Seria(
        ("EXPA", "EXP", "EXFL", "EXFC", "EXF", "EXC", "EXT", "EX"),
        TYP_WSTAWKOWE_EX, KOD_ISO,
        "eshop.ntn-snr.com (EX.208.G2), agrodoctor.eu (karta EX208 G2)",
        "SNR. Kulista powierzchnia zewnętrzna, mimośrodowy pierścień. EX208: całkowita "
        "szerokość 56,3 mm, pierścień zewnętrzny 21 mm - DUŻO szerszy niż UC i ES.",
    ),
    Seria(
        ("GRAE", "RALE", "RASE", "RAE", "GRA", "RA"),
        TYP_WSTAWKOWE_RAE, WPROST_MM,
        "medias.schaeffler.com (RAE35-XL-NPP-B), traceparts.com (karta serii RAE..XL-NPP)",
        "INA/Schaeffler. Liczba to WPROST otwór w mm. RAE ma pierścień zewnętrzny "
        "WALCOWY, GRAE KULISTY - tylko GRAE kompensuje niewspółosiowość wału.",
    ),
    Seria(
        ("RNAO", "RNA", "NKIA", "NKIB", "NKI", "NKX", "NKS", "NAO", "NA", "NK", "HK", "BK",
         "IR", "TA"),
        TYP_IGIELKOWE, BRAK_REGULY,
        "ISO 15 / katalogi igiełkowych",
        "W tych seriach dwie ostatnie cyfry NIE są kodem otworu.",
    ),
    Seria(
        ("NNU", "NNCF", "NCF", "NUP", "NUB", "NJP", "NN", "NU", "NJ", "NF", "NP", "N"),
        TYP_WALCOWE, KOD_ISO,
        "ISO 15",
        "NU205 to 25x52x15 - bez zachowania przedrostka redukowało się do '205' "
        "(205x285x38), co był realny błąd w tym programie.",
    ),
    Seria(("QJ",), TYP_SKOSNE, KOD_ISO, "ISO 15", "Czteropunktowe."),
    Seria(("AXK", "AX"), TYP_OPOROWE, BRAK_REGULY, "katalogi oporowych igiełkowych"),
    Seria(
        ("37431A",),
        TYP_STOZKOWE_CALOWE, BRAK_REGULY,
        "cad.timken.com, karta 37431A",
        "Numeracja CALOWA. 37431A to sam pierścień wewnętrzny (cone) kompletu "
        "37431A/37625: otwór 109,538 mm, stożek 132,745 mm, szerokość 21,438 mm.",
    ),
)


def przedrostki_wszystkie() -> list[str]:
    """Wszystkie zarejestrowane przedrostki, od najdłuższego - do normalizacji symbolu."""
    wynik: list[str] = []
    for s in SERIE:
        wynik.extend(s.przedrostki)
    return sorted(set(wynik), key=lambda p: (-len(p), p))


def seria_dla(przedrostek: str) -> Seria | None:
    for s in SERIE:
        if przedrostek in s.przedrostki:
            return s
    return None
