"""
Rozpoznawanie TYPU łożyska na podstawie samego oznaczenia (ISO 15 / ISO 355).

Po co to jest: wbudowany katalog wymiarów (bearing_data.py) ma ~250 najpopularniejszych
rozmiarów. Gdy ktoś wpisze symbol spoza katalogu, wymiarów trzeba szukać w internecie -
ale TYP da się ustalić bez żadnego katalogu i bez sieci, bo oznaczenia łożysk nie są
przypadkowe: pierwsze cyfry (albo przedrostek literowy) kodują konstrukcję.

Dzięki temu kategoria ustawia się sama dla tysięcy oznaczeń, których nie ma w katalogu.

UWAGA - najważniejsza pułapka tego formatu: o typie decyduje NIE tylko prefiks, ale też
LICZBA CYFR. Przykłady, które łatwo pomylić:

    3204   (4 cyfry)  -> skośne dwurzędowe
    30204  (5 cyfr)   -> STOŻKOWE
    2205   (4 cyfry)  -> wahliwe kulkowe
    22205  (5 cyfr)   -> wahliwe BARYŁKOWE

Dlatego reguły są uporządkowane od najbardziej szczegółowej i zawsze sprawdzają długość
ciągu cyfr. Zmieniając cokolwiek w tym pliku, uruchom testy w tests/test_bearing_types.py -
weryfikują one m.in. zgodność ze WSZYSTKIMI wpisami wbudowanego katalogu.

Świadome ograniczenie: klasyfikujemy WYŁĄCZNIE z oznaczenia. Z samych wymiarów (d/D/B)
typu wyznaczyć się nie da - różne konstrukcje dzielą te same gabaryty - i celowo nawet
nie próbujemy, bo pewnie brzmiąca, ale błędna kategoria jest gorsza niż jej brak.
"""
from __future__ import annotations

import re

from bearing_data import (TYP_IGIELKOWE, TYP_KULKOWE, TYP_OPOROWE, TYP_SKOSNE,
                           TYP_STOZKOWE, TYP_WAHLIWE_BARYLKOWE, TYP_WAHLIWE_KULKOWE,
                           TYP_WALCOWE, TYP_WSTAWKOWE, TYP_WSTAWKOWE_ES,
                           TYP_WSTAWKOWE_RAE, TYP_WSTAWKOWE_EX)


# --- reguły na przedrostkach literowych -------------------------------------
# Kolejność MA ZNACZENIE: igiełkowe (NA/NK/NKI) muszą być sprawdzone przed walcowymi
# (N/NU/NJ), bo inaczej reguła na "N" połknęłaby "NA4900".
_PREFIX_RULES: list[tuple[str, str]] = [
    # Wstawkowe INA/Schaeffler. PRZED igiełkowymi, bo tam jest reguła na "RNA"/"NA",
    # a tu wchodzą oznaczenia zaczynające się od RA.
    (r"^(GRAE|RALE|RASE|RAE|GRA|RA)\d", TYP_WSTAWKOWE_RAE),
    # Wstawkowe SNR serii EX (EX208, EXP..., EXF...). Osobno od ES, bo przy tych samych
    # 40 x 80 mm mają dużo szerszy pierścień wewnętrzny - to inna część, nie zamiennik.
    (r"^(EXPA|EXP|EXFL|EXFC|EXF|EXC|EXT|EX)\d", TYP_WSTAWKOWE_EX),
    # Wstawkowe serii ES - PRZED regułą UC i jako OSOBNY typ. ES208 i UC208 mają ten
    # sam otwór i tę samą średnicę zewnętrzną, więc łatwo je pomylić, ale to inne
    # konstrukcje i jedna nie zastąpi drugiej w maszynie.
    (r"^(ESPA|ESP|ES)\d", TYP_WSTAWKOWE_ES),
    # łożyska wstawkowe / w oprawach (mocowane wkrętami)
    # US/UEL (SNR) i YEL/YET/YAR (SKF) to również łożyska wstawkowe; kod otworu czyta
    # się w nich jak w ISO, więc idą razem z UC.
    (r"^(UCFL|UCFC|UCPH|UCP|UCF|UCT|UCX|UC|UK|SB|SA|CSA|USFE|US|UEL|UEM|YEL|YET|YAR)\d",
     TYP_WSTAWKOWE),
    # igiełkowe - PRZED walcowymi
    (r"^(RNAO|RNA|NKIA|NKIB|NKI|NKX|NKS|NAO|NA|NK|HK|BK|IR|TA)\d", TYP_IGIELKOWE),
    # walcowe
    (r"^(NNU|NNCF|NCF|NUP|NUB|NJP|NN|NU|NJ|NF|NP|N)\d", TYP_WALCOWE),
    # skośne czteropunktowe
    (r"^QJ\d", TYP_SKOSNE),
    # oporowe walcowe / baryłkowe zapisywane literowo
    (r"^(AXK|AX|81|89)\d", TYP_OPOROWE),
    # wahliwe baryłkowe zapisywane z literą C (np. C2210)
    (r"^C\d{4}", TYP_WAHLIWE_BARYLKOWE),
]


# --- reguły na samych cyfrach -----------------------------------------------
# Klucz: (liczba cyfr, przedrostek cyfrowy) -> typ. Sprawdzane od najdłuższego
# przedrostka, żeby "302" wygrało z "30".
_DIGIT_RULES: list[tuple[int, tuple[str, ...], str]] = [
    # --- 5 cyfr ---
    # stożkowe (ISO 355 / DIN 720)
    (5, ("302", "303", "313", "320", "322", "323", "329", "330", "331", "332"), TYP_STOZKOWE),
    # wahliwe baryłkowe (DIN 635-2)
    # 202xx/203xx to łożyska baryłkowe jednorzędowe - bez tego wpisu seria zostawała
    # nierozpoznana (realny przypadek z magazynu: 20211 dostało domyślne "kulkowe zwykłe").
    (5, ("202", "203", "213", "222", "223", "230", "231", "232", "238", "239", "240", "241",
         "248", "249"), TYP_WAHLIWE_BARYLKOWE),
    # oporowe kulkowe i baryłkowe
    (5, ("511", "512", "513", "514", "522", "523", "524", "292", "293", "294"), TYP_OPOROWE),
    # kulkowe zwykłe cienkościenne (seria 16000) oraz 4-rzędowe 6xxxx
    (5, ("160", "161", "162", "163"), TYP_KULKOWE),
    # --- 4 cyfry ---
    # skośne dwurzędowe (3200/3300) - UWAGA: 5-cyfrowe 302xx/303xx to STOŻKOWE (wyżej)
    (4, ("32", "33"), TYP_SKOSNE),
    # wahliwe kulkowe (1200/1300/2200/2300)
    (4, ("12", "13", "22", "23"), TYP_WAHLIWE_KULKOWE),
    # oporowe kulkowe jednokierunkowe zapisywane 4-cyfrowo
    # 4-cyfrowe 52xx/53xx to łożyska SKOŚNE DWURZĘDOWE (starsze oznaczenie tego samego,
    # co 32xx/33xx: 5202 = 3202 = 15x35x15,9 mm), a NIE oporowe. Oporowe kulkowe mają
    # oznaczenia PIĘCIOCYFROWE (51100, 51200, 52200...) i są obsłużone regułą wyżej.
    # Realny błąd: łożysko 5202 użytkownika zostało przez tę regułę zaliczone do
    # oporowych, choć jest skośne - a to zupełnie inna konstrukcja i zastosowanie.
    (4, ("52", "53"), TYP_SKOSNE),
]

# Reguły na pierwszej cyfrze - najogólniejsze, sprawdzane NA KOŃCU.
_FIRST_DIGIT_RULES: list[tuple[str, str]] = [
    ("6", TYP_KULKOWE),   # 6000/6200/6300/6800/6900 - zdecydowanie najczęstsze
    ("7", TYP_SKOSNE),    # 7200/7300 - skośne jednorzędowe
    ("1", TYP_WAHLIWE_KULKOWE),  # 1200/1300 złapane wyżej; tu reszta serii 1xxx
]

# Najkrótsze sensowne oznaczenie cyfrowe to 3 znaki (np. 607, 608 - miniaturowe kulkowe).
# Bez tego progu "12" czy "5" dostawałyby typ z reguły na pierwszej cyfrze, czyli czyste
# zgadywanie na wejściu, które oznaczeniem łożyska w ogóle nie jest.
_MIN_DIGITS = 3

# Nazwy producentów, które użytkownik często wpisuje przed właściwym oznaczeniem
# ("SKF 6205-2RS1"). Obcinamy je, żeby nie zasłoniły oznaczenia. Lista jawna, a nie
# "utnij dowolne litery z przodu" - inaczej śmieciowe wejście typu "ABC123" dostałoby
# przypadkowy typ zamiast uczciwego "nie wiem".
_BRANDS = (
    "SKF", "FAG", "INA", "NSK", "NTN", "KOYO", "TIMKEN", "NACHI", "IKO", "THK",
    "ZVL", "ZKL", "CX", "NKE", "SNR", "URB", "FLT", "KINEX", "STEYR", "RHP",
    "MCGILL", "TORRINGTON", "BARDEN", "SCHAEFFLER", "LOYAL", "CRAFT", "ASAHI",
)


def _normalized(raw: str) -> str:
    """Wielkie litery, bez separatorów, bez nazwy producenta z przodu."""
    text = re.sub(r"[\s\-_/.]", "", (raw or "").strip().upper())
    for brand in _BRANDS:
        if text.startswith(brand) and len(text) > len(brand):
            return text[len(brand):]
    return text


# Kod średnicy wewnętrznej (dwie ostatnie cyfry części numerycznej) wg ISO 15.
# Od 04 w górę obowiązuje reguła "kod x 5 mm"; cztery pierwsze kody są wyjątkami.
_BORE_CODE_EXCEPTIONS = {"00": 10.0, "01": 12.0, "02": 15.0, "03": 17.0}


def bore_from_symbol(raw: str) -> float | None:
    """Średnica wewnętrzna (d) wyliczona z samego oznaczenia, albo None gdy się nie da.

    Oznaczenia znormalizowanych łożysk kodują otwór: dwie ostatnie cyfry to "kod otworu",
    a d = kod x 5 mm (z wyjątkiem 00/01/02/03 = 10/12/15/17 mm). Działa to dla serii
    metrycznych: 6204 -> 20, 6205 -> 25, 30204 -> 20, 22210 -> 50, NU205 -> 25, UC206 -> 30.

    Po co: to niezależne od katalogu i od internetu sprawdzenie sensowności wymiarów.
    Wyszukiwarka potrafi zwrócić wymiary ZUPEŁNIE innego łożyska (realny przypadek:
    dla 6204 przyszło 60x80 zamiast 20x47) - taki wynik odrzucamy, zamiast zapisywać
    bzdurę, która potem wygląda w magazynie na prawdziwą.

    Świadomie zwracamy None dla serii, w których ta reguła NIE obowiązuje (igiełkowe
    HK/BK/NA, miniatury 6xx, wymiary calowe) - lepiej nie sprawdzać niż sprawdzić źle.
    """
    text = _normalized(raw)
    if not text:
        return None

    # Serie INA (RAE/GRAE/RALE/RA): liczba w oznaczeniu to WPROST otwór w milimetrach,
    # a nie kod otworu. RAE35 ma 35 mm, nie 175 mm (35 x 5) - reguła ISO dałaby tu
    # wynik pięciokrotnie zawyżony i odrzuciłaby prawdziwe wymiary jako "niepasujące".
    m_ina = re.match(r"^(?:GRAE|RALE|RASE|RAE|GRA|RA)(\d{2,3})", text)
    if m_ina:
        wartosc = int(m_ina.group(1))
        # Zakres rozsądku: seria obejmuje kilkanaście do stu kilkudziesięciu milimetrów.
        return float(wartosc) if 10 <= wartosc <= 200 else None

    # Serie, w których dwie ostatnie cyfry NIE są kodem otworu.
    if re.match(r"^(RNAO|RNA|NKIA|NKIB|NKI|NKX|NKS|NAO|NA|NK|HK|BK|IR|TA|AXK|AX)\d", text):
        return None

    # Część numeryczna: pomijamy przedrostek literowy serii (NU, UC, QJ...).
    m = re.match(r"^([A-Z]*)(\d+)", text)
    if not m:
        return None
    prefiks, digits = m.group(1), m.group(2)

    # Bez przedrostka reguła dotyczy oznaczeń 4- i 5-cyfrowych (6204, 30204, 22210).
    # Gołe 3 cyfry są niejednoznaczne: "126" to łożysko o otworze 6 mm, a nie 130 mm
    # (kod "26"), więc takich celowo nie sprawdzamy.
    # Z przedrostkiem literowym 3 cyfry są już jednoznaczne i reguła obowiązuje:
    # UC206 -> 06 -> 30 mm, NU205 -> 05 -> 25 mm.
    dozwolone = (3, 4, 5) if prefiks else (4, 5)
    if len(digits) not in dozwolone:
        return None

    # Kod otworu obowiązuje TYLKO w numeracji metrycznej ISO. Jeśli nie rozpoznajemy
    # nawet typu, to nie wiemy, w jakim systemie zapisane jest to oznaczenie - i nie
    # wolno nam twierdzić, ile ma otworu.
    #
    # Realny przypadek: 37431A to calowe łożysko stożkowe Timkena o otworze 109,5 mm,
    # a reguła ISO wyliczała z dwóch ostatnich cyfr ("31") otwór 155 mm. Program
    # odrzucał wtedy PRAWDZIWE wymiary jako "niepasujące do oznaczenia" i przyjmował
    # fałszywe - czyli kontrola sensowności działała dokładnie na odwrót.
    if classify_symbol(text) is None:
        return None

    kod = digits[-2:]
    if kod in _BORE_CODE_EXCEPTIONS:
        return _BORE_CODE_EXCEPTIONS[kod]
    wartosc = int(kod)
    if wartosc < 4:
        return None
    return float(wartosc * 5)


def dimensions_are_plausible(raw_symbol: str, d: float | None, D: float | None,
                              B: float | None, tolerance: float = 1.0) -> bool:
    """Czy wymiary w ogóle mogą należeć do łożyska o tym oznaczeniu?

    Sprawdza dwie rzeczy, obie niezależne od internetu:
      1. podstawową geometrię (0 < d < D, B > 0),
      2. zgodność d z kodem otworu wyliczonym z oznaczenia (jeśli da się go ustalić).

    Używane do odsiewania błędnych wyników wyszukiwania w sieci - patrz lookup.py.
    """
    if d is not None and D is not None and not (0 < d < D):
        return False
    if B is not None and B <= 0:
        return False

    oczekiwane_d = bore_from_symbol(raw_symbol)
    if oczekiwane_d is not None and d is not None:
        if abs(d - oczekiwane_d) > tolerance:
            return False
    return True


def classify_symbol(raw: str) -> str | None:
    """Zwraca typ łożyska rozpoznany z oznaczenia albo None, gdy nie da się ustalić.

    Przyjmuje surowe oznaczenie w dowolnym zapisie ("SKF NU 205 ECP", "6205-2RS",
    "30204 A"). None oznacza uczciwe "nie wiem" - lepsze niż zgadywanie.
    """
    if not raw or not raw.strip():
        return None

    # Ujednolicenie: wielkie litery, bez spacji/łączników, żeby "NU 205" == "NU-205".
    text = re.sub(r"[\s\-_/.]", "", raw.strip().upper())
    # Obcięcie nazwy producenta z przodu ("SKF6205" -> "6205"), żeby nie zasłoniła oznaczenia.
    for brand in _BRANDS:
        if text.startswith(brand) and len(text) > len(brand):
            text = text[len(brand):]
            break
    if not text:
        return None

    for pattern, typ in _PREFIX_RULES:
        if re.match(pattern, text):
            return typ

    # Ciąg cyfr rozpoczynający oznaczenie (przyrostki typu 2RS/ZZ/C3 są tu nieistotne).
    m = re.match(r"^(\d+)", text)
    if not m:
        return None
    digits = m.group(1)
    if len(digits) < _MIN_DIGITS:
        return None

    for length, prefixes, typ in _DIGIT_RULES:
        if len(digits) == length and digits.startswith(prefixes):
            return typ

    for first, typ in _FIRST_DIGIT_RULES:
        if digits.startswith(first):
            return typ

    return None
