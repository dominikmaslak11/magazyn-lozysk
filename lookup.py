"""
Wyszukiwanie wymiarów łożysk: najpierw wbudowana baza offline (pewne, szybkie),
a gdy symbolu/wymiarów nie ma w bazie - próba dociągnięcia danych z internetu
(orientacyjne, oznaczone w GUI jako pochodzące z sieci).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

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
# Bez tego "NU205" stałoby się "205" i szukalibyśmy w internecie zupełnie innego łożyska
# (realny przypadek: NU205 to 25x52x15, a wyszukiwarka na "205" zwracała 205x285x38).
# Sortowane od najdłuższego, żeby "NUP" wygrało z "NU", a "NU" z "N".
_LETTER_PREFIXES = tuple(sorted((
    # wstawkowe / w oprawach
    "UCFL", "UCFC", "UCPH", "UCP", "UCF", "UCT", "UCX", "UC", "UK", "SB", "SA", "CSA",
    # ES/ESP MUSZĄ tu być: bez nich "ES208" redukowało się do "208", czyli do zwykłego
    # łożyska kulkowego 40x80x18 - zupełnie innej części o tych samych dwóch pierwszych
    # wymiarach. Ta sama pułapka, co kiedyś przy NU205 -> 205.
    "ESPA", "ESP", "ES",
    # walcowe
    "NNU", "NNCF", "NCF", "NUP", "NN", "NU", "NJ", "NF",
    # igiełkowe
    "RNAO", "RNA", "NKIA", "NKI", "NAO", "NA", "NK", "HK", "BK", "IR",
    # skośne czteropunktowe
    "QJ",
), key=len, reverse=True))


def normalize_symbol(raw: str) -> str:
    """Wyciąga bazowy numer łożyska z dowolnego zapisu, np. 'SKF 6008-2RS1' -> '6008',
    ale zachowuje przedrostki literowe serii wstawkowych, np. 'UC 211 D1' -> 'UC211'."""
    if not raw:
        return ""
    raw = raw.strip().upper()
    for prefix in _LETTER_PREFIXES:
        m = re.search(rf"\b{prefix}\s*-?\s*(\d{{3,4}})", raw)
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
