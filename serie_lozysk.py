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
                           TYP_TULEJA_WCIAGANA, TYP_WAHLIWE_KULKOWE, TYP_WALCOWE, TYP_WSTAWKOWE,
                           TYP_WSTAWKOWE_ES, TYP_WSTAWKOWE_EX, TYP_WSTAWKOWE_RAE,
                           TYP_WSTAWKOWE_UD)

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
    # Cyfry doklejane do przedrostka, gdy test buduje przykładowe oznaczenie serii.
    # Domyślne "208" pasuje do serii ISO, ale nie do wszystkich: numery calowe Timkena
    # mają 4-6 cyfr, a reguła celowo wymaga tylu, żeby "H208" (tuleja wciągana) nie
    # udawało łożyska stożkowego. Bez tego pola test wymuszałby regułę zbyt luźną.
    cyfry_przykladu: str = "208"


# Kolejność w krotce `przedrostki` MA ZNACZENIE tam, gdzie jedno jest początkiem
# drugiego (UCFL przed UC, ESP przed ES) - inaczej krótsze połknęłoby dłuższe.
SERIE: tuple[Seria, ...] = (
    Seria(
        ("UCFL", "UCFC", "UCPH", "UCP", "UCF", "UCT", "UCX", "UC", "UK", "SB", "SA", "CSA",
         "USFE", "UEL", "UEM", "YEL", "YET", "YAR"),
        TYP_WSTAWKOWE, KOD_ISO,
        "eshop.ntn-snr.com (USFE208G2), katalog UC200",
        "Wstawkowe mocowane WKRĘTAMI dociskowymi. UC208: pierścień wewnętrzny 49,2 mm. "
        "Goły przedrostek 'US' (bez FE) NIE jest tu - patrz seria osobno niżej.",
    ),
    Seria(
        ("US",),
        TYP_WAHLIWE_KULKOWE, KOD_ISO,
        "Identyfikacja Dominika (23.09) na sztuce US206 z magazynu",
        "Kulkowe SAMONASTAWNE (dwurzędowe, seria 1200), NIE wstawkowe - mimo że 'US' "
        "dawniej stał w tej samej grupie co UC/UEL/YAR na podstawie karty SNR "
        "US208G2 z eshop.ntn-snr.com. Ta karta opisywała inne łożysko - fizyczna sztuka "
        "z magazynu nie ma oprawy ani wkrętów dociskowych. US206 to odpowiednik 1206 "
        "(30x62x16), ten sam kod otworu ISO co przy wstawkowych (US206 -> 06 -> 30 mm), "
        "ale wymiary D/B trzeba brać z katalogu serii 1200, nie z UC.",
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
        ("UD",),
        TYP_WSTAWKOWE_UD, KOD_ISO,
        "albeco.com.pl (karta UD205 S ZVL: d 25, D 52, C 15, kulisty pierścień "
        "zewnętrzny, masa 0,129 kg) oraz bearingsize.info (205-NPP-B INA, 25x52x15)",
        "ZVL. Odpowiednik INA 2xx-NPP-B, GOST 1726205, rodzina SKF YAR. Kod otworu "
        "jak w ISO (UD205 -> 05 -> 25 mm). PIERŚCIEŃ WEWNĘTRZNY NIE JEST POSZERZONY - "
        "szerokość zewnętrzna i całkowita to ta sama liczba, inaczej niż przy UC/ES/EX. "
        "UD205 to 25x52x15, a UC205 przy tym samym otworze i tej samej średnicy "
        "zewnętrznej ma 34,1 mm; to nie są zamienniki.",
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
        ("LL", "LM", "HM", "HH", "EE", "EH", "L", "M"),
        TYP_STOZKOWE_CALOWE, BRAK_REGULY,
        "ahrinternational.com/TIMKEN_nomenclature.shtml oraz "
        "rhtrd.com/bearings/timken-bearings/timken-part-number-prefixes/ "
        "(dwa niezależne wykazy przedrostków Timkena)",
        "Serie CALOWE Timkena: L (light), M (medium) i ich złożenia "
        "LL/LM/HM/HH, plus EE i EH. Numer bazowy to numer KATALOGOWY - nie koduje "
        "ani otworu, ani rozmiaru, więc reguła ISO 'dwie ostatnie cyfry x 5 mm' tu "
        "nie obowiązuje. UWAGA: przedrostek J (JLM, JH, JM, JW, JP...) to u Timkena "
        "seria METRYCZNA, nie calowa - oba źródła mówią o nim 'metric cone bore and "
        "cup O.D.', więc świadomie NIE ma go na tej liście. "
        "Przedrostek H (heavy) jest PRZECIĄŻONY: dzieli go z tuleją wciąganą liczba "
        "cyfr - tu zostaje wariant 4+ cyfr (H414242), a 3-cyfrowe H2/H3 to osobna "
        "seria 'tuleja wciągana' poniżej.",
        cyfry_przykladu="44643",
    ),
    Seria(
        ("H",),
        TYP_TULEJA_WCIAGANA, KOD_ISO,
        "SKF/Schaeffler, katalog tulei wciąganych (seria H); potwierdzone na sztuce "
        "FAG H210 z magazynu (wałek 50 mm)",
        "Tuleja wciągana (adapter sleeve), NIE łożysko toczne - osprzęt do osadzenia "
        "łożyska z otworem stożkowym na wałku cylindrycznym. Trzy cyfry po H to "
        "liczba 2xx/3xx i kod otworu ISO: H208 = 40 mm, H210 = 50 mm. Trzy cyfry "
        "odróżniają tuleję od calowego stożka Timkena H (heavy), który ma ich 4+.",
        cyfry_przykladu="208",
    ),
    Seria(
        ("T",),
        TYP_OPOROWE, BRAK_REGULY,
        "cad.timken.com, karta T139-904A1 (typ TTSP) oraz "
        "rhtrd.com/bearings/timken-bearings/timken-part-number-prefixes/ "
        "('T (Race) - Thrust bearing assemblies')",
        "Calowe łożyska OPOROWE Timkena, typ TTSP: dwie bieżnie, wałeczki, koszyk "
        "i pierścień spinający. 'T139' to numer bazowy, 'T139-904A1' numer KOMPLETU - "
        "ta sama relacja co przy stożkowych (37431A to sam stożek, 37431A/37625 "
        "komplet). Numer idzie za otworem w setnych CALA (T126 -> 1,26\", "
        "T139 -> 1,385\"), więc kod otworu ISO tu nie obowiązuje.",
    ),
    Seria(
        ("37431A", "37625"),
        TYP_STOZKOWE_CALOWE, BRAK_REGULY,
        "cad.timken.com, karty 37431A (stożek) i 37431A/37625 (komplet)",
        "Oznaczenia calowe BEZ przedrostka literowego. Nie da się ich odróżnić od "
        "numeracji ISO żadną regułą - '37431' wygląda dokładnie jak numer metryczny - "
        "więc znamy je WYŁĄCZNIE z tej listy i dopisujemy pojedynczo, ze źródłem. "
        "Stożek i miska mają osobne numery, a komplet zapisuje się przez ukośnik: "
        "37431A/37625 to 109,538 x 158,75 x 23,02 mm (23,02 to szerokość CAŁKOWITA T; "
        "sam stożek ma 21,438 mm, sama miska 15,875 mm).",
    ),
    Seria(
        ("357234",),
        TYP_SKOSNE, BRAK_REGULY,
        "Identyfikacja Dominika (22.09): łożysko kulkowe skośne dwurzędowe 35x72x34, "
        "numer katalogowy OEM",
        "Numer katalogowy producenta, nie seria ISO - żadna reguła go nie rozpozna, więc "
        "typ i wymiary są wpisane JAWNIE (35x72x34, skośne dwurzędowe). '35' na początku "
        "przypadkowo zgadza się z otworem, ale numer nie koduje otworu regułą ISO - stąd "
        "BRAK_REGULY, a wymiary biorą się z katalogu.",
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
