"""Zapytanie ofertowe do sklepu — PDF gotowy do wysłania.

Świadomie ZAPYTANIE, nie zamówienie: research wykazał, że sklep internetowy Arsena
nie ma tych pozycji w katalogu, a sklepu stacjonarnego nie sprawdzimy zza biurka.
Zamówienie na towar, którego sklep może nie prowadzić, to zła forma i strata czasu
obu stron. Dokument jest tak ułożony, żeby sprzedawca mógł go wypełnić i odesłać.
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

SKLEP = "Arsen, Kalisz, ul. Dobrzecka"
ZAMAWIAJACY = "Dominik Maslak"
KONTAKT = "dominikmaslak11@gmail.com"

POZYCJE = [
    # (lp, opis, ilosc, uwagi)
    ("1", "Plyta OSB-3, grubosc 18 mm, arkusz 2500 x 1250 mm", "1 szt.",
     "dowolny producent"),
    ("2", "Plyta wiorowa laminowana BIALA, grubosc 18 mm", "2,04 m2",
     "DOCIECIE NA WYMIAR (patrz nizej)"),
    ("3", "Listwa sosnowa 20 x 30 mm, dlugosc 2,7 m", "4 szt.",
     "lub kantowka 20x30 / 30x40"),
    ("4", "Wkrety do drewna 4 x 35 mm, ocynkowane", "100 szt.",
     "NIE nierdzewne"),
    ("5", "Wkrety do drewna 3,5 x 30 mm, ocynkowane", "100 szt.",
     "NIE nierdzewne"),
    ("6", "Podporki do polek, kolek 5 mm, metalowe", "24 szt.", ""),
    ("7", "Obrzeze melaminowe biale 18-19 mm z klejem, rolka 5 m", "2 szt.",
     "do krawedzi plyty bialej"),
]

FORMATKI = [
    ("plyta laminowana biala 18 mm", "755 x 450 mm", "6 szt.",
     "1 dluzszy bok (755 mm)"),
]


class Zapytanie(FPDF):
    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 4, "Zapytanie wygenerowane z aplikacji Magazyn Lozysk", align="C",
                   new_x="LMARGIN", new_y="NEXT")
        self.set_x(0)
        self.cell(0, 4, f"strona {self.page_no()}", align="C")


def buduj(sciezka: Path) -> Path:
    pdf = Zapytanie(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 9, "ZAPYTANIE OFERTOWE", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "materialy na polki - dwa projekty", align="C",
              new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 9.5)
    for etykieta, wartosc in (("Do:", SKLEP), ("Od:", ZAMAWIAJACY),
                               ("Kontakt:", KONTAKT), ("Data:", "2026-08-21")):
        pdf.set_x(18)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.cell(22, 5.5, etykieta)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.cell(0, 5.5, wartosc, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_x(18)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(174, 4.8,
        "Prosze o informacje, ktore z ponizszych pozycji macie w sprzedazy, oraz o wycene. "
        "Jesli czegos nie prowadzicie - prosze o zaznaczenie, wezme to gdzie indziej. "
        "Najwazniejsze pytanie dotyczy pozycji 2: czy tniecie plyte na wymiar i ile to kosztuje.")
    pdf.ln(4)

    # --- tabela pozycji ---
    kol = (10, 92, 22, 50)
    pdf.set_x(18)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(228, 228, 228)
    for tekst, szer in zip(("Lp.", "Pozycja", "Ilosc", "Uwagi"), kol):
        pdf.cell(szer, 7, tekst, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for lp, opis, ilosc, uwagi in POZYCJE:
        pdf.set_x(18)
        pdf.cell(kol[0], 9, lp, border=1, align="C")
        pdf.cell(kol[1], 9, opis, border=1)
        pdf.cell(kol[2], 9, ilosc, border=1, align="C")
        pdf.cell(kol[3], 9, uwagi, border=1)
        pdf.ln()

    # kolumny do wypełnienia przez sklep
    pdf.ln(3)
    pdf.set_x(18)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 4.5, "Do wypelnienia przez sklep: dostepnosc (tak/nie), cena jednostkowa, "
                      "termin.", new_x="LMARGIN", new_y="NEXT")

    # --- specyfikacja dociecia ---
    pdf.ln(6)
    pdf.set_x(18)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Pozycja 2 - specyfikacja dociecia", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    kol2 = (78, 34, 20, 42)
    pdf.set_x(18)
    pdf.set_font("Helvetica", "B", 8.5)
    for tekst, szer in zip(("Material", "Wymiar formatki", "Ilosc", "Obrzeze"), kol2):
        pdf.cell(szer, 7, tekst, border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for mat, wym, ile, obrz in FORMATKI:
        pdf.set_x(18)
        pdf.cell(kol2[0], 9, mat, border=1)
        pdf.cell(kol2[1], 9, wym, border=1, align="C")
        pdf.cell(kol2[2], 9, ile, border=1, align="C")
        pdf.cell(kol2[3], 9, obrz, border=1)
        pdf.ln()

    pdf.ln(3)
    pdf.set_x(18)
    pdf.set_font("Helvetica", "", 8.5)
    for linia in (
        "Formatki sa na polki do szafy o szerokosci wewnetrznej 760 mm -",
        "wymiar 755 mm uwzglednia juz 5 mm luzu na wsuniecie.",
        "Glebokosc 450 mm zamiast pelnych 470 mm, zeby zostal zapas na zawiasy.",
        "Laczna powierzchnia: 2,04 m2.",
    ):
        pdf.set_x(18)
        pdf.cell(0, 4.6, linia, new_x="LMARGIN", new_y="NEXT")

    # --- pytania ---
    pdf.ln(6)
    pdf.set_x(18)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Pytania", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for i, linia in enumerate((
        "Czy tniecie plyte na wymiar? Ile kosztuje jedno ciecie i czy jest limit sztuk?",
        "Czy okleicie ciete krawedzie obrzezem, czy mam kupic rolke i zrobic samemu?",
        "W jakim formacie macie plyte laminowana biala 18 mm?",
        "Czy OSB-3 18 mm jest w arkuszu 2500 x 1250 mm i w jakiej cenie?",
        "Jaki termin realizacji dociecia?",
    ), 1):
        pdf.set_x(18)
        pdf.cell(6, 5.5, f"{i}.")
        pdf.multi_cell(168, 5.5, linia)

    pdf.ln(8)
    pdf.set_x(18)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(174, 5,
        "Jesli czesc pozycji odpada, prosze o wycene reszty - i tak wole kupic na miejscu "
        "niz jechac do marketu sieciowego.")

    pdf.output(str(sciezka))
    return sciezka


if __name__ == "__main__":
    cel = Path(__file__).resolve().parent / "warsztat" / "zapytanie-arsen.pdf"
    cel.parent.mkdir(exist_ok=True)
    print("Zapisano:", buduj(cel))
