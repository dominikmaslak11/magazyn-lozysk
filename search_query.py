"""
Rozpoznawanie intencji w JEDNYM polu wyszukiwania (wersja webowa).

Port 1:1 z SearchQuery.kt w appce Android - obie strony muszą rozumieć ten sam zapis,
bo opis składni w UI jest wspólny i rozjazd od razu byłby mylący dla użytkownika.

    6205        -> szukanie po symbolu (jak dotąd)
    25x52       -> wymiary: d=25, D=52, szerokość dowolna
    25x52x15    -> wymiary: d=25, D=52, B=15
    x52         -> tylko średnica zewnętrzna 52
    25x         -> tylko średnica wewnętrzna 25
    25 52 15    -> to samo co 25x52x15

Pojedyncza liczba ("6205") celowo NIE uruchamia szukania po wymiarach - byłaby nie do
odróżnienia od symbolu. Do szukania po jednym wymiarze służy zapis "x52" albo "25x".
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Tolerancja dopasowania [mm] - taka sama jak przy wyszukiwaniu w katalogu i w appce.
TOLERANCE = 0.6

_SEPARATORS = re.compile(r"[x×*]", re.IGNORECASE)
_NUMBER = re.compile(r"^\d+([.,]\d+)?$")


@dataclass
class DimensionQuery:
    d: float | None
    D: float | None
    B: float | None

    @property
    def is_empty(self) -> bool:
        return self.d is None and self.D is None and self.B is None


def parse_dimensions(raw: str) -> DimensionQuery | None:
    """Zwraca wymiary, jeśli tekst wygląda na zapytanie wymiarowe, albo None -
    wtedy szukamy po symbolu."""
    text = (raw or "").strip()
    if not text:
        return None

    if _SEPARATORS.search(text):
        parts = _SEPARATORS.split(text)
    else:
        chunks = [c for c in re.split(r"[\s,;]+", text) if c]
        if len(chunks) < 2:
            return None
        parts = chunks

    if len(parts) > 3:
        return None

    values: list[float | None] = []
    for part in parts:
        p = part.strip()
        if not p:
            values.append(None)                  # puste miejsce = dowolny wymiar
        elif _NUMBER.match(p):
            values.append(float(p.replace(",", ".")))
        else:
            return None                          # cokolwiek innego -> to nie wymiary

    query = DimensionQuery(
        d=values[0] if len(values) > 0 else None,
        D=values[1] if len(values) > 1 else None,
        B=values[2] if len(values) > 2 else None,
    )
    return None if query.is_empty else query
