"""Model 3D dolnej części Regału 2 — do uruchomienia w FreeCAD.

Buduje bryłowy model przebudowy: sześć nowych półek z przegrodami usztywniającymi
w przestrzeni 142 cm, którą dziś zajmuje jedna pusta półka.

Uruchomienie (bez GUI):
    freecadcmd model_regalu.py

Wynik: warsztat/regal-2.FCStd (do otwarcia i modyfikacji) oraz warsztat/regal-2.step
(format uniwersalny, otworzy każdy program CAD).

Wszystkie wymiary pochodzą z bazy magazynu i z planu cięcia - jedno miejsce do zmiany
jest niżej, w sekcji WYMIARY. Zmiana któregokolwiek przelicza cały model.
"""

import sys
from pathlib import Path

import FreeCAD as App
import Part

# ============================================================ WYMIARY (mm) ===

REGAL_SZER = 860.0        # wewnętrzna szerokość regału (zmierzona)
REGAL_GLEB = 500.0        # głębokość
PRZESTRZEN = 1420.0       # prześwit dolnej półki - tyle mamy do podziału
SCIANKA = 20.0            # grubość ścianki starej szafy

POLKA_DL = 855.0          # 860 minus 5 mm luzu, żeby półka weszła
POLKA_GLEB = 495.0
POLKA_GRUB = 18.0         # OSB-3
DESKA_GRUB = 20.0         # stara deska z blatu biurka (jedna z sześciu)

LISTWA_SZER = 20.0        # podpory boczne
LISTWA_WYS = 30.0

POLEK = 6                 # nowych półek -> 7 poziomów

KOLOR_OSB = (0.83, 0.72, 0.51)
KOLOR_DESKA = (0.45, 0.31, 0.22)
KOLOR_PRZEGRODA = (0.62, 0.72, 0.85)
KOLOR_LISTWA = (0.85, 0.80, 0.60)
KOLOR_SCIANKA = (0.72, 0.72, 0.72)


def poziomy() -> list[float]:
    """Wysokości spodu każdej półki, licząc od dna przestrzeni.

    Grubości półek odejmujemy od prześwitu i dzielimy RESZTĘ na równe komory -
    inaczej dolne komory wyszłyby wyższe od górnych o sumę grubości.
    """
    suma_grubosci = (POLEK - 1) * POLKA_GRUB + DESKA_GRUB
    komora = (PRZESTRZEN - suma_grubosci) / (POLEK + 1)
    wysokosci, z = [], komora
    for i in range(POLEK):
        wysokosci.append(z)
        z += (DESKA_GRUB if i == POLEK - 1 else POLKA_GRUB) + komora
    return wysokosci


def klocek(doc, nazwa, dl, szer, wys, poz, kolor):
    o = doc.addObject("Part::Box", nazwa)
    o.Length, o.Width, o.Height = dl, szer, wys
    o.Placement = App.Placement(App.Vector(*poz), App.Rotation(0, 0, 0, 1))
    if hasattr(o, "ViewObject") and o.ViewObject:
        o.ViewObject.ShapeColor = kolor
    return o


def zbuduj():
    doc = App.newDocument("regal2")
    wysokosci = poziomy()
    komora = (PRZESTRZEN - (POLEK - 1) * POLKA_GRUB - DESKA_GRUB) / (POLEK + 1)

    # Ścianki boczne - tylko dla kontekstu, żeby było widać, w czym to siedzi.
    for x in (-SCIANKA, REGAL_SZER):
        klocek(doc, "Scianka", SCIANKA, REGAL_GLEB, PRZESTRZEN, (x, 0, 0), KOLOR_SCIANKA)

    luz = (REGAL_SZER - POLKA_DL) / 2      # po 2,5 mm z każdej strony

    for i, z in enumerate(wysokosci):
        ostatnia = i == POLEK - 1
        grubosc = DESKA_GRUB if ostatnia else POLKA_GRUB
        nazwa = "Polka_deska" if ostatnia else f"Polka_{i+1}"
        kolor = KOLOR_DESKA if ostatnia else KOLOR_OSB
        klocek(doc, nazwa, POLKA_DL, POLKA_GLEB, grubosc, (luz, 0, z), kolor)

        # Podpory boczne: listwa przykręcona do ścianki, na niej leży półka.
        for x in (0.0, REGAL_SZER - LISTWA_SZER):
            klocek(doc, f"Listwa_{i+1}", LISTWA_SZER, POLKA_GLEB, LISTWA_WYS,
                    (x, 0, z - LISTWA_WYS), KOLOR_LISTWA)

        # Przegroda pionowa w połowie szerokości: dzieli rozpiętość z 860 na 428 mm,
        # przez co ugięcie spada szesnastokrotnie. Wycinana z odpadu, więc za darmo.
        klocek(doc, f"Przegroda_{i+1}", POLKA_GRUB, POLKA_GLEB, komora,
                (REGAL_SZER / 2 - POLKA_GRUB / 2, 0, z - komora), KOLOR_PRZEGRODA)

    # Przegroda w najwyższej komorze (nad ostatnią półką) - domyka układ.
    klocek(doc, "Przegroda_gorna", POLKA_GRUB, POLKA_GLEB, komora,
            (REGAL_SZER / 2 - POLKA_GRUB / 2, 0, wysokosci[-1] + DESKA_GRUB), KOLOR_PRZEGRODA)

    doc.recompute()
    return doc, wysokosci, komora


def main():
    katalog = Path(__file__).resolve().parent / "warsztat"
    katalog.mkdir(exist_ok=True)
    doc, wysokosci, komora = zbuduj()

    fcstd = katalog / "regal-2.FCStd"
    doc.saveAs(str(fcstd))

    bryly = [o.Shape for o in doc.Objects if hasattr(o, "Shape")]
    step = katalog / "regal-2.step"
    Part.export([o for o in doc.Objects if hasattr(o, "Shape")], str(step))

    print(f"\nModel: {POLEK} półek, {POLEK + 1} poziomów")
    print(f"Komora (prześwit): {komora:.1f} mm")
    print("Spody półek nad dnem przestrzeni:")
    for i, z in enumerate(wysokosci, 1):
        print(f"  półka {i}: {z:7.1f} mm" + ("   <- stara deska z biurka" if i == POLEK else ""))
    objetosc = sum(s.Volume for s in bryly) / 1e9
    print(f"\nŁączna objętość brył: {objetosc:.4f} m³")
    print(f"Zapisano:\n  {fcstd}\n  {step}")


main()
