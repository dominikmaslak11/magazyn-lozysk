"""Serwer MCP do narzędzi stolarskich — liczenie, modele 3D i wysyłka PDF.

Po co własny, skoro gotowych serwerów MCP do FreeCAD jest kilkanaście: wszystkie
sprawdzone (neka-nat, bonninr i pochodne) łączą się przez RPC z **uruchomionym
FreeCAD-em z pulpitem**. Ten serwer stoi na maszynie bez X-ów i bez monitora,
więc tamta droga jest zamknięta. Tu FreeCAD wołamy przez `freecadcmd`, bezgłowo.

Drugi powód: te serwery dają setki ogólnych narzędzi CAD. Tu potrzeba czterech
konkretnych, które rozumieją TEN projekt — wymiary półek, cennik cięcia w Leroy
i gotowe modele regału oraz szafy.

Uruchomienie zdalne (Claude Code na laptopie, wykonanie na serwerze):
    claude mcp add warsztat -- ssh <serwer> /opt/magazyn-lozysk/venv/bin/python \\
        /opt/magazyn-lozysk/warsztat_mcp.py

Sprawdzenie na miejscu:
    ./venv/bin/python warsztat_mcp.py --sprawdz
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

KATALOG = Path(__file__).resolve().parent
sys.path.insert(0, str(KATALOG))

import stolarz  # noqa: E402
import zrzynki  # noqa: E402

# Wyniki NIE lądują w katalogu z kodem: na serwerze to klon gita.
WYNIKI = Path(os.environ.get("LOZYSKA_WYNIKI", Path.home() / "wyniki"))

MODELE = {
    "regal": ("model_regalu.py", "Regał 2 na łożyska — dolna część z półkami"),
    "szafa": ("model_szafy.py", "Szafa na ubrania 120 x 76 x 47 cm"),
}

LIMIT_FREECAD_S = 300  # Core 2 Duo liczy bryły wolno, ale nie w nieskończoność


def wycen_odpad(dlugosc_mm: float, szerokosc_mm: float, cena_zl: float,
                 express: bool = False, tne_sam: bool = False) -> dict:
    stawka = 0.0 if tne_sam else (zrzynki.CIECIE_EXPRESS if express
                                   else zrzynki.CIECIE_ZWYKLE)
    w = zrzynki.wyceniaj(dlugosc_mm, szerokosc_mm, cena_zl, stawka)
    return {
        "werdykt": w.werdykt,
        "polek": w.polek,
        "przegrod": w.przegrod,
        "ciec_do_zlecenia": w.ciec_polki if w.polek else w.ciec_przegrod,
        "koszt_ciecia_zl": round(w.koszt_ciecia, 2),
        "razem_zl": round(w.koszt_calkowity, 2),
        "cena_za_polke_zl": round(w.cena_za_polke, 2) if w.cena_za_polke else None,
        "polka_z_arkusza_zl": round(w.odniesienie, 2),
        "instrukcja": zrzynki.instrukcja_ciecia(w),
        "raport": zrzynki.raport(w),
    }


def _wycena_do_pdf(dlugosc_mm: float, szerokosc_mm: float, cena_zl: float,
                    express: bool, tne_sam: bool) -> tuple[Any, Path]:
    stawka = 0.0 if tne_sam else (zrzynki.CIECIE_EXPRESS if express
                                   else zrzynki.CIECIE_ZWYKLE)
    w = zrzynki.wyceniaj(dlugosc_mm, szerokosc_mm, cena_zl, stawka)
    WYNIKI.mkdir(parents=True, exist_ok=True)
    cel = WYNIKI / f"odpad-{dlugosc_mm:.0f}x{szerokosc_mm:.0f}-{cena_zl:.0f}zl.pdf"
    return w, zrzynki.buduj_pdf(w, cel)


def kartka_pdf(dlugosc_mm: float, szerokosc_mm: float, cena_zl: float,
                express: bool = False, tne_sam: bool = False) -> dict:
    w, sciezka = _wycena_do_pdf(dlugosc_mm, szerokosc_mm, cena_zl, express, tne_sam)
    return {"plik": str(sciezka), "werdykt": w.werdykt,
            "rozmiar_kb": round(sciezka.stat().st_size / 1024)}


def wyslij_wycene(dlugosc_mm: float, szerokosc_mm: float, cena_zl: float,
                   adres: str = "dominikmaslak11@gmail.com",
                   express: bool = False, tne_sam: bool = False) -> dict:
    from wysylka import wyslij_email

    w, sciezka = _wycena_do_pdf(dlugosc_mm, szerokosc_mm, cena_zl, express, tne_sam)
    wynik = wyslij_email(
        adres,
        f"Odpad OSB {dlugosc_mm:.0f}x{szerokosc_mm:.0f} - {w.werdykt}",
        zrzynki.raport(w) + "\n\n" + "\n".join(zrzynki.instrukcja_ciecia(w)),
        [sciezka])
    return {"werdykt": w.werdykt, "plik": str(sciezka), "poczta": wynik}


def plan_polek(wysokosc_mm: float, szerokosc_mm: float, glebokosc_mm: float,
                ile_polek: int, material: str = "OSB-3 18 mm",
                obciazenie_kg: float = 30.0, scianka_mm: float = 18.0) -> dict:
    m = stolarz.MATERIALY.get(material)
    if m is None:
        return {"blad": f"Nie znam materiału '{material}'. Dostępne: "
                        + ", ".join(sorted(stolarz.MATERIALY))}
    p = stolarz.Przestrzen("zabudowa", wysokosc_mm, szerokosc_mm, glebokosc_mm,
                            scianka_mm)
    plan = stolarz.zaplanuj(p, m, ile_polek, obciazenie_kg)
    return {
        "poziomow": plan.poziomy,
        "przeswit_mm": round(plan.przeswit, 1),
        "formatka_mm": f"{plan.polka.dlugosc:.0f} x {plan.polka.glebokosc:.0f}",
        "ugiecie_mm": round(plan.ugiecie, 2),
        "ugiecie_po_latach_mm": round(plan.ugiecie_po_latach, 2),
        "granica_mm": round(plan.granica, 2),
        "wytrzyma": plan.ok,
        "podparcie_posrodku": plan.podparcie_posrodku,
        "raport": stolarz.raport_planu(plan),
    }


def model_3d(ktory: str) -> dict:
    """Przelicza model parametryczny FreeCAD-em i zwraca ścieżki do plików."""
    wpis = MODELE.get(ktory)
    if wpis is None:
        return {"blad": f"Nie znam modelu '{ktory}'. Dostępne: {', '.join(MODELE)}"}
    skrypt, opis = wpis

    # Na laptopie FreeCAD bywa rozpakowanym AppImage'em spoza PATH - stąd FREECAD_CMD.
    freecad = os.environ.get("FREECAD_CMD") or None
    if freecad and not Path(freecad).exists():
        freecad = None
    for kandydat in ("freecadcmd", "FreeCADCmd") if freecad is None else ():
        sciezka = subprocess.run(["which", kandydat], capture_output=True, text=True)
        if sciezka.returncode == 0:
            freecad = sciezka.stdout.strip()
            break
    if freecad is None:
        return {"blad": "Nie ma freecadcmd. Instalacja: apt install freecad-python3"}

    WYNIKI.mkdir(parents=True, exist_ok=True)
    try:
        # Uruchamiamy w katalogu wyników, bo skrypty zapisują obok siebie -
        # a katalog z kodem to klon gita i ma zostać czysty.
        wynik = subprocess.run([freecad, str(KATALOG / skrypt)],
                                capture_output=True, text=True,
                                timeout=LIMIT_FREECAD_S, cwd=WYNIKI)
    except subprocess.TimeoutExpired:
        return {"blad": f"FreeCAD liczył dłużej niż {LIMIT_FREECAD_S} s i został przerwany."}

    pliki = sorted(str(p) for p in (WYNIKI / "warsztat").glob("*")
                   if p.suffix.lower() in (".fcstd", ".step"))
    return {"model": opis, "kod_wyjscia": wynik.returncode,
            "pliki": pliki,
            "wyjscie": (wynik.stdout or wynik.stderr)[-1500:]}


# --------------------------------------------------------------------------

def zbuduj_serwer():
    from mcp.server import MCPServer

    s = MCPServer(
        name="warsztat",
        instructions=(
            "Narzędzia stolarskie: wycena odpadów płyty, plany półek z rachunkiem "
            "ugięcia i modele 3D we FreeCAD. Wymiary podawaj w MILIMETRACH. "
            "Ceny w złotych. Cięcie w Leroy: 3 zł zwykłe, 6 zł express."
        ),
    )

    @s.tool(description=(
        "Czy odpad płyty OSB w markecie się opłaca. Wymiary w mm, cena w zł. "
        "Domyślnie zakłada cięcie zlecone w sklepie po 3 zł."))
    def odpad(dlugosc_mm: float, szerokosc_mm: float, cena_zl: float,
              express: bool = False, tne_sam: bool = False) -> dict:
        return wycen_odpad(dlugosc_mm, szerokosc_mm, cena_zl, express, tne_sam)

    @s.tool(description="Wycena odpadu jako gotowy PDF z rysunkiem rozkroju.")
    def odpad_pdf(dlugosc_mm: float, szerokosc_mm: float, cena_zl: float,
                  express: bool = False, tne_sam: bool = False) -> dict:
        return kartka_pdf(dlugosc_mm, szerokosc_mm, cena_zl, express, tne_sam)

    @s.tool(description="Wycena odpadu wysłana e-mailem razem z PDF-em.")
    def odpad_mailem(dlugosc_mm: float, szerokosc_mm: float, cena_zl: float,
                     adres: str = "dominikmaslak11@gmail.com",
                     express: bool = False, tne_sam: bool = False) -> dict:
        return wyslij_wycene(dlugosc_mm, szerokosc_mm, cena_zl, adres, express, tne_sam)

    @s.tool(description=(
        "Plan półek do zabudowy: prześwit między półkami, wymiar formatki i "
        "sprawdzenie ugięcia pod obciążeniem (także po latach)."))
    def polki(wysokosc_mm: float, szerokosc_mm: float, glebokosc_mm: float,
              ile_polek: int, material: str = "OSB-3 18 mm",
              obciazenie_kg: float = 30.0, scianka_mm: float = 18.0) -> dict:
        return plan_polek(wysokosc_mm, szerokosc_mm, glebokosc_mm, ile_polek,
                          material, obciazenie_kg, scianka_mm)

    @s.tool(description=(
        "Przelicza model 3D we FreeCAD (bezgłowo) i zapisuje FCStd oraz STEP. "
        "Dostępne modele: regal, szafa."))
    def model(ktory: str) -> dict:
        return model_3d(ktory)

    @s.tool(description="Lista materiałów płytowych, które zna kalkulator.")
    def materialy() -> list[dict]:
        return [{"nazwa": m.nazwa, "grubosc_mm": m.grubosc,
                 "arkusz_mm": f"{m.arkusz[0]:.0f} x {m.arkusz[1]:.0f}" if m.arkusz else None,
                 "cena_arkusza_zl": m.cena_arkusza}
                for m in stolarz.MATERIALY.values()]

    return s


def _sprawdz() -> int:
    print(f"katalog wynikow : {WYNIKI}")
    print(f"materialy       : {len(stolarz.MATERIALY)}")
    w = wycen_odpad(1700, 1000, 40)
    print(f"wycena odpadu   : {w['werdykt']}, {w['polek']} polek, "
          f"{w['cena_za_polke_zl']} zl/szt")
    fc = subprocess.run(["which", "freecadcmd"], capture_output=True, text=True)
    print(f"freecadcmd      : {fc.stdout.strip() or 'BRAK'}")
    try:
        from wysylka import SMTP_CONFIG
        print(f"poczta          : {'skonfigurowana' if SMTP_CONFIG.exists() else 'BRAK smtp.json'}")
    except Exception as e:
        print(f"poczta          : blad ({e})")
    return 0


if __name__ == "__main__":
    if "--sprawdz" in sys.argv:
        raise SystemExit(_sprawdz())
    zbuduj_serwer().run(transport="stdio")
