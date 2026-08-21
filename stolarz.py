"""Stolarz — planowanie półek w istniejącej przestrzeni.

Wydzielone z przebudowy szafy na regał na łożyska. Za każdym razem liczy się to samo:
ile półek wejdzie, czy się ugną, jak pociąć płytę i ile zostanie odpadu — zmieniają się
tylko wymiary i materiał.

    python stolarz.py --wysokosc 1200 --szerokosc 760 --glebokosc 470 --scianka 16

CZEGO TO NARZĘDZIE NIE ROBI: nie zna ciężaru zawartości ani tego, jak wysoko sięgasz.
Obciążenie podaje się z ręki, bo 20 kg złożonych ubrań i 60 kg łożysk to dwa różne
światy, a program nie zgadnie, co wstawisz na półkę.

Cztery rzeczy, które w praktyce decydują o powodzeniu, a łatwo je pominąć:

  * RZAZ — piła zjada ~4 mm na cięcie. Przy pięciu pasach po 500 mm z arkusza 2500 mm
    ostatni wychodzi o 16 mm węższy niż pozostałe.
  * PEŁZANIE — płyta pod stałym obciążeniem dogina się latami. Ugięcie policzone
    „na dziś" trzeba podwoić, żeby zobaczyć, jak półka będzie wyglądać za pięć lat.
  * LUZ — półka cięta na dokładny wymiar wnętrza nie wejdzie. Zawsze kilka mm mniej.
  * PODPARCIE POŚRODKU — skraca rozpiętość o połowę, a ugięcie spada SZESNASTOKROTNIE
    (idzie z czwartą potęgą długości). Kawałek odpadu bije każdą rozsądną grubość płyty.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, field

# --- stałe warsztatowe ---------------------------------------------------------

RZAZ_MM = 4.0                 # ile materiału zjada tarcza na jedno cięcie
LUZ_SZEROKOSC_MM = 5.0        # żeby półka weszła między ścianki
WSPOLCZYNNIK_PELZANIA = 2.0   # ugięcie po latach / ugięcie początkowe
DOPUSZCZALNE_UGIECIE = 200.0  # L/200 — granica, powyżej której widać wygięcie


@dataclass(frozen=True)
class Material:
    """Płyta: grubość, sztywność i format arkusza."""
    nazwa: str
    grubosc: float
    E: float                  # moduł sprężystości przy zginaniu [MPa]
    arkusz: tuple[float, float] | None = None
    cena_arkusza: float | None = None

    @property
    def pole_arkusza(self) -> float:
        return self.arkusz[0] * self.arkusz[1] if self.arkusz else 0.0


# Wartości E przyjęte ostrożnie — producenci podają wyższe, ale płyta z marketu
# rzadko trafia w górną granicę normy.
OSB_18 = Material("OSB-3 18 mm", 18.0, 3500.0, (2500.0, 1250.0), 104.0)
WIOROWA_18 = Material("wiórowa surowa 18 mm", 18.0, 2800.0, (2800.0, 2070.0), 230.0)
LAMINOWANA_18 = Material("laminowana biała 18 mm", 18.0, 2800.0, (2800.0, 2070.0), None)
LAMINOWANA_16 = Material("laminowana biała 16 mm", 16.0, 2800.0, (2800.0, 2070.0), None)
SKLEJKA_18 = Material("sklejka 18 mm", 18.0, 7000.0, (2500.0, 1250.0), None)

MATERIALY = {m.nazwa: m for m in (OSB_18, WIOROWA_18, LAMINOWANA_18, LAMINOWANA_16, SKLEJKA_18)}


@dataclass
class Przestrzen:
    """Wnętrze, które zabudowujemy — wymiary w świetle."""
    wysokosc: float
    szerokosc: float
    glebokosc: float
    scianka: float = 18.0
    nazwa: str = "przestrzeń"


@dataclass
class Polka:
    dlugosc: float
    glebokosc: float

    @property
    def pole(self) -> float:
        return self.dlugosc * self.glebokosc


@dataclass
class Plan:
    przestrzen: Przestrzen
    material: Material
    polka: Polka
    ile_polek: int
    przeswit: float
    obciazenie_kg: float
    ugiecie: float
    ugiecie_po_latach: float
    granica: float
    podparcie_posrodku: bool

    @property
    def poziomy(self) -> int:
        return self.ile_polek + 1

    @property
    def ok(self) -> bool:
        return self.ugiecie_po_latach <= self.granica


def ugiecie_mm(rozpietosc: float, szerokosc_polki: float, grubosc: float,
                E: float, obciazenie_kg: float) -> float:
    """Belka swobodnie podparta, obciążenie równomierne: 5wL⁴/(384EI)."""
    I = szerokosc_polki * grubosc ** 3 / 12
    w = obciazenie_kg * 9.81 / rozpietosc
    return 5 * w * rozpietosc ** 4 / (384 * E * I)


def przeswit_dla(przestrzen: Przestrzen, material: Material, ile_polek: int) -> float:
    """Wysokość jednej komory. Grubości półek ODEJMUJEMY od przestrzeni przed podziałem —
    inaczej dolne komory wyszłyby wyższe od górnych o sumę grubości."""
    return (przestrzen.wysokosc - ile_polek * material.grubosc) / (ile_polek + 1)


def zaplanuj(przestrzen: Przestrzen, material: Material, ile_polek: int,
              obciazenie_kg: float, glebokosc_polki: float | None = None,
              podparcie_posrodku: bool = False) -> Plan:
    dlugosc = przestrzen.szerokosc - LUZ_SZEROKOSC_MM
    gleb = glebokosc_polki if glebokosc_polki is not None else przestrzen.glebokosc - LUZ_SZEROKOSC_MM
    rozpietosc = dlugosc / (2 if podparcie_posrodku else 1)
    obc = obciazenie_kg / (2 if podparcie_posrodku else 1)

    u = ugiecie_mm(rozpietosc, gleb, material.grubosc, material.E, obc)
    return Plan(
        przestrzen=przestrzen, material=material,
        polka=Polka(dlugosc, gleb), ile_polek=ile_polek,
        przeswit=przeswit_dla(przestrzen, material, ile_polek),
        obciazenie_kg=obciazenie_kg,
        ugiecie=u, ugiecie_po_latach=u * WSPOLCZYNNIK_PELZANIA,
        granica=dlugosc / DOPUSZCZALNE_UGIECIE,
        podparcie_posrodku=podparcie_posrodku,
    )


@dataclass
class Rozkroj:
    """Ile formatek wyjdzie z arkusza i co zostanie."""
    material: Material
    formatka: Polka
    sztuk_z_arkusza: int
    uklad: str
    arkuszy: int
    potrzeba: int
    odpad_mm2: float = 0.0
    opis_odpadu: list[str] = field(default_factory=list)

    @property
    def odpad_m2(self) -> float:
        return self.odpad_mm2 / 1e6

    @property
    def wykorzystanie(self) -> float:
        if not self.material.arkusz:
            return 0.0
        pole = self.arkuszy * self.material.pole_arkusza
        return 100.0 * (self.potrzeba * self.formatka.pole) / pole if pole else 0.0


def rozkroj(material: Material, formatka: Polka, potrzeba: int) -> Rozkroj:
    """Ile formatek z arkusza, przy obu orientacjach, z uwzględnieniem rzazu.

    Liczymy prosty układ siatkowy — dokładne pakowanie 2D dałoby czasem jedną sztukę
    więcej, ale wymaga cięć, których nie da się wykonać ręczną pilarką na kozłach.
    """
    if not material.arkusz:
        return Rozkroj(material, formatka, 0, "nieznany format arkusza", 0, potrzeba)

    A, B = material.arkusz

    def siatka(dl, szer, kdl, kszer):
        return int((dl + RZAZ_MM) // (kdl + RZAZ_MM)) * int((szer + RZAZ_MM) // (kszer + RZAZ_MM))

    wariant_a = siatka(A, B, formatka.dlugosc, formatka.glebokosc)
    wariant_b = siatka(A, B, formatka.glebokosc, formatka.dlugosc)
    if wariant_a >= wariant_b:
        na_arkusz, uklad = wariant_a, "dłuższy bok formatki wzdłuż arkusza"
    else:
        na_arkusz, uklad = wariant_b, "formatka obrócona o 90 stopni"

    if na_arkusz == 0:
        return Rozkroj(material, formatka, 0, "formatka nie mieści się w arkuszu", 0, potrzeba)

    arkuszy = math.ceil(potrzeba / na_arkusz)
    odpad = arkuszy * material.pole_arkusza - potrzeba * formatka.pole
    return Rozkroj(material, formatka, na_arkusz, uklad, arkuszy, potrzeba, odpad)


# ------------------------------------------------------------------ raport ----

def raport_planu(plan: Plan) -> str:
    p, m = plan.przestrzen, plan.material
    l = [
        f"{p.nazwa}: {p.wysokosc:.0f} x {p.szerokosc:.0f} x {p.glebokosc:.0f} mm "
        f"(ścianka {p.scianka:.0f} mm)",
        f"materiał: {m.nazwa}",
        "",
        f"  półek: {plan.ile_polek}   ->  {plan.poziomy} poziomów po {plan.przeswit:.0f} mm",
        f"  formatka: {plan.polka.dlugosc:.0f} x {plan.polka.glebokosc:.0f} mm",
        "",
        f"  obciążenie przyjęte: {plan.obciazenie_kg:.0f} kg na półkę",
        f"  ugięcie teraz:       {plan.ugiecie:.1f} mm",
        f"  ugięcie po latach:   {plan.ugiecie_po_latach:.1f} mm   "
        f"(granica {plan.granica:.1f} mm)   {'OK' if plan.ok else 'ZA DUZO'}",
    ]
    if plan.podparcie_posrodku:
        l.append("  (z podparciem pośrodku — rozpiętość liczona jako połowa)")
    if not plan.ok:
        l += ["", "  Co z tym zrobić: grubsza płyta, podparcie pośrodku"
                  " albo listwa usztywniająca pod krawędzią."]
    return "\n".join(l)


def raport_rozkroju(r: Rozkroj) -> str:
    if not r.sztuk_z_arkusza:
        return f"Rozkrój: {r.uklad}"
    return "\n".join([
        f"arkusz {r.material.arkusz[0]:.0f} x {r.material.arkusz[1]:.0f} mm",
        f"  {r.sztuk_z_arkusza} formatek z arkusza ({r.uklad})",
        f"  potrzeba {r.potrzeba} -> kupujesz {r.arkuszy} arkusz(e)",
        f"  odpad: {r.odpad_m2:.2f} m²   wykorzystanie: {r.wykorzystanie:.0f}%",
    ])


def main() -> int:
    ap = argparse.ArgumentParser(description="Planowanie półek w istniejącej przestrzeni.")
    ap.add_argument("--wysokosc", type=float, required=True, help="prześwit w mm")
    ap.add_argument("--szerokosc", type=float, required=True, help="szerokość wewnętrzna w mm")
    ap.add_argument("--glebokosc", type=float, required=True, help="głębokość w mm")
    ap.add_argument("--scianka", type=float, default=18.0)
    ap.add_argument("--material", default="OSB-3 18 mm", choices=list(MATERIALY))
    ap.add_argument("--obciazenie", type=float, default=20.0, help="kg na półkę")
    ap.add_argument("--polek", type=int, help="ile półek; bez tego pokaże warianty")
    ap.add_argument("--glebokosc-polki", type=float, help="jeśli formatka ma być płytsza")
    ap.add_argument("--sztuk", type=int, default=1, help="ile takich przestrzeni (np. 2 szafy)")
    ap.add_argument("--nazwa", default="przestrzeń")
    args = ap.parse_args()

    prz = Przestrzen(args.wysokosc, args.szerokosc, args.glebokosc, args.scianka, args.nazwa)
    mat = MATERIALY[args.material]

    warianty = [args.polek] if args.polek else range(1, 7)
    print()
    for n in warianty:
        plan = zaplanuj(prz, mat, n, args.obciazenie, args.glebokosc_polki)
        if args.polek:
            print(raport_planu(plan))
            print()
            r = rozkroj(mat, plan.polka, n * args.sztuk)
            print(raport_rozkroju(r))
        else:
            print(f"  {n} półek -> {plan.poziomy} poziomów po {plan.przeswit:5.0f} mm   "
                   f"ugięcie po latach {plan.ugiecie_po_latach:4.1f} mm  "
                   f"{'OK' if plan.ok else 'za duzo'}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
