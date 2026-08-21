"""Tokeny dostępu do magazynu — po jednym na urządzenie.

Po co: kiedyś był jeden token do wszystkiego. Wystarczyło, że dostęp miało dostać
urządzenie spoza tailnetu (telefon taty), i model przestał się bronić — zgubienie
tego jednego telefonu zmuszałoby do zmiany tokenu we WSZYSTKICH urządzeniach naraz.

Teraz każde urządzenie ma własny token i unieważnia się je pojedynczo:

    python tokeny.py --lista
    python tokeny.py --dodaj tata
    python tokeny.py --uniewaznij tata
    python tokeny.py --pokaz tata          # do wklejenia przy budowaniu APK

Token właściciela (~/.lozyska_data/token.txt) zostaje nietknięty — mają go już
wgrane oba moje telefony i przeglądarka. Tego pliku to narzędzie nie rusza.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

import database as db

TOKENY_PATH = db.DB_DIR / "tokeny.json"
WLASCICIEL = "wlasciciel"

# Długość jak w token.txt: 24 bajty losowe -> 32 znaki base64. Przy tokenie
# wystawionym do internetu przez Funnel to jest jedyna zapora, więc nie skracamy.
BAJTOW = 24


def wczytaj() -> dict[str, str]:
    try:
        dane = json.loads(TOKENY_PATH.read_text())
    except FileNotFoundError:
        return {}
    except ValueError as e:
        raise SystemExit(f"{TOKENY_PATH} nie jest poprawnym JSON-em: {e}")
    return dane if isinstance(dane, dict) else {}


def zapisz(tokeny: dict[str, str]) -> None:
    TOKENY_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Zapis przez plik tymczasowy: przerwanie w połowie nie zostawi obciętego JSON-a,
    # który zablokowałby dostęp wszystkim urządzeniom naraz.
    tmp = TOKENY_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(tokeny, indent=2, ensure_ascii=False) + "\n")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    tmp.replace(TOKENY_PATH)


def dodaj(nazwa: str) -> str:
    if nazwa == WLASCICIEL:
        raise SystemExit(f"Nazwa '{WLASCICIEL}' jest zarezerwowana dla token.txt.")
    tokeny = wczytaj()
    if nazwa in tokeny:
        raise SystemExit(f"Urządzenie '{nazwa}' już istnieje. "
                         f"Najpierw: python tokeny.py --uniewaznij {nazwa}")
    token = secrets.token_urlsafe(BAJTOW)
    tokeny[nazwa] = token
    zapisz(tokeny)
    return token


def uniewaznij(nazwa: str) -> None:
    tokeny = wczytaj()
    if nazwa not in tokeny:
        raise SystemExit(f"Nie ma urządzenia '{nazwa}'. Lista: python tokeny.py --lista")
    del tokeny[nazwa]
    zapisz(tokeny)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Tokeny dostępu do magazynu - po jednym na urządzenie.")
    p.add_argument("--lista", action="store_true", help="wypisz urządzenia (bez tokenów)")
    p.add_argument("--dodaj", metavar="NAZWA", help="nadaj token nowemu urządzeniu")
    p.add_argument("--uniewaznij", metavar="NAZWA", help="odbierz dostęp urządzeniu")
    p.add_argument("--pokaz", metavar="NAZWA", help="wypisz sam token (do skryptu)")
    a = p.parse_args(argv)

    if a.dodaj:
        token = dodaj(a.dodaj)
        print(f"Urządzenie '{a.dodaj}' dodane. Token:\n\n    {token}\n")
        print("Serwer podchwyci to od razu, bez restartu.")
        return 0

    if a.uniewaznij:
        uniewaznij(a.uniewaznij)
        print(f"Urządzenie '{a.uniewaznij}' straciło dostęp - natychmiast, bez restartu.")
        print("Appka na tym telefonie zacznie zwracać 401 przy najbliższej synchronizacji.")
        return 0

    if a.pokaz:
        tokeny = wczytaj()
        if a.pokaz not in tokeny:
            print(f"Nie ma urządzenia '{a.pokaz}'.", file=sys.stderr)
            return 1
        print(tokeny[a.pokaz])
        return 0

    # domyślnie: lista
    tokeny = wczytaj()
    print(f"{WLASCICIEL:20} (token.txt) - moje telefony i przeglądarka")
    if not tokeny:
        print("\nBrak dodatkowych urządzeń. Dodaj: python tokeny.py --dodaj tata")
        return 0
    for nazwa in sorted(tokeny):
        # Tokenów NIE wypisujemy - lista bywa pokazywana na ekranie przy ludziach.
        print(f"{nazwa:20} (tokeny.json)")
    print(f"\nRazem urządzeń: {len(tokeny) + 1}. Token do wglądu: --pokaz NAZWA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
