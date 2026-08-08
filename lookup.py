"""
Wyszukiwanie wymiarów łożysk: najpierw wbudowana baza offline (pewne, szybkie),
a gdy symbolu/wymiarów nie ma w bazie - próba dociągnięcia danych z internetu
(orientacyjne, oznaczone w GUI jako pochodzące z sieci).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from bearing_data import BEARING_DB, BEARING_TYPE, SOURCE_OFFLINE, SOURCE_ONLINE, SOURCE_MANUAL

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


# Przedrostki serii, które trzeba zachować w symbolu (nie same cyfry) -
# np. łożyska wstawkowe UC206, UK, SB itd. Dopisz tu kolejne w razie potrzeby.
_LETTER_PREFIXES = ("UC", "UK", "SB", "SA", "UCP", "UCF", "UCFL")


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

    if requests is not None:
        online = _online_lookup_by_symbol(symbol)
        if online:
            d, D, B = online
            return LookupResult(symbol, d, D, B, SOURCE_ONLINE, None,
                                 note="Dane orientacyjne z internetu - zweryfikuj suwmiarką.")

    return LookupResult(symbol, None, None, None, SOURCE_MANUAL, None,
                         note="Nie znaleziono - wpisz wymiary ręcznie.")


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
