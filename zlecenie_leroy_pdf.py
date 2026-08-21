"""Zlecenie docięcia — jedna kartka do zostawienia na ladzie.

Osobny dokument od planu cięcia. Tamten ma 9 stron i pięć z nich dotyczy roboty
w domu; zostawiony na ladzie wprowadza w błąd, bo pracownik nie wie, które rysunki
go dotyczą.

Ten ma być kompletny, jednoznaczny i mieścić się na dwóch kartkach:
strona 1 — co zrobić i jak się skontaktować, strona 2 — rysunek formatki.

Zasada: wszystko, czego sklep potrzebuje, musi być NA TEJ KARTCE. Bez odsyłaczy
do innych dokumentów, bez "patrz strona 6".
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

KLIENT = "Dominik Maslak"
EMAIL = "dominikmaslak11@gmail.com"

FORMATKA = (755.0, 450.0)
SZTUK = 6
MATERIAL = "Plyta meblowa laminowana BIALA 18 mm"
POWIERZCHNIA = 2.04


class Zlecenie(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 4, f"{KLIENT}  |  {EMAIL}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 7)
        self.cell(0, 4, "Dokument wygenerowany automatycznie", align="C")


def pole(pdf, etykieta: str, szerokosc: float, wysokosc: float = 11.0) -> None:
    """Ramka z etykietą do wypełnienia długopisem przez obsługę."""
    x, y = pdf.get_x(), pdf.get_y()
    pdf.set_draw_color(120, 120, 120)
    pdf.set_line_width(0.3)
    pdf.rect(x, y, szerokosc, wysokosc)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.set_xy(x + 2, y + 1)
    pdf.cell(szerokosc - 4, 3.5, etykieta)
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(x + szerokosc, y)


def strona_zlecenia(pdf) -> None:
    pdf.add_page()
    pdf.set_y(16)
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 12, "ZLECENIE DOCIECIA", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # --- kontakt ---
    pdf.set_x(18)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(24, 7, "Klient:")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(70, 7, KLIENT)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(20, 7, "Telefon:")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, ".............................................", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(18)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(24, 7, "E-mail:")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, EMAIL, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # --- co ciac ---
    pdf.set_x(18)
    pdf.set_fill_color(214, 234, 214)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(174, 9, "  DO DOCIECIA", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_x(22)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 7, MATERIAL, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_x(22)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, f"{SZTUK} formatek     {FORMATKA[0]:.0f} x {FORMATKA[1]:.0f} mm",
              new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(22)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"lacznie {POWIERZCHNIA:.2f} m2   |   rysunek formatki na drugiej stronie",
              new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # --- opcje ---
    pdf.set_x(22)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Termin", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(26)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(8, 7, "[  ]")
    pdf.cell(60, 7, "EXPRESS - ten sam dzien")
    pdf.cell(8, 7, "[  ]")
    pdf.cell(0, 7, "standardowy 2-3 dni", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(26)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 5, "Prosze o EXPRESS, jesli mozliwe.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_x(22)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Obrzeze", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(26)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(166, 6,
        "Prosze o oklejenie JEDNEGO DLUZSZEGO BOKU (755 mm) w kazdej formatce - "
        "to bedzie przednia krawedz polki. Jesli nie macie takiej uslugi, prosze "
        "o informacje, kupie rolke obrzeza.")
    pdf.ln(6)

    # --- czego NIE ---
    pdf.set_x(18)
    pdf.set_fill_color(245, 225, 225)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(174, 9, "  KUPUJE, ALE NIE ZLECAM CIECIA", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_x(22)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "Plyta OSB-3 18 mm, arkusz 2500 x 1250 mm  -  1 sztuka",
              new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(22)
    pdf.set_font("Helvetica", "I", 9.5)
    pdf.cell(0, 5.5, "Arkusz w calosci, potne go sam w kaciku majsterkowicza.",
              new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # --- pola dla sklepu ---
    pdf.set_x(18)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Do wypelnienia przez sklep", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_x(18)
    for etykieta, szer in (("Nr zlecenia", 54), ("Koszt ciecia", 54), ("Termin odbioru", 66)):
        pole(pdf, etykieta, szer)
    pdf.ln(14)
    pdf.set_x(18)
    pole(pdf, "Uwagi", 174, 20)


def strona_rysunku(pdf) -> None:
    pdf.add_page()
    pdf.set_y(18)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 9, "Rysunek formatki", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"{SZTUK} sztuk, {MATERIAL.lower()}", align="C",
              new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    S = 0.185
    dl, gl = FORMATKA[0] * S, FORMATKA[1] * S
    x0 = (210 - dl) / 2
    y0 = 60.0

    pdf.set_fill_color(250, 250, 248)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.6)
    pdf.rect(x0, y0, dl, gl, style="FD")

    # krawedz z obrzezem
    pdf.set_draw_color(0, 130, 0)
    pdf.set_line_width(2.4)
    pdf.line(x0, y0 + gl, x0 + dl, y0 + gl)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(0, 120, 0)
    pdf.set_xy(x0, y0 + gl + 3)
    pdf.cell(dl, 5, "TA KRAWEDZ - obrzeze (przod polki)", align="C")
    pdf.set_text_color(0, 0, 0)

    # wymiary
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.3)
    pdf.line(x0, y0 - 8, x0 + dl, y0 - 8)
    for x in (x0, x0 + dl):
        pdf.line(x, y0 - 10, x, y0 - 6)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_xy(x0, y0 - 17)
    pdf.cell(dl, 6, f"{FORMATKA[0]:.0f} mm", align="C")

    pdf.line(x0 - 8, y0, x0 - 8, y0 + gl)
    for y in (y0, y0 + gl):
        pdf.line(x0 - 10, y, x0 - 6, y)
    pdf.set_xy(x0 - 32, y0 + gl / 2 - 3)
    pdf.cell(22, 6, f"{FORMATKA[1]:.0f} mm", align="R")

    pdf.set_y(y0 + gl + 22)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "", 10)
    for linia in (
        f"Grubosc plyty: 18 mm.  Sztuk: {SZTUK}.  Lacznie {POWIERZCHNIA:.2f} m2.",
        "",
        "Formatki sa polkami do szafy o szerokosci wewnetrznej 760 mm -",
        "wymiar 755 mm uwzglednia 5 mm luzu na wsuniecie.",
        "Glebokosc 450 mm zamiast pelnych 470 mm, zeby zostal zapas na zawiasy.",
        "",
        "Wszystkie szesc formatek jest identycznych.",
    ):
        pdf.set_x(20)
        pdf.cell(0, 5.6, linia, new_x="LMARGIN", new_y="NEXT")


def buduj(sciezka: Path) -> Path:
    pdf = Zlecenie(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(False)
    strona_zlecenia(pdf)
    strona_rysunku(pdf)
    pdf.output(str(sciezka))
    return sciezka


if __name__ == "__main__":
    cel = Path(__file__).resolve().parent / "warsztat" / "zlecenie-leroy.pdf"
    cel.parent.mkdir(exist_ok=True)
    print("Zapisano:", buduj(cel))
