"""
Generowanie PDF-ów do wydruku:

  * build_shelf_labels_pdf()      - etykiety regałów: jedna strona na regał, z listą
    przypisanych łożysk. Do przyklejenia na regale, żeby od razu było widać co gdzie leży.
  * build_bearing_qr_labels_pdf() - arkusz małych naklejek z kodem QR na każde łożysko.
    Kod QR koduje po prostu symbol łożyska (np. "6008") - appka Android po zeskanowaniu
    otwiera okno dodawania z wpisanym symbolem i dociągniętymi wymiarami
    (patrz android-offline/.../BarcodeScanner.kt).
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import segno
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


# ------------------------------------------------- naklejki QR na łożyska ----

# Siatka naklejek na A4 pionowo (210 x 297 mm).
QR_MARGIN = 10.0          # margines strony [mm]
QR_COLS = 3
QR_ROWS = 8
QR_CELL_W = (210.0 - 2 * QR_MARGIN) / QR_COLS   # ~63.3 mm
QR_CELL_H = (297.0 - 2 * QR_MARGIN) / QR_ROWS   # ~34.6 mm
QR_PAD = 2.5              # wewnętrzny odstęp naklejki [mm]
QR_SIZE = 24.0            # bok kodu QR [mm] - reszta szerokości zostaje na opis


def _qr_png(data: str) -> io.BytesIO:
    """Kod QR jako PNG w pamięci. Korekcja błędów 'M' - naklejka na regale może się
    trochę zabrudzić/przetrzeć, a wciąż da się ją odczytać.

    UWAGA: celowo make_qr(), nie make(). To drugie dla krótkich tekstów (a symbol
    łożyska jest krótki) tworzy kod *Micro QR*, którego większość skanerów - w tym
    ML Kit w naszej appce Android - w ogóle nie czyta.

    border=2 to biały margines ("quiet zone") wokół kodu; bez niego skanery mają
    problem z odczytem naklejki wyciętej równo przy krawędzi kodu.
    """
    buf = io.BytesIO()
    segno.make_qr(data, error="m").save(buf, kind="png", scale=8, border=2)
    buf.seek(0)
    return buf


def build_bearing_qr_labels_pdf() -> bytes:
    """Arkusz naklejek: kod QR (symbol łożyska) + symbol, wymiary i regał obok."""
    shelves = {s.id: s for s in db.get_shelves()}
    bearings = sorted(db.get_bearings(), key=lambda b: b.symbol)

    pdf = FPDF(orientation="P", format="A4")
    pdf.add_font("DejaVu", "", str(FONT_DIR / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(FONT_DIR / "DejaVuSans-Bold.ttf"))
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(QR_MARGIN, QR_MARGIN, QR_MARGIN)

    if not bearings:
        pdf.add_page()
        pdf.set_font("DejaVu", "", 13)
        pdf.set_text_color(140, 140, 140)
        pdf.cell(0, 10, "Brak łożysk w magazynie - nie ma czego oznaczać.")
        return bytes(pdf.output())

    per_page = QR_COLS * QR_ROWS
    for index, bearing in enumerate(bearings):
        if index % per_page == 0:
            pdf.add_page()
        slot = index % per_page
        x = QR_MARGIN + (slot % QR_COLS) * QR_CELL_W
        y = QR_MARGIN + (slot // QR_COLS) * QR_CELL_H

        # Ramka do wycinania nożyczkami.
        pdf.set_draw_color(200, 205, 210)
        pdf.set_line_width(0.2)
        pdf.rect(x, y, QR_CELL_W, QR_CELL_H)

        pdf.image(
            _qr_png(bearing.symbol),
            x=x + QR_PAD, y=y + (QR_CELL_H - QR_SIZE) / 2, w=QR_SIZE, h=QR_SIZE,
        )

        text_x = x + QR_PAD * 2 + QR_SIZE
        text_w = QR_CELL_W - (text_x - x) - QR_PAD

        pdf.set_xy(text_x, y + QR_PAD + 1)
        pdf.set_font("DejaVu", "B", 12)
        pdf.set_text_color(20, 30, 40)
        pdf.cell(text_w, 6, bearing.symbol, new_x="LMARGIN", new_y="NEXT")

        pdf.set_xy(text_x, pdf.get_y())
        pdf.set_font("DejaVu", "", 8)
        pdf.set_text_color(70, 80, 90)
        dims = f"{_fmt(bearing.d)} x {_fmt(bearing.D)} x {_fmt(bearing.B)} mm"
        pdf.cell(text_w, 4.5, dims, new_x="LMARGIN", new_y="NEXT")

        shelf = shelves.get(bearing.regal_id)
        pdf.set_xy(text_x, pdf.get_y())
        pdf.set_text_color(120, 130, 140)
        pdf.cell(text_w, 4.5, shelf.nazwa if shelf else "bez regału", new_x="LMARGIN", new_y="NEXT")

        if bearing.typ:
            pdf.set_xy(text_x, pdf.get_y())
            pdf.set_font("DejaVu", "", 7)
            pdf.cell(text_w, 4, bearing.typ[:28], new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


# ------------------------------------------------ naklejki na skrytki --------

# Arkusz A4 pionowo. Naklejki leżą w takim układzie, w jakim stoją w regale:
# dwie kolumny (lewa/prawa skrytka) i jeden rząd na półkę, górna półka u góry
# kartki. Dzięki temu po rozcięciu nie trzeba ich sortować - każda jest już na
# swoim miejscu.
BIN_MARGIN = 10.0
BIN_HEADER_H = 18.0
BIN_COLS = 2
BIN_CELL_W = (210.0 - 2 * BIN_MARGIN) / BIN_COLS   # 95 mm
BIN_ROW_H = 28.5
BIN_PAD = 3.0


def _zakres_opis(shelf: db.Shelf) -> str:
    """Zakres średnicy zewnętrznej słowami, tak jak ma stać na naklejce."""
    if shelf.d_min is None and shelf.d_max is None:
        return "bez zakresu średnicy"
    if shelf.d_max is None:
        return f"D od {shelf.d_min:g} mm w górę"
    if not shelf.d_min:
        return f"D do {shelf.d_max:g} mm"
    return f"D {shelf.d_min:g} – {shelf.d_max:g} mm"


def _typy_opis(typy: str) -> str:
    """Lista typów skrócona tak, żeby zmieściła się na naklejce.

    Nazwy typów w bazie są pełnymi zdaniami ("wstawkowe (UC)", "wstawkowe (ES)"),
    więc wypisane po przecinku nie mieszczą się w komórce. Gdy wszystkie dzielą tę
    samą część przed nawiasem, wyciągamy ją raz przed dwukropek.
    """
    lista = [t.strip() for t in typy.split(",") if t.strip()]
    if not lista:
        return "wszystkie typy"
    rozbite = [re.match(r"^(.*?)\s*\((.*)\)$", t) for t in lista]
    if len(lista) > 1 and all(rozbite) and len({m.group(1) for m in rozbite}) == 1:
        return f"{rozbite[0].group(1)}: " + " · ".join(m.group(2) for m in rozbite)
    return " · ".join(lista)


def _skroc(pdf: FPDF, tekst: str, szerokosc_mm: float) -> str:
    """Ucina tekst do szerokości komórki, żeby nigdy nie wyszedł poza ramkę naklejki."""
    if pdf.get_string_width(tekst) <= szerokosc_mm:
        return tekst
    while tekst and pdf.get_string_width(tekst + "…") > szerokosc_mm:
        tekst = tekst[:-1]
    return tekst + "…"


def build_bin_labels_pdf() -> bytes:
    """Arkusz naklejek na skrytki: kod skrytki, zakres średnicy i przeznaczenie."""
    wezly = {s.id: s for s in db.get_shelves()}
    skrytki = [s for s in wezly.values() if s.poziom_typ == "skrytka"]

    # Grupowanie po półce; półki od najwyższej do najniższej, żeby arkusz był mapą regału.
    polki: dict[str | None, list[db.Shelf]] = {}
    for s in skrytki:
        polki.setdefault(s.parent_id, []).append(s)
    kolejnosc = sorted(polki, key=lambda pid: -(wezly[pid].poziom if pid in wezly else 0))

    pdf = FPDF(orientation="P", format="A4")
    pdf.add_font("DejaVu", "", str(FONT_DIR / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(FONT_DIR / "DejaVuSans-Bold.ttf"))
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(BIN_MARGIN, BIN_MARGIN, BIN_MARGIN)
    pdf.add_page()

    if not skrytki:
        pdf.set_font("DejaVu", "", 13)
        pdf.set_text_color(140, 140, 140)
        pdf.cell(0, 10, "Brak skrytek w bazie - nie ma czego oznaczać.")
        return bytes(pdf.output())

    pdf.set_font("DejaVu", "B", 15)
    pdf.set_text_color(20, 30, 40)
    pdf.cell(0, 8, "Naklejki na skrytki", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(120, 130, 140)
    pdf.cell(0, 5, "Układ jak w regale: górna półka u góry kartki, kolumny to lewa i prawa "
                    "skrytka. Rozetnij po ramkach.", new_x="LMARGIN", new_y="NEXT")

    y = BIN_MARGIN + BIN_HEADER_H
    for pid in kolejnosc:
        grupa = sorted(polki[pid], key=lambda s: s.nazwa)
        # Półka z inną liczbą skrytek niż dwie i tak się rozłoży - po dwie w rzędzie.
        for start in range(0, len(grupa), BIN_COLS):
            if y + BIN_ROW_H > 297.0 - BIN_MARGIN:
                pdf.add_page()
                y = BIN_MARGIN
            for kol, s in enumerate(grupa[start:start + BIN_COLS]):
                x = BIN_MARGIN + kol * BIN_CELL_W
                pdf.set_draw_color(150, 158, 166)
                pdf.set_line_width(0.25)
                pdf.rect(x, y, BIN_CELL_W, BIN_ROW_H)

                pdf.set_xy(x + BIN_PAD, y + BIN_PAD)
                pdf.set_font("DejaVu", "B", 20)
                pdf.set_text_color(20, 30, 40)
                pdf.cell(22, 10, s.nazwa)

                pdf.set_xy(x + BIN_PAD + 22, y + BIN_PAD + 1)
                pdf.set_font("DejaVu", "B", 10)
                pdf.set_text_color(40, 55, 70)
                pdf.cell(BIN_CELL_W - 22 - 2 * BIN_PAD, 5, _zakres_opis(s))

                pdf.set_xy(x + BIN_PAD + 22, y + BIN_PAD + 6)
                pdf.set_font("DejaVu", "", 8)
                pdf.set_text_color(110, 120, 130)
                opis_w = BIN_CELL_W - 22 - 2 * BIN_PAD
                pdf.cell(opis_w, 4.5, _skroc(pdf, _typy_opis(s.typy), opis_w))

                rodzic = wezly.get(s.parent_id)
                pdf.set_xy(x + BIN_PAD, y + BIN_ROW_H - BIN_PAD - 4.5)
                pdf.set_font("DejaVu", "", 8)
                pdf.set_text_color(140, 148, 156)
                pdf.cell(BIN_CELL_W - 2 * BIN_PAD, 4.5, rodzic.nazwa if rodzic else "")
            y += BIN_ROW_H

    return bytes(pdf.output())
