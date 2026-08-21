"""Model 3D zabudowy szafy na ubrania — do uruchomienia w FreeCAD.

    freecadcmd model_szafy.py

Wynik: warsztat/szafa.FCStd i warsztat/szafa.step

Wymiary pochodzą z pomiaru i z obliczeń w stolarz.py. Zmiana czegokolwiek w sekcji
WYMIARY przelicza cały model — łącznie z rozstawem półek, bo grubości są odejmowane
od prześwitu przed podziałem.
"""

import os
import sys
from pathlib import Path

import FreeCAD as App
import Part

# ============================================================ WYMIARY (mm) ===

WYSOKOSC = 1200.0        # prześwit do zabudowania
SZEROKOSC = 760.0        # szerokość wewnętrzna
GLEBOKOSC = 470.0        # głębokość wnętrza
SCIANKA = 16.0           # grubość ścianki szafy

POLEK = 3                # -> 4 poziomy
POLKA_GRUB = 18.0
POLKA_DL = SZEROKOSC - 5.0        # 5 mm luzu, żeby weszła
POLKA_GLEB = 450.0                # płytsza od wnętrza: 2 cm zapasu na zawiasy i drzwi

# Listwy nośne pod półkami. W szafie na ubrania nie dajemy przegród pionowych -
# przeszkadzałyby przy układaniu, a przy 20 kg płyta 18 mm i tak mieści się w normie.
LISTWA = (20.0, 20.0)             # przekrój
SZAF = 2

KOLOR_PLYTA = (0.95, 0.95, 0.93)  # biała laminowana
KOLOR_SZAFA = (0.80, 0.78, 0.74)
KOLOR_LISTWA = (0.85, 0.78, 0.58)


def przeswit() -> float:
    """Grubości półek odejmujemy PRZED podziałem, inaczej dolne komory byłyby wyższe."""
    return (WYSOKOSC - POLEK * POLKA_GRUB) / (POLEK + 1)


def klocek(doc, nazwa, dl, szer, wys, poz, kolor):
    o = doc.addObject("Part::Box", nazwa)
    o.Length, o.Width, o.Height = dl, szer, wys
    o.Placement = App.Placement(App.Vector(*poz), App.Rotation(0, 0, 0, 1))
    if hasattr(o, "ViewObject") and o.ViewObject:
        o.ViewObject.ShapeColor = kolor
    return o


def zbuduj_szafe(doc, x_offset: float, nr: int) -> None:
    k = przeswit()
    luz = (SZEROKOSC - POLKA_DL) / 2

    # korpus szafy - dla kontekstu
    for x in (x_offset - SCIANKA, x_offset + SZEROKOSC):
        klocek(doc, f"Scianka_{nr}", SCIANKA, GLEBOKOSC, WYSOKOSC, (x, 0, 0), KOLOR_SZAFA)
    for z in (-SCIANKA, WYSOKOSC):
        klocek(doc, f"Poziom_{nr}", SZEROKOSC + 2 * SCIANKA, GLEBOKOSC, SCIANKA,
                (x_offset - SCIANKA, 0, z), KOLOR_SZAFA)

    z = k
    for i in range(1, POLEK + 1):
        klocek(doc, f"Polka_{nr}_{i}", POLKA_DL, POLKA_GLEB, POLKA_GRUB,
                (x_offset + luz, 0, z), KOLOR_PLYTA)
        # listwy nośne na obu ściankach
        for x in (x_offset, x_offset + SZEROKOSC - LISTWA[0]):
            klocek(doc, f"Listwa_{nr}_{i}", LISTWA[0], POLKA_GLEB, LISTWA[1],
                    (x, 0, z - LISTWA[1]), KOLOR_LISTWA)
        z += POLKA_GRUB + k


def main():
    doc = App.newDocument("szafa")
    for nr in range(SZAF):
        zbuduj_szafe(doc, nr * (SZEROKOSC + 2 * SCIANKA + 120.0), nr + 1)
    doc.recompute()

    # Katalog wynikow: domyslnie obok kodu, ale na serwerze katalog z kodem
    # to klon gita - zapisywanie do niego brudzi produkcje.
    katalog = Path(os.environ.get("LOZYSKA_WYNIKI",
                                  Path(__file__).resolve().parent)) / "warsztat"
    katalog.mkdir(exist_ok=True)
    fcstd = katalog / "szafa.FCStd"
    doc.saveAs(str(fcstd))
    Part.export([o for o in doc.Objects if hasattr(o, "Shape")], str(katalog / "szafa.step"))

    k = przeswit()
    print(f"\n{SZAF} szafy po {POLEK} półki = {SZAF * POLEK} formatek "
           f"{POLKA_DL:.0f} x {POLKA_GLEB:.0f} x {POLKA_GRUB:.0f} mm")
    print(f"Prześwit: {POLEK + 1} poziomy po {k:.0f} mm")
    print("Wysokości spodów półek nad dnem:")
    z = k
    for i in range(1, POLEK + 1):
        print(f"   półka {i}: {z:6.0f} mm")
        z += POLKA_GRUB + k
    print(f"\nZapisano:\n  {fcstd}\n  {katalog / 'szafa.step'}")


main()
