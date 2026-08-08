"""
Generowanie PDF-a z etykietami regałów - jedna strona na regał, z listą przypisanych
łożysk. Do wydruku i przyklejenia na regale, żeby od razu było widać co gdzie leży.
"""
from __future__ import annotations

import io
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

import database as db

FONT_DIR = Path(__file__).parent / "fonts"

# Wagi względne szerokości kolumn (fpdf2 rozkłada je proporcjonalnie na szerokość strony).
COLUMNS = [
    ("Symbol", 20), ("Typ", 24), ("d [mm]", 11), ("D [mm]", 11),
    ("B [mm]", 11), ("Ilość", 9), ("Uwagi", 34),
]


def _fmt(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:g}"


class ShelfLabelsPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Magazyn Łożysk - strona {self.page_no()}", align="C")


def build_shelf_labels_pdf() -> bytes:
    shelves = db.get_shelves()  # poziom malejąco: dół -> góra
    bearings_by_shelf: dict[int, list[db.Bearing]] = {s.id: [] for s in shelves}
    for b in db.get_bearings():
        if b.regal_id in bearings_by_shelf:
            bearings_by_shelf[b.regal_id].append(b)
    for lst in bearings_by_shelf.values():
        lst.sort(key=lambda b: b.symbol)

    pdf = ShelfLabelsPDF(orientation="L", format="A4")
    pdf.add_font("DejaVu", "", str(FONT_DIR / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(FONT_DIR / "DejaVuSans-Bold.ttf"))
    pdf.set_auto_page_break(auto=True, margin=18)

    for shelf in shelves:
        pdf.add_page()

        lo = "0" if shelf.d_min is None else f"{shelf.d_min:g}"
        hi = "bez limitu" if shelf.d_max is None else f"{shelf.d_max:g}"

        pdf.set_font("DejaVu", "B", 22)
        pdf.set_text_color(20, 30, 40)
        pdf.cell(0, 12, shelf.nazwa, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("DejaVu", "", 12)
        pdf.set_text_color(90, 100, 110)
        pdf.cell(0, 8, f"Poziom {shelf.poziom} · Zakres średnicy zewnętrznej D: {lo}-{hi} mm",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        rows = bearings_by_shelf.get(shelf.id, [])
        if not rows:
            pdf.set_font("DejaVu", "", 13)
            pdf.set_text_color(140, 140, 140)
            pdf.cell(0, 10, "Brak łożysk przypisanych do tego regału.")
            continue

        pdf.set_text_color(0, 0, 0)
        with pdf.table(
            col_widths=tuple(w for _, w in COLUMNS),
            text_align=("LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "LEFT"),
            headings_style=FontFace(family="DejaVu", emphasis="BOLD", fill_color=(230, 236, 242)),
            line_height=7,
        ) as table:
            header_row = table.row()
            for label, _ in COLUMNS:
                header_row.cell(label)
            for b in rows:
                row = table.row()
                row.cell(b.symbol)
                row.cell(b.typ or "")
                row.cell(_fmt(b.d))
                row.cell(_fmt(b.D))
                row.cell(_fmt(b.B))
                row.cell(str(b.ilosc))
                row.cell(b.uwagi or "")

    return bytes(pdf.output())
