"""Plan cięcia dla taty: dwa arkusze OSB 11 mm, wyrzynarka, rzaz 2 mm.

Po co osobny generator, skoro jest plan_ciecia_pdf.py: tamten powstał pod płytę
18 mm ciętą piłą panelową w markecie i połowa jego stron to wyceny cięcia oraz
zapytania do sklepu. Po decyzji z 25.08.2026 (kupione 2 x OSB 11 mm, tnie tata
wyrzynarką) tamte założenia są nieaktualne, a mieszanie ich z nowymi dałoby
kartkę, przy której trzeba się zastanawiać, co jeszcze obowiązuje. Przy warsztacie
nie ma na to miejsca.

Rysunek jest w skali i uwzględnia rzaz, bo to nie szczegół: pięć półek po 495 mm
plus cztery rzazy to 2483 mm z 2500 - zapas wynosi 17 mm na cały arkusz.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from fpdf import FPDF

# --- Muszą się zgadzać z model_regalu.py i model_szafy.py ---
ARKUSZ = (2500.0, 1250.0)
RZAZ = 2.0                 # ząb wyrzynarki taty, zmierzony

POLKA_REGAL = (855.0, 495.0)
POLKA_GORNA = (855.0, 391.0)   # płytsza, bo wychodzi z pasa odpadowego
PRZEGRODA = (495.0, 192.0)     # komora przy półkach 11 mm (przy 18 mm było 187)
POLKA_SZAFA = (755.0, 450.0)
LISTWA_REGAL = (495.0, 30.0)   # 12 szt., podpory boczne pod półki regału
LISTWA_SZAFA = (450.0, 20.0)   # 12 szt., podpory boczne pod półki szafy
PASEK = (755.0, 40.0)          # usztywnienie pod przednią krawędzią półki szafy
# 40 mm, nie 60: rachunek ugięcia daje minimum 27 mm, a 40 mm zostawia zapas
# (1,69 mm przy granicy 3,77). Węższy pasek = mniej materiału na paski
# i większy odpad w jednym kawałku.

KOMORA_REGAL = 192.0
KOMORA_SZAFA = 292.0

# Stara deska z blatu biurka - laminowana wiórowa, GRUBSZA niż OSB.
# Idzie wyłącznie do regału: Dominik dopuszcza tam 20 mm i więcej, ale w szafie
# na ubrania wszystko ma być z 11 mm OSB, żeby wyglądało jednolicie.
DESKA = (1240.0, 520.0)
DESKA_GRUB = 20.0
LISTWA_DESKA = (495.0, 23.0)   # z paska po zwężeniu 520 -> 495


@dataclass
class Kawalek:
    x: float
    y: float
    dl: float
    szer: float
    etykieta: str
    kolor: tuple[int, int, int]


OSB = (222, 196, 145)
PRZEG = (170, 195, 225)
PASKI = (200, 215, 180)
LISTWY = (215, 195, 225)
DESKA_KOLOR = (196, 164, 132)


def uklad_regalu() -> list[Kawalek]:
    """Arkusz 1. Pięć półek bokiem 495 wzdłuż arkusza - tak mieści się ich pięć,
    a nie cztery. Z pozostałego pasa 393 mm idzie półka górna i przegrody."""
    k: list[Kawalek] = []
    for i in range(5):
        x = i * (POLKA_REGAL[1] + RZAZ)
        k.append(Kawalek(x, 0, POLKA_REGAL[1], POLKA_REGAL[0], f"półka {i+1}\n855x495", OSB))
    y2 = POLKA_REGAL[0] + RZAZ
    k.append(Kawalek(0, y2, POLKA_GORNA[0], POLKA_GORNA[1], "półka górna\n855x391", OSB))
    x0 = POLKA_GORNA[0] + RZAZ
    n = 0
    for kol in range(3):
        for wier in range(2):
            x = x0 + kol * (PRZEGRODA[0] + RZAZ)
            y = y2 + wier * (PRZEGRODA[1] + RZAZ)
            n += 1
            k.append(Kawalek(x, y, PRZEGRODA[0], PRZEGRODA[1], f"przegroda {n}\n495x192", PRZEG))
    return k


def uklad_szafy() -> list[Kawalek]:
    """Arkusz 2, układ dobrany tak, żeby ODPAD ZOSTAŁ JEDNYM PROSTOKĄTEM.

    Poprzednia wersja kładła półki 3 x 2 i paski pod spodem - odpad rozpadał się
    wtedy na wąski pas 2500 x 260 i skrawek z boku. Tutaj pięć półek idzie
    obróconych w górnym pasie, paski chowają się PIONOWO w skrawku z prawej,
    którego i tak nie da się użyć na nic innego, a szósta półka i ostatni pasek
    schodzą do lewej kolumny.

    Efekt: 1740 x 490 mm wolnego w jednym kawałku (0,85 m2) zamiast paska.
    To materiał na dwie kolejne półki, a nie na podpałkę. Sprawdzone programem
    liczącym największy pusty prostokąt - patrz pakowanie.py w notatkach sesji.
    """
    k: list[Kawalek] = []
    for i in range(5):                                   # 5 półek obróconych
        k.append(Kawalek(i * (POLKA_SZAFA[1] + RZAZ), 0,
                         POLKA_SZAFA[1], POLKA_SZAFA[0], f"półka {i+1}\n450x755", OSB))
    x_skrawek = 5 * (POLKA_SZAFA[1] + RZAZ)
    for i in range(5):                                   # paski pionowo w skrawku
        k.append(Kawalek(x_skrawek + i * (PASEK[1] + RZAZ), 0,
                         PASEK[1], PASEK[0], "", PASKI))
    y2 = POLKA_SZAFA[0] + RZAZ
    k.append(Kawalek(0, y2, *POLKA_SZAFA, "półka 6\n755x450", OSB))
    k.append(Kawalek(0, y2 + POLKA_SZAFA[1] + RZAZ, *PASEK, "pasek 6", PASKI))

    # Listwy nośne z tego samego arkusza (decyzja 26.08) - zamiast kupowania
    # sosny. Kosztuje to kawałek dużego odpadu: zostaje 1743 x 277 zamiast
    # 1743 x 493, czyli już nie wyjdzie z niego półka. Świadomy wybór.
    x0 = POLKA_SZAFA[0] + RZAZ
    for wiersz in range(4):
        for kol in range(3):
            k.append(Kawalek(x0 + kol * (LISTWA_REGAL[0] + RZAZ),
                             y2 + wiersz * (LISTWA_REGAL[1] + RZAZ),
                             *LISTWA_REGAL, "", LISTWY))
    y3 = y2 + 4 * (LISTWA_REGAL[1] + RZAZ)
    for wiersz in range(4):
        for kol in range(3):
            k.append(Kawalek(x0 + kol * (LISTWA_SZAFA[0] + RZAZ),
                             y3 + wiersz * (LISTWA_SZAFA[1] + RZAZ),
                             *LISTWA_SZAFA, "", LISTWY))
    return k


# ------------------------------------------------------------------- PDF ----

def uklad_deski() -> list[Kawalek]:
    """Rozkrój blatu biurka. Trzy cięcia, prawie zero odpadu.

    Sedno: pasek, który odpada przy zwężeniu 520 -> 495 mm, NIE jest odpadem.
    Wychodzą z niego dwie listwy nośne - dokładnie te dwie, których brakowało
    do siódmej półki regału. Bez tego trzeba by dokupić sosnę.
    """
    k: list[Kawalek] = []
    k.append(Kawalek(0, 0, 855.0, 495.0, "PÓŁKA z deski\n855x495\n(grubość 20 mm)", DESKA_KOLOR))
    x = 855.0 + RZAZ
    k.append(Kawalek(x, 0, PRZEGRODA[1], PRZEGRODA[0], "przegroda\n192x495", PRZEG))
    # pasek ze zwężenia - dwie listwy nośne
    y = 495.0 + RZAZ
    for i in range(2):
        k.append(Kawalek(i * (LISTWA_DESKA[0] + RZAZ), y, *LISTWA_DESKA, "", LISTWY))
    return k


def _pdf() -> FPDF:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    fonty = Path(__file__).resolve().parent / "fonts"
    # DejaVu, nie Helvetica: etykiety mają polskie znaki, a Helvetica ich nie koduje.
    pdf.add_font("DejaVu", "", str(fonty / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(fonty / "DejaVuSans-Bold.ttf"))
    pdf.set_auto_page_break(False)
    return pdf


RYS_X, RYS_Y, RYS_SKALA = 12.0, 30.0, 0.106   # arkusz 2500 mm -> 265 mm papieru


def rysuj_arkusz(pdf, kawalki: list[Kawalek], tytul: str, podtytul: str,
                 adnotacje: list[tuple[float, float, str]] | None = None,
                 arkusz: tuple[float, float] = ARKUSZ) -> None:
    pdf.add_page()
    pdf.set_font("DejaVu", "B", 16)
    pdf.set_xy(12, 10)
    pdf.cell(0, 8, tytul)
    pdf.set_font("DejaVu", "", 10)
    pdf.set_xy(12, 19)
    pdf.cell(0, 5, podtytul)

    X0, Y0 = RYS_X, RYS_Y
    SKALA = 265.0 / arkusz[0]        # skala z szerokości - deska jest krótsza od arkusza
    pdf.set_line_width(0.5)
    pdf.set_draw_color(60, 60, 60)
    pdf.rect(X0, Y0, arkusz[0] * SKALA, arkusz[1] * SKALA)

    for k in kawalki:
        x, y = X0 + k.x * SKALA, Y0 + k.y * SKALA
        w, h = k.dl * SKALA, k.szer * SKALA
        pdf.set_fill_color(*k.kolor)
        pdf.set_draw_color(40, 40, 40)
        pdf.set_line_width(0.3)
        pdf.rect(x, y, w, h, style="DF")
        # Etykieta tylko tam, gdzie się mieści - na wąskich paskach zamieniłaby
        # się w plamę i zasłoniła linie cięcia.
        if h >= 7 and w >= 14:
            pdf.set_font("DejaVu", "", 6.5 if h < 12 else 7.5)
            pdf.set_text_color(30, 30, 30)
            linie = k.etykieta.split("\n")
            ty = y + h / 2 - len(linie) * 2.0
            for ln in linie:
                pdf.set_xy(x, ty)
                pdf.cell(w, 4, ln, align="C")
                ty += 3.6
    pdf.set_text_color(0, 0, 0)

    # Opisy w miejscu, którego dotyczą - podane we współrzędnych ARKUSZA,
    # żeby nie trzeba było przeliczać ich ręcznie przy zmianie skali.
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(90, 90, 90)
    for ax, ay, tekst in (adnotacje or []):
        pdf.set_xy(X0 + ax * SKALA, Y0 + ay * SKALA)
        pdf.cell(0, 4, tekst)
    pdf.set_text_color(0, 0, 0)

    # Wymiary arkusza przy krawędziach - żeby nie trzeba było ufać skali.
    pdf.set_font("DejaVu", "", 8)
    pdf.set_xy(X0, Y0 + arkusz[1] * SKALA + 1.5)
    pdf.cell(arkusz[0] * SKALA, 5, f"{arkusz[0]:.0f} mm", align="C")
    pdf.set_xy(X0 + arkusz[0] * SKALA + 2, Y0 + arkusz[1] * SKALA / 2 - 2)
    pdf.cell(20, 4, f"{arkusz[1]:.0f} mm")


def lista(pdf, wiersze: list[tuple[str, str, int]], naglowek: str, y: float) -> None:
    pdf.set_font("DejaVu", "B", 11)
    pdf.set_xy(12, y)
    pdf.cell(0, 6, naglowek)
    y += 8
    pdf.set_font("DejaVu", "", 9.5)
    for nazwa, wymiar, ile in wiersze:
        pdf.set_xy(14, y)
        for i in range(ile):                     # kratka na każdą sztukę
            pdf.rect(14 + i * 5, y + 0.8, 3.6, 3.6)
        pdf.set_xy(14 + ile * 5 + 4, y)
        pdf.cell(0, 5, f"{ile} x  {nazwa}   —   {wymiar}")
        y += 5.5


def strona_zasad(pdf) -> None:
    """Zasady na osobnej stronie, bo to jest to, co realnie decyduje o wyniku.
    Rysunek mówi CO ciąć, ta strona - JAK, żeby wyszło proste i pasowało."""
    pdf.add_page()
    pdf.set_font("DejaVu", "B", 16)
    pdf.set_xy(12, 12)
    pdf.cell(0, 8, "Zanim zaczniesz ciąć")

    blok = [
        ("B", "Wyrzynarka to nie piła panelowa"),
        ("", "Brzeszczot ucieka na długim cięciu. Bez prowadnicy albo przykręconej"),
        ("", "listwy potrafi zejść 3–5 mm z linii — a półka ma wejść między boki."),
        ("", ""),
        ("B", "Dobra strona SPODEM"),
        ("", "OSB wyrywa od góry, przy wyjściu zęba. Ta strona, która ma być widoczna,"),
        ("", "leży do dołu."),
        ("", ""),
        ("B", "Tnij 2–3 mm PONIŻEJ wymiaru"),
        ("", "Za wąską półkę da się podeprzeć listwą. Za szerokiej nie wciśniesz."),
        ("", ""),
        ("B", "Rzaz 2 mm jest już wliczony"),
        ("", "Wymiary na rysunku to gotowe formatki. Tnij po linii, nie obok niej —"),
        ("", "odstępy między kawałkami na rysunku to właśnie miejsce na rzaz."),
        ("", ""),
        ("B", "Przegrody zmierz na miejscu"),
        ("", f"Rachunek daje {KOMORA_REGAL:.0f} mm dla regału i {KOMORA_SZAFA:.0f} mm dla szafy."),
        ("", "Zmierz pierwszą komorę w regale i dopiero wtedy tnij pozostałe siedem."),
        ("", "Przegroda ma być DOCIŚNIĘTA do półki wyżej — luźna niczego nie podpiera."),
        ("", ""),
        ("B", "Nawiercaj przy krawędziach"),
        ("", "Bliżej niż 5 cm od krawędzi wierć 2,5 mm. OSB 11 mm pęka po włóknie."),
    ]
    y = 26.0
    for styl, tekst in blok:
        pdf.set_font("DejaVu", "B" if styl == "B" else "", 11 if styl == "B" else 10)
        pdf.set_xy(14, y)
        pdf.cell(0, 5.5, tekst)
        y += 5.6 if tekst else 2.5

    pdf.set_font("DejaVu", "B", 11)
    pdf.set_xy(150, 26)
    pdf.cell(0, 6, "Łączenie")
    dane = [
        "Paski usztywniające pod półki szafy:",
        "  klej na całej długości + wkręty 4x40 co 15 cm,",
        "  wkręcane Z GÓRY przez półkę w pasek.",
        "",
        "Przegrody w regale:",
        "  kątowniki meblowe, 2 na przegrodę.",
        "  NIE wkręcaj w krawędź płyty 11 mm —",
        "  rozwarstwia się i nie trzyma.",
        "",
        "Kołki i gwoździe: nie w tej grubości.",
    ]
    y = 34.0
    pdf.set_font("DejaVu", "", 10)
    for ln in dane:
        pdf.set_xy(152, y)
        pdf.cell(0, 5.2, ln)
        y += 5.2 if ln else 2.5


def zbuduj(sciezka: Path) -> Path:
    pdf = _pdf()

    rysuj_arkusz(pdf, uklad_regalu(), "Arkusz 1 — REGAŁ NA ŁOŻYSKA",
                 "OSB-3 11 mm, 2500 x 1250 mm, wyrzynarka (rzaz 2 mm)",
                 adnotacje=[(2360, 900, "zapas")])
    lista(pdf, [("półki dolne", "855 x 495 mm", 5),
                ("półka górna", "855 x 391 mm", 1),
                ("przegrody", f"495 x {KOMORA_REGAL:.0f} mm", 6)],
          "Z tego arkusza wychodzi:", 168)
    pdf.set_font("DejaVu", "", 9.5)
    pdf.set_xy(14, 194)
    pdf.cell(0, 5, "+ ze starej deski z biurka: 1 półka 855 x 495 i 2 przegrody  ->  razem 8 przegród")

    rysuj_arkusz(pdf, uklad_szafy(), "Arkusz 2 — SZAFA NA UBRANIA ROBOCZE",
                 "OSB-3 11 mm, 2500 x 1250 mm, wyrzynarka (rzaz 2 mm)",
                 adnotacje=[(830, 1010, "ODPAD 1740 x 277 mm — jeden kawałek, nie tnij"),
                            (830, 1075, "fiolet: 12 listew 495x30 (regał) + 12 listew 450x20 (szafa)"),
                            (830, 1140, "zielone: 6 pasków usztywniających 755 x 40 mm"),
                            (830, 1205, "(pięć w skrawku z prawej, szósty pod półką 6)")])
    lista(pdf, [("półki", "755 x 450 mm", 6),
                ("paski usztywniające", "755 x 40 mm", 6),
                ("listwy nośne do REGAŁU", "495 x 30 mm", 12),
                ("listwy nośne do SZAFY", "450 x 20 mm", 12)],
          "Z tego arkusza wychodzi:", 166)
    pdf.set_font("DejaVu", "", 9.5)
    pdf.set_xy(14, 196)
    pdf.cell(0, 5, "Pasek idzie pod PRZEDNIĄ krawędź półki, na sztorc. Bez niego półka ugnie się 12,6 mm.")
    pdf.set_xy(14, 202)
    pdf.cell(0, 5, "Listwy nośne też z tego arkusza — sosny nie kupujemy. Odpad: 1740 x 277 mm.")

    rysuj_arkusz(pdf, uklad_deski(), "Stara DESKA z blatu biurka — do REGAŁU",
                 "laminowana wiórowa 1240 x 520 x 20 mm, wyrzynarka (rzaz 2 mm)",
                 adnotacje=[(1055, 200, "reszta 189 x 495 — zapas"),
                            (1000, 460, "fiolet: 2 listwy 495 x 23 mm"),
                            (1000, 505, "z paska po zwężeniu 520 -> 495")],
                 arkusz=DESKA)
    lista(pdf, [("półka (20 mm, do regału)", "855 x 495 mm", 1),
                ("przegroda", "495 x 192 mm", 1),
                ("listwy nośne (20 mm)", "495 x 23 mm", 2)],
          "Z deski wychodzi:", 158)
    pdf.set_font("DejaVu", "", 9.5)
    pdf.set_xy(14, 182)
    pdf.cell(0, 5, "Kolejność: 1) zwęź całą deskę 520 -> 495 mm  2) odetnij półkę 855  "
                   "3) z reszty jedna przegroda  4) pasek na dwie listwy")
    pdf.set_xy(14, 188)
    pdf.cell(0, 5, "Laminat chroni tylko płaszczyzny — ZABEZPIECZ KRAWĘDZIE po cięciu "
                   "(obrzeże, silikon albo farba).")
    pdf.set_xy(14, 194)
    pdf.cell(0, 5, "Te dwie listwy idą pod SIÓDMĄ (górną) półkę regału. To dokładnie te, "
                   "których brakowało.")

    strona_zasad(pdf)
    pdf.output(str(sciezka))
    return sciezka


if __name__ == "__main__":
    katalog = Path(os.environ.get("LOZYSKA_WYNIKI", Path(__file__).resolve().parent)) / "warsztat"
    katalog.mkdir(parents=True, exist_ok=True)
    print(zbuduj(katalog / "plan-ciecia-11mm.pdf"))
