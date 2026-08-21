"""Serwer MCP nad Vikunją — nadzór nad projektami z poziomu Claude.

Po co to jest: żeby móc powiedzieć „załóż zadanie", „co jest przeterminowane",
„przesuń termin" i żeby to trafiło do prawdziwego narzędzia z wykresem Gantta,
a nie do kolejnego pliku TODO.md, który nikt nie otwiera.

Dlaczego Vikunja, a nie ProjectLibre: ProjectLibre nie ma API. Integracja
wymagałaby forka 1899 plików Javy pod licencją CPAL, której paragraf 15 przy
wystawieniu czegokolwiek do sieci każe opublikować własne źródła. Vikunja ma
udokumentowane REST API — cały ten plik to cienka warstwa nad nim.

Konfiguracja: ~/.lozyska_data/vikunja.json (chmod 600, POZA repozytorium).
Ta sama zasada co przy smtp.json i ai_keys.json — token nigdy nie trafia do gita.

Uruchomienie ręczne (do sprawdzenia, czy działa):
    ./venv/bin/python nadzorca.py --sprawdz
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KONFIG = Path.home() / ".lozyska_data" / "vikunja.json"

# Vikunja liczy priorytet 1..5; 0 znaczy „nie ustawiono".
PRIORYTETY = {0: "-", 1: "niski", 2: "sredni", 3: "wysoki", 4: "pilne", 5: "TERAZ"}

LIMIT_STRON = 20  # zabezpieczenie przed pętlą, gdyby serwer źle stronicował


class BladVikunji(RuntimeError):
    """Vikunja odpowiedziała błędem albo jest nieosiągalna."""


def _konfiguracja() -> tuple[str, str]:
    if not KONFIG.exists():
        raise BladVikunji(
            f"Brak {KONFIG}. Utwórz plik z polami 'url' i 'token' (chmod 600)."
        )
    tryb = KONFIG.stat().st_mode & 0o077
    if tryb:
        # Token daje pełny dostęp do zadań — plik czytelny dla innych to wyciek.
        raise BladVikunji(f"{KONFIG} ma zbyt luźne prawa. Napraw: chmod 600 {KONFIG}")
    dane = json.loads(KONFIG.read_text())
    return dane["url"].rstrip("/"), dane["token"]


def _zapytaj(metoda: str, sciezka: str, dane: dict | None = None,
             parametry: dict | None = None) -> Any:
    url, token = _konfiguracja()
    pelny = f"{url}/{sciezka.lstrip('/')}"
    if parametry:
        pelny += "?" + urllib.parse.urlencode(parametry)

    tresc = json.dumps(dane).encode() if dane is not None else None
    zadanie = urllib.request.Request(pelny, data=tresc, method=metoda)
    zadanie.add_header("Authorization", f"Bearer {token}")
    zadanie.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(zadanie, timeout=20) as odp:
            surowe = odp.read()
    except urllib.error.HTTPError as e:
        szczegol = e.read().decode(errors="replace")[:300]
        raise BladVikunji(f"HTTP {e.code} przy {metoda} {sciezka}: {szczegol}") from e
    except urllib.error.URLError as e:
        raise BladVikunji(
            f"Serwer Vikunji nieosiągalny ({e.reason}). Sprawdź Tailscale "
            f"i 'systemctl status vikunja' na serwerze produkcyjnym."
        ) from e

    return json.loads(surowe) if surowe else None


def _wszystkie_strony(sciezka: str, parametry: dict | None = None) -> list[dict]:
    """Vikunja stronicuje po 50 pozycji; bez tego widać tylko pierwszą stronę."""
    zebrane: list[dict] = []
    for nr in range(1, LIMIT_STRON + 1):
        p = dict(parametry or {}, page=nr)
        partia = _zapytaj("GET", sciezka, parametry=p) or []
        zebrane.extend(partia)
        if len(partia) < 50:
            break
    return zebrane


def _data(tekst: str | None) -> str | None:
    """Przyjmuje 'YYYY-MM-DD' albo pełny znacznik ISO; zwraca to, co Vikunja lubi.

    Pusty string kasuje datę — Vikunja rozpoznaje rok zerowy jako 'brak'.
    """
    if tekst is None:
        return None
    tekst = tekst.strip()
    if not tekst:
        return "0001-01-01T00:00:00Z"
    if len(tekst) == 10:
        return f"{tekst}T09:00:00Z"
    return tekst


def _ustawiona(znacznik: str | None) -> bool:
    return bool(znacznik) and not znacznik.startswith("0001-")


def _skrot(zadanie: dict) -> dict:
    """Tylko te pola, które są potrzebne do rozmowy o projekcie.

    Pełna odpowiedź Vikunji ma ~40 pól (reakcje, załączniki, awatary autorów);
    wpuszczanie tego do kontekstu modelu to czysta strata miejsca.
    """
    def dzien(znacznik: str | None) -> str | None:
        # Vikunja zwraca rok zerowy zamiast pustej daty. Bez tego filtra w odpowiedzi
        # ląduje "0001-01-01", co czyta się jak termin z przeszłości - czyli każde
        # zadanie bez terminu wyglądałoby na przeterminowane.
        return znacznik[:10] if _ustawiona(znacznik) else None

    return {
        "id": zadanie["id"],
        "tytul": zadanie.get("title"),
        "zrobione": zadanie.get("done", False),
        "postep_proc": round((zadanie.get("percent_done") or 0) * 100),
        "priorytet": PRIORYTETY.get(zadanie.get("priority") or 0, "?"),
        "start": dzien(zadanie.get("start_date")),
        "koniec": dzien(zadanie.get("end_date")),
        "termin": dzien(zadanie.get("due_date")),
        "projekt_id": zadanie.get("project_id"),
    }


# --------------------------------------------------------------------------
# Operacje — czysty Python, bez MCP. Dzięki temu dają się testować bez serwera.
# --------------------------------------------------------------------------

def lista_projektow() -> list[dict]:
    return [
        {"id": p["id"], "tytul": p["title"], "opis": (p.get("description") or "")[:200]}
        for p in _wszystkie_strony("projects")
    ]


def utworz_projekt(tytul: str, opis: str = "") -> dict:
    p = _zapytaj("PUT", "projects", {"title": tytul, "description": opis})
    return {"id": p["id"], "tytul": p["title"]}


def lista_zadan(projekt_id: int, wliczajac_zrobione: bool = False) -> list[dict]:
    zadania = _wszystkie_strony(f"projects/{projekt_id}/tasks")
    if not wliczajac_zrobione:
        zadania = [z for z in zadania if not z.get("done")]
    return [_skrot(z) for z in zadania]


def utworz_zadanie(projekt_id: int, tytul: str, opis: str = "",
                   start: str | None = None, koniec: str | None = None,
                   termin: str | None = None, priorytet: int = 0) -> dict:
    ladunek: dict[str, Any] = {"title": tytul, "description": opis,
                                "priority": priorytet}
    for klucz, wartosc in (("start_date", start), ("end_date", koniec),
                            ("due_date", termin)):
        if wartosc is not None:
            ladunek[klucz] = _data(wartosc)
    return _skrot(_zapytaj("PUT", f"projects/{projekt_id}/tasks", ladunek))


def zaktualizuj_zadanie(zadanie_id: int, tytul: str | None = None,
                        opis: str | None = None, zrobione: bool | None = None,
                        postep_proc: int | None = None,
                        start: str | None = None, koniec: str | None = None,
                        termin: str | None = None,
                        priorytet: int | None = None) -> dict:
    # Vikunja zastępuje cały obiekt, więc najpierw pobieramy stan bieżący.
    # Wysłanie samych zmienionych pól wyzerowałoby resztę.
    biezace = _zapytaj("GET", f"tasks/{zadanie_id}")
    if tytul is not None:
        biezace["title"] = tytul
    if opis is not None:
        biezace["description"] = opis
    if zrobione is not None:
        biezace["done"] = zrobione
    if postep_proc is not None:
        biezace["percent_done"] = max(0, min(100, postep_proc)) / 100
    if priorytet is not None:
        biezace["priority"] = priorytet
    for klucz, wartosc in (("start_date", start), ("end_date", koniec),
                            ("due_date", termin)):
        if wartosc is not None:
            biezace[klucz] = _data(wartosc)
    return _skrot(_zapytaj("POST", f"tasks/{zadanie_id}", biezace))


def powiaz_zadania(zadanie_id: int, inne_id: int, rodzaj: str = "blocked") -> dict:
    """Zależność między zadaniami — to z niej powstają strzałki na Gancie.

    Rodzaje używane w praktyce: 'blocked' (to zadanie czeka na inne),
    'blocking' (to zadanie blokuje inne), 'subtask', 'parenttask'.
    """
    _zapytaj("PUT", f"tasks/{zadanie_id}/relations",
             {"other_task_id": inne_id, "relation_kind": rodzaj})
    return {"ok": True, "zadanie": zadanie_id, "rodzaj": rodzaj, "z": inne_id}


def przeglad() -> dict:
    """Stan wszystkich projektów naraz — to, od czego zaczyna się nadzór.

    Świadomie liczy przeterminowane po stronie klienta, a nie filtrem Vikunji:
    filtr trzeba by budować jako string i przy literówce zwraca po cichu pustkę,
    a tu chodzi o liczbę, na której podejmuje się decyzje.
    """
    dzis = datetime.now(timezone.utc).date().isoformat()
    wynik: dict[str, Any] = {"na_dzien": dzis, "projekty": []}
    lacznie_otwarte = lacznie_spoznione = 0

    for projekt in lista_projektow():
        zadania = _wszystkie_strony(f"projects/{projekt['id']}/tasks")
        otwarte = [z for z in zadania if not z.get("done")]
        spoznione = [
            z for z in otwarte
            if (_ustawiona(z.get("due_date")) and z["due_date"][:10] < dzis)
            or (_ustawiona(z.get("end_date")) and z["end_date"][:10] < dzis)
        ]
        lacznie_otwarte += len(otwarte)
        lacznie_spoznione += len(spoznione)
        wynik["projekty"].append({
            "id": projekt["id"],
            "tytul": projekt["tytul"],
            "zadan_lacznie": len(zadania),
            "otwartych": len(otwarte),
            "przeterminowanych": len(spoznione),
            "przeterminowane": [_skrot(z) for z in spoznione],
        })

    wynik["otwartych_lacznie"] = lacznie_otwarte
    wynik["przeterminowanych_lacznie"] = lacznie_spoznione
    return wynik


# --------------------------------------------------------------------------
# Warstwa MCP
# --------------------------------------------------------------------------

def zbuduj_serwer():
    from mcp.server import MCPServer

    serwer = MCPServer(
        name="nadzorca",
        instructions=(
            "Nadzór nad projektami w Vikunji. Daty podawaj jako "
            "YYYY-MM-DD. Priorytet 0-5, gdzie 5 to najwyższy. Zanim założysz nowy "
            "projekt, sprawdź listą, czy już nie istnieje."
        ),
    )

    @serwer.tool(description="Lista wszystkich projektów z ich identyfikatorami.")
    def projekty() -> list[dict]:
        return lista_projektow()

    @serwer.tool(description="Zakłada nowy projekt i zwraca jego identyfikator.")
    def nowy_projekt(tytul: str, opis: str = "") -> dict:
        return utworz_projekt(tytul, opis)

    @serwer.tool(description="Zadania w projekcie. Domyślnie pomija zrobione.")
    def zadania(projekt_id: int, wliczajac_zrobione: bool = False) -> list[dict]:
        return lista_zadan(projekt_id, wliczajac_zrobione)

    @serwer.tool(description=(
        "Zakłada zadanie. Daty w formacie YYYY-MM-DD. 'start' i 'koniec' rysują "
        "belkę na wykresie Gantta, 'termin' to sam deadline. Priorytet 0-5."))
    def nowe_zadanie(projekt_id: int, tytul: str, opis: str = "",
                     start: str | None = None, koniec: str | None = None,
                     termin: str | None = None, priorytet: int = 0) -> dict:
        return utworz_zadanie(projekt_id, tytul, opis, start, koniec, termin,
                              priorytet)

    @serwer.tool(description=(
        "Zmienia zadanie. Podaj tylko te pola, które mają się zmienić - reszta "
        "zostaje bez zmian. Pusty string w dacie kasuje datę."))
    def zmien_zadanie(zadanie_id: int, tytul: str | None = None,
                      opis: str | None = None, zrobione: bool | None = None,
                      postep_proc: int | None = None, start: str | None = None,
                      koniec: str | None = None, termin: str | None = None,
                      priorytet: int | None = None) -> dict:
        return zaktualizuj_zadanie(zadanie_id, tytul, opis, zrobione,
                                    postep_proc, start, koniec, termin, priorytet)

    @serwer.tool(description=(
        "Ustawia zależność między zadaniami - z tego powstają strzałki na Gancie. "
        "Rodzaj: blocked, blocking, subtask, parenttask."))
    def zaleznosc(zadanie_id: int, inne_id: int, rodzaj: str = "blocked") -> dict:
        return powiaz_zadania(zadanie_id, inne_id, rodzaj)

    @serwer.tool(description=(
        "Stan wszystkich projektów naraz: ile zadań otwartych i co jest "
        "przeterminowane. Od tego zaczynaj rozmowę o postępach."))
    def stan() -> dict:
        return przeglad()

    return serwer


def _sprawdz() -> int:
    """Diagnostyka: czy konfiguracja, sieć i uprawnienia tokenu są w porządku."""
    try:
        url, _ = _konfiguracja()
        print(f"konfiguracja  : {KONFIG} (prawa OK)")
        print(f"adres         : {url}")
        projekty = lista_projektow()
        print(f"polaczenie    : OK, projektow: {len(projekty)}")
        for p in projekty:
            print(f"                [{p['id']:3}] {p['tytul']}")
        stan = przeglad()
        print(f"zadan otwartych      : {stan['otwartych_lacznie']}")
        print(f"przeterminowanych    : {stan['przeterminowanych_lacznie']}")
    except BladVikunji as e:
        print(f"BLAD: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    if "--sprawdz" in sys.argv:
        raise SystemExit(_sprawdz())
    zbuduj_serwer().run(transport="stdio")
