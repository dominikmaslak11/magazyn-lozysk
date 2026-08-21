"""Zestawienie kosztów zakupów w trzech sklepach — PDF.

Osobny dokument od planu cięcia: tamten mówi CO zrobić, ten WGDZIE i ZA ILE.
Ceny oznaczone są jako potwierdzone albo szacunkowe — bez tego rozróżnienia
zestawienie wygląda dokładniej, niż jest.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fpdf import FPDF

POTWIERDZONA = "potw."
SZACUNEK = "szac."
BRAK = "?"


@dataclass
class Pozycja:
    nazwa: str
    ilosc: str
    leroy: str
    leroy_status: str
    castorama: str
    castorama_status: str
    arsen: str
    arsen_status: str
    projekt: str


POZYCJE = [
    Pozycja("OSB-3 18 mm, arkusz 250x125 (kod LM 43226043)", "1 szt.",
            "104", POTWIERDZONA, "104", POTWIERDZONA, "?", BRAK, "regal"),
    Pozycja("plyta laminowana biala 18 mm, dociecie na wymiar", "2,04 m2",
            "78", POTWIERDZONA, "?", BRAK, "?", BRAK, "szafy"),
    Pozycja("listwa 20x30x2700 (kod LM 45216185)", "4 szt.",
            "48", SZACUNEK, "?", BRAK, "?", BRAK, "regal"),
    Pozycja("wkrety do drewna 4x35 ocynk", "100 szt.",
            "25", SZACUNEK, "25", SZACUNEK, "?", BRAK, "regal"),
    Pozycja("wkrety do drewna 3,5x30 ocynk", "100 szt.",
            "20", SZACUNEK, "20", SZACUNEK, "?", BRAK, "regal"),
    Pozycja("podporki do polek, kolek 5 mm", "24 szt.",
            "15", SZACUNEK, "15", SZACUNEK, "?", BRAK, "szafy"),
    Pozycja("obrzeze melaminowe biale, rolka 5 m", "1-2 szt.",
            "30", SZACUNEK, "30", SZACUNEK, "?", BRAK, "szafy"),
]


class Zestawienie(FPDF):
    def header(self):
        if self.page_no() != 1:
            return
        self.set_font("Helvetica", "B", 15)
        self.cell(0, 8, "Zestawienie kosztow - gdzie kupic", align="C",
                   new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "Regal na lozyska + polki do dwoch szaf   |   stan na 2026-08-21",
                   align="C", new_x="LMARGIN", new_y="NEXT")

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 5, "Magazyn Lozysk - warsztat/zestawienie-kosztow.pdf", align="C")


def buduj(sciezka: Path) -> Path:
    pdf = Zestawienie(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()
    pdf.set_y(30)

    # --- tabela ---
    kol = (108, 20, 30, 30, 30, 24)
    naglowki = ("pozycja", "ilosc", "Leroy Merlin", "Castorama", "Arsen Kalisz", "projekt")
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(225, 225, 225)
    pdf.set_x(14)
    for tekst, szer in zip(naglowki, kol):
        pdf.cell(szer, 7, tekst, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    suma_leroy = 0.0
    for p in POZYCJE:
        pdf.set_x(14)
        pdf.cell(kol[0], 6, p.nazwa, border=1)
        pdf.cell(kol[1], 6, p.ilosc, border=1, align="C")
        for wart, status, szer in ((p.leroy, p.leroy_status, kol[2]),
                                    (p.castorama, p.castorama_status, kol[3]),
                                    (p.arsen, p.arsen_status, kol[4])):
            if wart == "?":
                pdf.set_text_color(150, 150, 150)
                pdf.cell(szer, 6, "brak danych", border=1, align="C")
                pdf.set_text_color(0, 0, 0)
            else:
                pdf.cell(szer, 6, f"{wart} zl ({status})", border=1, align="C")
        pdf.cell(kol[5], 6, p.projekt, border=1, align="C")
        pdf.ln()
        if p.leroy != "?":
            suma_leroy += float(p.leroy)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_x(14)
    pdf.cell(kol[0] + kol[1], 7, "RAZEM", border=1, align="R")
    pdf.cell(kol[2], 7, f"{suma_leroy:.0f} zl", border=1, align="C", fill=True)
    pdf.cell(kol[3], 7, "niepelne", border=1, align="C")
    pdf.cell(kol[4], 7, "nieznane", border=1, align="C")
    pdf.cell(kol[5], 7, "", border=1)
    pdf.ln(12)

    # --- co ustalono o Arsenie ---
    pdf.set_x(14)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Arsen Kalisz - co udalo sie ustalic", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    for linia in (
        "Sklep internetowy arsen.pl (dawniej arsen24.pl) DZIALA i ma ceny, ale w jego",
        "katalogu NIE MA zadnej z potrzebnych pozycji. Sprawdzone dwiema metodami:",
        "przez API sklepu (WooCommerce) i przez wyszukiwarke strony (Selenium).",
        "Zapytania OSB, plyta meblowa, wkrety do drewna, listwa, obrzeze, sklejka,",
        "kantowka - wszystkie zwracaja zero wynikow.",
        "",
        "100 kategorii sklepu to glownie: Malowanie (1472 produkty), Narzedzia (553),",
        "Budowa (543, ale kleje i chemia), Farby, Ogrod, Elektryka.",
        "",
        "TO NIE ZNACZY, ze sklep stacjonarny ich nie ma. Arsen opisuje sie jako",
        "hurtownia budowlana i siec sklepow, a witryna internetowa czesto pokazuje",
        "tylko czesc asortymentu. Tego nie rozstrzygnie research - tylko telefon.",
    ):
        pdf.set_x(14)
        pdf.cell(0, 4.6, linia, new_x="LMARGIN", new_y="NEXT")

    # --- pytania ---
    pdf.ln(3)
    pdf.set_x(14)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Pytania do zadania w sklepie", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    for i, linia in enumerate((
        "Czy tniecie plyte na wymiar? Jesli tak - ile kosztuje ciecie i czy jest limit sztuk?",
        "Czy macie plyte wiorowa laminowana BIALA 18 mm i w jakim formacie?",
        "Czy mozna zamowic dociecie na konkretny wymiar (6 formatek 755 x 450 mm)?",
        "Czy oklejacie obrzezem ciete krawedzie, czy trzeba kupic rolke i zrobic samemu?",
        "Czy macie OSB-3 18 mm w arkuszu 250 x 125 cm i po ile?",
        "Czy sa listwy sosnowe 20 x 30 mm i wkrety do drewna 4x35 oraz 3,5x30 ocynkowane?",
    ), 1):
        pdf.set_x(14)
        pdf.cell(6, 4.8, f"{i}.")
        pdf.cell(0, 4.8, linia, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)
    pdf.set_x(14)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 4.6, "Ceny oznaczone 'potw.' sprawdzone w sklepie internetowym. 'szac.' to moje "
                      "oszacowanie - zweryfikuj przy kasie.", new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(sciezka))
    return sciezka


if __name__ == "__main__":
    cel = Path(__file__).resolve().parent / "warsztat" / "zestawienie-kosztow.pdf"
    cel.parent.mkdir(exist_ok=True)
    print("Zapisano:", buduj(cel))
