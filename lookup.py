"""
Wyszukiwanie wymiarów łożysk: najpierw wbudowana baza offline (pewne, szybkie),
a gdy symbolu/wymiarów nie ma w bazie - próba dociągnięcia danych z internetu
(orientacyjne, oznaczone w GUI jako pochodzące z sieci).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from serie_lozysk import przedrostki_wszystkie
from bearing_data import BEARING_DB, BEARING_TYPE, SOURCE_OFFLINE, SOURCE_ONLINE, SOURCE_MANUAL
from bearing_types import bore_from_symbol, classify_symbol, dimensions_are_plausible

try:
    import requests
except ImportError:  # requests może nie być jeszcze zainstalowany
    requests = None

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
TIMEOUT = 8


@dataclass
class LookupResult:
    symbol: str | None
    d: float | None
    D: float | None
    B: float | None
    source: str  # "offline" / "internet" / "recznie"
    typ: str | None = None
    note: str = ""


# Przedrostki serii, które trzeba ZACHOWAĆ w symbolu (nie sprowadzać do samych cyfr).
# Bez tego "NU205" stałoby się "205" i szukalibyśmy zupełnie innego łożyska (realny
# przypadek: NU205 to 25x52x15, a wyszukiwarka na "205" zwracała 205x285x38). Ta sama
# pułapka powtórzyła się przy ES208 i EX.208.G2, za każdym razem dla innej serii.
#
# Dlatego lista NIE jest już pisana ręcznie, tylko brana z REJESTRU SERII
# (serie_lozysk.py). Dopisanie serii w jednym miejscu zamyka ją we wszystkich -
# a tests/test_spojnosc_regul.py pilnuje, żeby telefon znał dokładnie te same.
# Posortowane od najdłuższego, żeby "NUP" wygrało z "NU", a "NU" z "N".
#
# Tylko przedrostki LITEROWE, zgodnie z nazwą. W rejestrze są też wpisy czysto
# liczbowe (calowe 37431A/37625), a te nie są przedrostkami serii - doklejenie do
# nich cyfr dawało "37431A3762", symbol nieistniejący w żadnym katalogu.
_LETTER_PREFIXES = tuple(p for p in przedrostki_wszystkie() if p[0].isalpha())

# Oznaczenia calowe bez przedrostka literowego, w zapisie katalogowym. Zwracamy je
# w CAŁOŚCI, bo obcięcie któregokolwiek członu daje inne łożysko albo żadne:
# "37431A" -> "37431" gubiło literę i nie trafiało we własny wpis katalogu, a
# "37431A/37625" (komplet stożek + miska) rozpadało się na sam numer stożka.
_INCH_NUMERIC = tuple(p for p in przedrostki_wszystkie() if not p[0].isalpha())
_INCH_ALTERNATYWA = "|".join(re.escape(p) for p in _INCH_NUMERIC)
_INCH_RE = re.compile(rf"\b(?:{_INCH_ALTERNATYWA})(?:\s*/\s*(?:{_INCH_ALTERNATYWA}))?")


# Seria BG/BD - patrz komentarz przy _BORE_FIRST_RULE w bearing_types.py.
_BG_RE = re.compile(r"\b(\d{2,3})\s*B([GD])[\s\-_./]*(\d{4})")


def normalize_symbol(raw: str) -> str:
    """Wyciąga bazowy numer łożyska z dowolnego zapisu, np. 'SKF 6008-2RS1' -> '6008',
    ale zachowuje przedrostki literowe serii wstawkowych, np. 'UC 211 D1' -> 'UC211'."""
    if not raw:
        return ""
    raw = raw.strip().upper()
    # Oznaczenia calowe PRZED reszt(ą): są w całości cyfrowe, więc reguła "weź ciąg
    # cyfr" na końcu tej funkcji zjadłaby literę i drugi człon kompletu.
    m_cal = _INCH_RE.search(raw)
    if m_cal:
        return re.sub(r"\s+", "", m_cal.group(0))
    # UWAGA na KROPKI: SNR zapisuje oznaczenia jako "EX.208.G2" / "ES.208.G2". Dopóki
    # kropka nie była traktowana jak separator, przedrostek się nie doklejał i całość
    # redukowała się do gołego "208" - czyli do zwykłego łożyska kulkowego 40x80x18
    # zamiast wstawkowego 40x80x56,3. Ten sam objaw co przy NU205 -> 205.
    #
    # Zakres {3,6}, a nie {3,4}: numery calowe Timkena mają 4-6 cyfr, więc przy starym
    # progu "LM11949" skracało się do "LM1194" - symbolu, którego nie ma nigdzie.
    # Seria BG/BD (30BG5222 2DSE): otwór przed literami, potem cztery cyfry. Bez tego
    # reguła "weź ciąg cyfr" niżej zwracała "5222" - inne łożysko o innych wymiarach.
    m_bg = _BG_RE.search(raw)
    if m_bg:
        return f"{m_bg.group(1)}B{m_bg.group(2)}{m_bg.group(3)}"
    for prefix in _LETTER_PREFIXES:
        m = re.search(rf"\b{prefix}[\s\-_./]*(\d{{3,6}})", raw)
        if m:
            return f"{prefix}{m.group(1)}"
    match = re.search(r"\d{3,6}", raw)
    return match.group(0) if match else raw


def lookup_by_symbol(raw_symbol: str) -> LookupResult:
    symbol = normalize_symbol(raw_symbol)

    if symbol in BEARING_DB:
        d, D, B = BEARING_DB[symbol]
        return LookupResult(symbol, d, D, B, SOURCE_OFFLINE, BEARING_TYPE.get(symbol))

    # Symbolu nie ma w katalogu, ale TYP da się ustalić z samego oznaczenia (ISO 15/355),
    # bez sieci - patrz bearing_types.py. Klasyfikujemy z SUROWEGO wejścia, bo
    # normalize_symbol() obcina przedrostki literowe (NU/NA/HK...), które niosą typ.
    rozpoznany_typ = classify_symbol(raw_symbol)

    odrzucone_z_sieci = False
    if requests is not None:
        online = _online_lookup_by_symbol(symbol)
        if online:
            d, D, B = online
            # Wyszukiwarka potrafi zwrócić wymiary ZUPEŁNIE innego łożyska (realny przypadek:
            # dla 6204 przyszło 60x80 zamiast 20x47). Oznaczenie samo w sobie mówi, jaki
            # powinien być otwór, więc taki wynik odrzucamy zamiast zapisywać bzdurę, która
            # w magazynie wygląda potem na prawdziwą.
            if dimensions_are_plausible(raw_symbol, d, D, B):
                return LookupResult(symbol, d, D, B, SOURCE_ONLINE, rozpoznany_typ,
                                     note="Dane orientacyjne z internetu - zweryfikuj suwmiarką.")
            odrzucone_z_sieci = True

    if odrzucone_z_sieci:
        oczekiwane = bore_from_symbol(raw_symbol)
        note = ("Znaleziony w internecie wynik nie pasuje do tego oznaczenia i został odrzucony. "
                "Wpisz wymiary ręcznie.")
        if oczekiwane is not None:
            note = (f"Znaleziony w internecie wynik nie pasuje do tego oznaczenia (otwór powinien mieć "
                    f"ok. {oczekiwane:g} mm) i został odrzucony. Wpisz wymiary ręcznie.")
    else:
        note = "Nie znaleziono - wpisz wymiary ręcznie."
        if rozpoznany_typ:
            note = f"Nie znaleziono wymiarów - typ rozpoznany z oznaczenia ({rozpoznany_typ}). Wpisz wymiary ręcznie."
    return LookupResult(symbol, None, None, None, SOURCE_MANUAL, rozpoznany_typ, note=note)


def lookup_by_dimensions(d: float | None, D: float | None, B: float | None,
                          tolerance: float = 0.6) -> list[tuple[str, float, float, float, str]]:
    """Zwraca listę kandydatów (symbol, d, D, B, typ) z bazy offline pasujących do wymiarów."""
    candidates = []
    for sym, (bd, bD, bB) in BEARING_DB.items():
        score = 0.0
        checks = 0
        if d is not None:
            score += abs(bd - d)
            checks += 1
        if D is not None:
            score += abs(bD - D)
            checks += 1
        if B is not None:
            score += abs(bB - B)
            checks += 1
        if checks == 0:
            continue
        if (d is None or abs(bd - d) <= tolerance) and \
           (D is None or abs(bD - D) <= tolerance) and \
           (B is None or abs(bB - B) <= tolerance):
            candidates.append((score, sym, bd, bD, bB))

    candidates.sort(key=lambda c: c[0])
    return [(sym, bd, bD, bB, BEARING_TYPE.get(sym, "")) for _, sym, bd, bD, bB in candidates]


def online_lookup_by_dimensions(d: float | None, D: float | None, B: float | None) -> str | None:
    """Best-effort: szuka w internecie symbolu łożyska pasującego do podanych wymiarów."""
    if requests is None or (d is None and D is None and B is None):
        return None
    parts = []
    if d:
        parts.append(f"{int(d)}")
    if D:
        parts.append(f"{int(D)}")
    if B:
        parts.append(f"{int(B)}")
    dims_query = "x".join(parts)
    query = f"bearing {dims_query} mm symbol number"
    text = _ddg_search_text(query)
    if not text:
        return None
    # szukaj typowych oznaczeń łożysk: 4-5 cyfr, ew. z przedrostkiem serii 16
    for pat in (r"\b1[0-9]{4}\b", r"\b6[0-9]{3}\b", r"\b6[0-9]{4}\b"):
        m = re.search(pat, text)
        if m:
            return m.group(0)
    return None


def _online_lookup_by_symbol(symbol: str) -> tuple[float, float, float] | None:
    query = f"{symbol} bearing dimensions bore mm outer diameter width"
    text = _ddg_search_text(query)
    if not text:
        return None

    # wzorce typu "40x80x18" / "40 x 80 x 18"
    m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*[x×]\s*(\d{1,3}(?:\.\d+)?)\s*[x×]\s*(\d{1,3}(?:\.\d+)?)", text)
    if m:
        d, D, B = (float(m.group(i)) for i in (1, 2, 3))
        if d < D:
            return d, D, B
    return None


def _ddg_search_text(query: str) -> str:
    if requests is None:
        return ""
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.text
    except Exception:
        return ""
