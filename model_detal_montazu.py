"""Detal montażowy: co trzyma półkę, a co tylko pilnuje przegrody.

Po co ten model: w rozmowie zlały się trzy różne rzeczy - listwy nośne, przegroda
i kątowniki - i wyszło wrażenie, że trzeba wybrać jedno z nich. Nie trzeba, bo
robią co innego:

  * LISTWA (żółta)   - na niej LEŻY półka. Element nośny, w obu meblach.
  * PRZEGRODA (niebieska) - podpiera półkę POŚRODKU, przez co rozpiętość spada
    z 855 na 428 mm. Bez niej płyta 11 mm ugina się 25 mm. Też nośna.
  * KĄTOWNIK (czerwony) - NIE podpiera niczego. Trzyma tylko przegrodę, żeby
    nie uciekła w bok. Element porządkowy, nie konstrukcyjny.
  * PASEK (zielony)  - usztywnia półkę szafy od spodu przy przedniej krawędzi.
    Zastępuje przegrodę tam, gdzie przegroda przeszkadzałaby w składaniu ubrań.

Uruchamianie:  freecadcmd model_detal_montazu.py
"""

import os
import sys

import FreeCAD as App
import Part

WYNIKI = os.environ.get("LOZYSKA_WYNIKI", os.path.dirname(os.path.abspath(__file__)))
KATALOG = os.path.join(WYNIKI, "warsztat")

KOLOR_PLYTA = (0.83, 0.72, 0.51)
KOLOR_LISTWA = (0.95, 0.80, 0.25)
KOLOR_PRZEGRODA = (0.35, 0.60, 0.90)
KOLOR_KATOWNIK = (0.90, 0.25, 0.20)
KOLOR_PASEK = (0.35, 0.75, 0.35)
KOLOR_SCIANKA = (0.70, 0.70, 0.70)


def klocek(doc, nazwa, dx, dy, dz, poz, kolor=None):
    """Kolorów NIE ustawiamy tutaj: freecadcmd nie ma warstwy graficznej i próba
    dotknięcia ViewObject wywala skrypt bez czytelnego komunikatu. Kolory nadaje
    skrypt renderujący, po przedrostku nazwy."""
    o = doc.addObject("Part::Feature", nazwa)
    o.Shape = Part.makeBox(dx, dy, dz, App.Vector(*poz))
    return o


def katownik(doc, nazwa, poz, dlugosc=40.0, grubosc=2.5, ramie=40.0, obrot=1):
    """Kątownik montażowy 40x40: dwa ramiona zespolone w L.

    'obrot' = 1 albo -1 - kątownik siedzi z lewej albo z prawej strony przegrody,
    zawsze ramieniem poziomym na półce, pionowym na przegrodzie.
    """
    x, y, z = poz
    poziome = Part.makeBox(ramie, dlugosc, grubosc, App.Vector(x if obrot > 0 else x - ramie, y, z))
    pionowe = Part.makeBox(grubosc, dlugosc, ramie,
                           App.Vector(x if obrot > 0 else x - grubosc, y, z))
    o = doc.addObject("Part::Feature", nazwa)
    o.Shape = poziome.fuse(pionowe)
    return o


# ---------------------------------------------------- REGAŁ: jedna komora ----

def detal_regalu(doc):
    SZER, GLEB, GRUB = 855.0, 495.0, 11.0
    SCIANKA, LISTWA_SZER, LISTWA_WYS = 20.0, 20.0, 30.0
    KOMORA = 192.0

    klocek(doc, "R_scianka_lewa", SCIANKA, GLEB, 320, (-SCIANKA, 0, -60), KOLOR_SCIANKA)
    klocek(doc, "R_scianka_prawa", SCIANKA, GLEB, 320, (SZER, 0, -60), KOLOR_SCIANKA)

    klocek(doc, "R_polka_dolna", SZER, GLEB, GRUB, (0, 0, 0), KOLOR_PLYTA)
    z_gora = GRUB + KOMORA
    klocek(doc, "R_polka_gorna", SZER, GLEB, GRUB, (0, 0, z_gora), KOLOR_PLYTA)

    # Listwy nośne - półka górna na nich leży. Przykręcone do ścianek.
    for x, nazwa in ((0.0, "R_listwa_lewa"), (SZER - LISTWA_SZER, "R_listwa_prawa")):
        klocek(doc, nazwa, LISTWA_SZER, GLEB, LISTWA_WYS,
               (x, 0, z_gora - LISTWA_WYS), KOLOR_LISTWA)

    # Przegroda pionowa - to ONA robi z rozpietosci 855 mm dwie po 428 mm.
    x_przeg = SZER / 2 - GRUB / 2
    klocek(doc, "R_przegroda", GRUB, GLEB, KOMORA, (x_przeg, 0, GRUB), KOLOR_PRZEGRODA)

    # Kątowniki: po jednym z każdej strony przegrody, przy DOLNEJ półce.
    # Nie niosą obciążenia - pilnują, żeby przegroda nie przesunęła się w bok.
    for y in (60.0, GLEB - 60.0 - 40.0):
        katownik(doc, f"R_katownik_L_{int(y)}", (x_przeg, y, GRUB), obrot=-1)
        katownik(doc, f"R_katownik_P_{int(y)}", (x_przeg + GRUB, y, GRUB), obrot=1)
    return z_gora


# ---------------------------------------------------- SZAFA: jedna półka ----

def detal_szafy(doc, przesuniecie_x):
    SZER, GLEB, GRUB = 755.0, 450.0, 11.0
    SCIANKA, LISTWA = 16.0, 20.0
    PASEK_WYS = 40.0
    X = przesuniecie_x

    klocek(doc, "S_scianka_lewa", SCIANKA, GLEB, 260, (X - SCIANKA, 0, -60), KOLOR_SCIANKA)
    klocek(doc, "S_scianka_prawa", SCIANKA, GLEB, 260, (X + SZER, 0, -60), KOLOR_SCIANKA)

    klocek(doc, "S_polka", SZER, GLEB, GRUB, (X, 0, 0), KOLOR_PLYTA)

    for x, nazwa in ((X, "S_listwa_lewa"), (X + SZER - LISTWA, "S_listwa_prawa")):
        klocek(doc, nazwa, LISTWA, GLEB, LISTWA, (x, 0, -LISTWA), KOLOR_LISTWA)

    # Pasek usztywniajacy POD PRZEDNIA krawedzia, na sztorc.
    # Tu NIE MA przegrody ani katownikow - przegroda dzielilaby polke na dwie
    # komory, a w szafie na ubrania to przeszkadza.
    klocek(doc, "S_pasek", SZER, GRUB, PASEK_WYS, (X, 0, -PASEK_WYS), KOLOR_PASEK)


def main():
    doc = App.newDocument("detal-montazu")
    detal_regalu(doc)
    detal_szafy(doc, 1200.0)
    doc.recompute()
    os.makedirs(KATALOG, exist_ok=True)
    sciezka = os.path.join(KATALOG, "detal-montazu.FCStd")
    doc.saveAs(sciezka)
    print("Zapisano:", sciezka)
    print(f"  obiektow: {len(doc.Objects)}")


main()
