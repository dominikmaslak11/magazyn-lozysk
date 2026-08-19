"""Rysunek planu cięcia arkusza — PDF w skali.

Po co: plan cięcia w postaci rysunku ASCII rozjeżdża się w każdej aplikacji, która
użyje czcionki proporcjonalnej, a przy pile trzyma się telefon w jednej ręce i nie ma
czasu na odcyfrowywanie. Rysunek w skali pokazuje od razu, co z czego wychodzi.

Rysunek uwzględnia RZAZ, czyli materiał zjadany przez tarczę (ok. 4 mm na cięcie).
To nie jest szczegół: przy pięciu pasach po 500 mm z arkusza 2500 mm cztery rzazy
zabierają 16 mm i ostatni pas wychodzi o półtora centymetra węższy.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fpdf import FPDF

# --- wymiary rzeczywiste w mm ---
ARKUSZ_DL, ARKUSZ_SZER = 2500.0, 1250.0
PAS = 495.0          # szerokość pasa (5 pasów z długości arkusza)
POLKA_DL = 855.0     # długość półki odcinana z pasa
RZAZ = 4.0           # ile zjada tarcza na jedno cięcie
PASOW = 5

SKALA = 0.088        # arkusz 2500 mm zajmie 220 mm na papierze A4 poziomo


@dataclass
class Ustawienie:
    x: float          # lewy górny róg rysunku na stronie, w mm papieru
    y: float

    def px(self, mm: float) -> float:
        return self.x + mm * SKALA

    def py(self, mm: float) -> float:
        return self.y + mm * SKALA


class PlanCiecia(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 15)
        self.cell(0, 8, "Plan ciecia - 5 polek 855 x 495 mm", align="C", new_x="LMARGIN",
                   new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, f"Arkusz OSB-3 18 mm, 2500 x 1250 mm   |   skala 1:{1/SKALA:.0f}   |   "
                         f"rzaz tarczy {RZAZ:.0f} mm uwzgledniony",
                   align="C", new_x="LMARGIN", new_y="NEXT")

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 5, "Magazyn Lozysk - warsztat/plan-ciecia.md", align="C")


def rysuj(pdf: PlanCiecia, u: Ustawienie) -> None:
    """Arkusz z pasami, cieciami i odpadem."""
    wys_polki = POLKA_DL * SKALA
    wys_odpadu = (ARKUSZ_SZER - POLKA_DL - RZAZ) * SKALA
    szer_pasa = PAS * SKALA

    pdf.set_line_width(0.5)
    x = 0.0
    for nr in range(1, PASOW + 1):
        lx = u.px(x)
        # pole półki
        pdf.set_fill_color(207, 226, 243)
        pdf.set_draw_color(90, 90, 90)
        pdf.rect(lx, u.py(0), szer_pasa, wys_polki, style="FD")
        # pole odpadu
        pdf.set_fill_color(236, 236, 236)
        pdf.rect(lx, u.py(POLKA_DL + RZAZ), szer_pasa, wys_odpadu, style="FD")

        # opis półki - dwie linie, wyśrodkowane w pionie
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_xy(lx, u.py(0) + wys_polki / 2 - 5)
        pdf.cell(szer_pasa, 5, f"POLKA {nr}", align="C")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_xy(lx, u.py(0) + wys_polki / 2 + 1)
        pdf.cell(szer_pasa, 5, f"{POLKA_DL:.0f} x {PAS:.0f} mm", align="C")

        # opis odpadu - też dwie osobne linie
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(110, 110, 110)
        pdf.set_xy(lx, u.py(POLKA_DL + RZAZ) + wys_odpadu / 2 - 5)
        pdf.cell(szer_pasa, 4, "odpad", align="C")
        pdf.set_xy(lx, u.py(POLKA_DL + RZAZ) + wys_odpadu / 2 - 1)
        pdf.cell(szer_pasa, 4, f"{ARKUSZ_SZER - POLKA_DL - RZAZ:.0f} x {PAS:.0f}", align="C")
        pdf.set_text_color(0, 0, 0)

        x += PAS
        if nr < PASOW:
            xc = u.px(x + RZAZ / 2)
            pdf.set_draw_color(200, 0, 0)
            pdf.set_line_width(0.7)
            pdf.line(xc, u.py(0) - 7, xc, u.py(ARKUSZ_SZER) + 3)
            # numer cięcia w kółku nad linią
            pdf.set_fill_color(200, 0, 0)
            pdf.ellipse(xc - 2.6, u.py(0) - 12.5, 5.2, 5.2, style="F")
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_xy(xc - 4, u.py(0) - 12)
            pdf.cell(8, 4, str(nr), align="C")
            pdf.set_text_color(0, 0, 0)
            x += RZAZ

    # cięcie poprzeczne
    yc = u.py(POLKA_DL + RZAZ / 2)
    pdf.set_draw_color(200, 0, 0)
    pdf.set_line_width(0.7)
    pdf.line(u.px(0) - 3, yc, u.px(x) + 3, yc)
    pdf.set_fill_color(200, 0, 0)
    pdf.ellipse(u.px(x) + 4, yc - 2.6, 5.2, 5.2, style="F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_xy(u.px(x) + 2.6, yc - 2.1)
    pdf.cell(8, 4, "5-9", align="C")
    pdf.set_text_color(0, 0, 0)

    # obrys całego arkusza na wierzchu
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.8)
    pdf.rect(u.px(0), u.py(0), ARKUSZ_DL * SKALA, ARKUSZ_SZER * SKALA)

    # wymiary
    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(u.px(0), u.py(ARKUSZ_SZER) + 4)
    pdf.cell(ARKUSZ_DL * SKALA, 5, f"{ARKUSZ_DL:.0f} mm", align="C")
    pdf.set_xy(u.px(0) - 22, u.py(ARKUSZ_SZER / 2) - 2)
    pdf.cell(18, 5, f"{ARKUSZ_SZER:.0f} mm", align="R")


def zbuduj(sciezka: Path) -> Path:
    pdf = PlanCiecia(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()

    u = Ustawienie(x=38, y=40)
    rysuj(pdf, u)

    y = u.y + ARKUSZ_SZER * SKALA + 14
    pdf.set_xy(16, y)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Kolejnosc ciec", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8.5)
    linie = [
        (f"1-4", f"cztery ciecia wzdluz arkusza: piec pasow po {PAS:.0f} mm "
                  f"(NIE po 500 - cztery rzazy zabieraja {4*RZAZ:.0f} mm i ostatni pas "
                  f"wyszedlby na {ARKUSZ_DL - 4*PAS - 4*RZAZ:.0f} mm)"),
        (f"5-9", f"z kazdego pasa odcinasz {POLKA_DL:.0f} mm; zostaje kawalek "
                  f"{ARKUSZ_SZER - POLKA_DL - RZAZ:.0f} x {PAS:.0f} mm - zabierz, przyda sie na przegrodki"),
    ]
    for nr, tresc in linie:
        pdf.set_x(16)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.cell(10, 5, nr)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.cell(0, 5, tresc, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 8.5)
    for linia in (
        "Najpierw WSZYSTKIE ciecia wzdluzne, potem poprzeczne - inaczej piec razy ustawiasz ten sam wymiar.",
        "Pierwszy pas przymierz do regalu, ZANIM potniesz reszte - z odpadu 391 mm nie wykroisz kolejnej polki.",
        f"Szosta polka: stara deska z blatu biurka, tnij w domu na {POLKA_DL:.0f} x {PAS:.0f} mm.",
    ):
        pdf.set_x(16)
        pdf.cell(0, 5, linia, new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(sciezka))
    return sciezka


if __name__ == "__main__":
    import sys
    cel = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("warsztat/plan-ciecia.pdf")
    cel.parent.mkdir(parents=True, exist_ok=True)
    print("Zapisano:", zbuduj(cel))
