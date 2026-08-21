"""Czy ten odpad w markecie się opłaca? — szybka wycena przy półce w sklepie.

Sytuacja, dla której to powstało: stoisz w Leroy przy koszu ze zrzynkami, widzisz
kawałek OSB z ceną i masz kilkanaście sekund na decyzję. Pytanie nie brzmi „ile
to kosztuje", tylko **ile kosztuje JEDNA PÓŁKA z tego kawałka** w porównaniu
z pełnym arkuszem za 104 zł.

    python zrzynki.py 1200x600 25              # ciecie zlecone, 3 zl za ciecie
    python zrzynki.py 1200x600 25 --express    # ten sam dzien, 6 zl za ciecie
    python zrzynki.py 1200x600 25 --bez-ciecia # tniesz sam
    python zrzynki.py 1200x600 25 --pdf --mail

Odpad, z którego nie wyjdzie ani jedna półka, nie jest bezwartościowy — przegrody
też są potrzebne, a na nie starczą małe kawałki. Dlatego liczymy jedno i drugie.

Koszt docinania jest doliczany PO OBU STRONACH porównania — do odpadu i do pełnego
arkusza. Bez tego rachunek kłamie na korzyść odpadów: mały kawałek daje mało półek,
ale cięć wymaga prawie tyle samo co duży.

Liczby biorą się z tego samego miejsca co plan cięcia (stolarz.py): rzaz 4 mm,
półka 855 x 495 mm, przegroda 495 x 187 mm, cięcie 3 zł (6 zł express).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from stolarz import OSB_18, Material, Polka, rozkroj

# Formatki z planu Regału 2 — patrz plan_ciecia_pdf.py.
POLKA = Polka(855.0, 495.0)
PRZEGRODA = Polka(495.0, 187.0)

# Cennik docinania w Leroy Kalisz, potwierdzony telefonicznie 2026-08-21.
CIECIE_ZWYKLE = 3.0    # termin 2-3 dni
CIECIE_EXPRESS = 6.0   # ten sam dzien

# Resztka mniejsza niż to nie wymaga osobnego cięcia - mieści się w obrzynie
# krawędzi arkusza.
RESZTKA_BEZ_CIECIA_MM = 20.0

# Poniżej tylu procent ceny odniesienia mówimy "bierz". Powyżej 100% - "nie".
# Między 85% a 100% oszczędność jest realna, ale niewielka, więc zwracamy uwagę,
# że dochodzi kłopot z przewiezieniem i docięciem osobnego kawałka.
PROG_OKAZJA = 0.85

# Mniej niż tyle przegród to nie jest powód, żeby wozić do domu osobny kawałek.
MIN_PRZEGROD = 2


def liczba_ciec(plyta_dl: float, plyta_szer: float,
                 formatka_dl: float, formatka_szer: float) -> tuple[int, int]:
    """Ile prostych cięć, żeby wyjąć z płyty jak najwięcej takich formatek.

    Model gilotynowy, bo tak tnie piła panelowa w markecie: najpierw płyta idzie
    na pasy, potem każdy pas na formatki. Cięcia w poprzek pasa nie da się zrobić
    inaczej - stąd mnożenie przez liczbę pasów.

    Zwraca (liczba_ciec, liczba_formatek). Sprawdza obie orientacje i wybiera tę,
    która daje więcej formatek; przy remisie tę tańszą w cięciach.
    """
    def wariant(dl_f, szer_f):
        wzdluz = int((plyta_dl + RZAZ) // (dl_f + RZAZ))
        wszerz = int((plyta_szer + RZAZ) // (szer_f + RZAZ))
        if wzdluz < 1 or wszerz < 1:
            return 999, 0
        # pasy w poprzek szerokości płyty
        resztka_szer = plyta_szer - wszerz * szer_f - (wszerz - 1) * RZAZ
        ciec_na_pasy = (wszerz - 1) + (1 if resztka_szer > RESZTKA_BEZ_CIECIA_MM else 0)
        # każdy pas rozcinany na formatki wzdłuż długości
        resztka_dl = plyta_dl - wzdluz * dl_f - (wzdluz - 1) * RZAZ
        ciec_w_pasie = (wzdluz - 1) + (1 if resztka_dl > RESZTKA_BEZ_CIECIA_MM else 0)
        return ciec_na_pasy + wszerz * ciec_w_pasie, wzdluz * wszerz

    a = wariant(formatka_dl, formatka_szer)
    b = wariant(formatka_szer, formatka_dl)
    # więcej formatek wygrywa; przy tylu samo - mniej cięć
    return min([a, b], key=lambda w: (-w[1], w[0]))


RZAZ = 4.0


def ukladanie(plyta_dl: float, plyta_szer: float,
              form_dl: float, form_szer: float) -> tuple[float, float]:
    """Jak ułożyć formatkę na płycie, żeby zmieściło się jej najwięcej.

    Zwraca (bok wzdłuż długości płyty, bok wzdłuż szerokości). Jedyne źródło
    prawdy o orientacji - i rysunek, i liczenie muszą z niego korzystać, żeby
    kartka pokazywała to samo, co tabela nad nią.
    """
    def ile(a, b):
        return int((plyta_dl + RZAZ) // (a + RZAZ)) * int((plyta_szer + RZAZ) // (b + RZAZ))

    return ((form_dl, form_szer) if ile(form_dl, form_szer) >= ile(form_szer, form_dl)
            else (form_szer, form_dl))

# Pełny arkusz z docinaniem w sklepie - to jest realny punkt odniesienia teraz,
# gdy cięcie zlecamy. Bez doliczenia cięć porównanie kłamie na korzyść odpadów.
_C_ARK, ODNIESIENIE_SZTUK = liczba_ciec(2500.0, 1250.0, 855.0, 495.0)
CIEC_ARKUSZA = _C_ARK
PRZEGROD_Z_ARKUSZA = rozkroj(OSB_18, PRZEGRODA, 1).sztuk_z_arkusza


def cena_polki_z_arkusza(cena_ciecia: float) -> float:
    return ((OSB_18.cena_arkusza or 0.0) + CIEC_ARKUSZA * cena_ciecia) / max(1, ODNIESIENIE_SZTUK)


def cena_przegrody_z_arkusza(cena_ciecia: float) -> float:
    c, _ = liczba_ciec(2500.0, 1250.0, 495.0, 187.0)
    return ((OSB_18.cena_arkusza or 0.0) + c * cena_ciecia) / max(1, PRZEGROD_Z_ARKUSZA)


@dataclass
class Wycena:
    dlugosc: float
    szerokosc: float
    cena: float
    polek: int
    przegrod: int
    uklad_polek: str
    uklad_przegrod: str
    ciec_polki: int = 0
    ciec_przegrod: int = 0
    cena_ciecia: float = CIECIE_ZWYKLE

    @property
    def pole_m2(self) -> float:
        return self.dlugosc * self.szerokosc / 1e6

    @property
    def koszt_ciecia(self) -> float:
        ile = self.ciec_polki if self.polek else self.ciec_przegrod
        return ile * self.cena_ciecia

    @property
    def koszt_calkowity(self) -> float:
        return self.cena + self.koszt_ciecia

    @property
    def cena_za_polke(self) -> float | None:
        return self.koszt_calkowity / self.polek if self.polek else None

    @property
    def cena_za_m2(self) -> float:
        return self.cena / self.pole_m2 if self.pole_m2 else 0.0

    @property
    def odniesienie(self) -> float:
        """Ile kosztuje półka z pełnego arkusza PRZY TEJ SAMEJ cenie cięcia."""
        return cena_polki_z_arkusza(self.cena_ciecia)

    @property
    def stosunek(self) -> float | None:
        """Cena półki z odpadu / cena półki z pełnego arkusza. Obie z cięciem."""
        c = self.cena_za_polke
        if c is None or not self.odniesienie:
            return None
        return c / self.odniesienie

    @property
    def cena_za_przegrode(self) -> float | None:
        return self.koszt_calkowity / self.przegrod if self.przegrod else None

    @property
    def werdykt(self) -> str:
        if self.polek == 0:
            # Kawałek bez półki nie jest bezwartościowy - przegród potrzeba
            # kilkadziesiąt. Ale oceniamy je tak samo jak półki: po cenie sztuki,
            # a nie po samej liczbie.
            c = self.cena_za_przegrode
            prog = cena_przegrody_z_arkusza(self.cena_ciecia)
            if self.przegrod >= MIN_PRZEGROD and c is not None and c <= prog:
                return "TYLKO NA PRZEGRODY"
            return "NIE"

        s = self.stosunek
        # UWAGA: 's' bywa zerem przy darmowym odpadzie, a zero jest fałszywe.
        # Skrót "s or coś" zamieniał tu najlepszą możliwą okazję w odmowę.
        if s is None:
            return "NIE"
        if s <= PROG_OKAZJA:
            return "BIERZ"
        if s <= 1.0:
            return "NA GRANICY"
        return "NIE"


def wyceniaj(dlugosc: float, szerokosc: float, cena: float,
             cena_ciecia: float = CIECIE_ZWYKLE) -> Wycena:
    # Odpad to po prostu arkusz o innym formacie - dzięki temu liczy to ten sam
    # kod co plan cięcia, razem z rzazem i obiema orientacjami.
    plyta = Material("odpad OSB-3 18 mm", 18.0, OSB_18.E, (dlugosc, szerokosc), cena)
    rp = rozkroj(plyta, POLKA, 1)
    rz = rozkroj(plyta, PRZEGRODA, 1)
    cp, _ = liczba_ciec(dlugosc, szerokosc, POLKA.dlugosc, POLKA.glebokosc)
    cz, _ = liczba_ciec(dlugosc, szerokosc, PRZEGRODA.dlugosc, PRZEGRODA.glebokosc)
    return Wycena(dlugosc, szerokosc, cena, rp.sztuk_z_arkusza, rz.sztuk_z_arkusza,
                  rp.uklad, rz.uklad,
                  ciec_polki=cp if rp.sztuk_z_arkusza else 0,
                  ciec_przegrod=cz if rz.sztuk_z_arkusza else 0,
                  cena_ciecia=cena_ciecia)


def wymiary_z_tekstu(tekst: str) -> tuple[float, float]:
    """Przyjmuje '1200x600', '1200 x 600', '120x60 cm' — bo w sklepie się nie celuje."""
    t = tekst.lower().replace(",", ".").strip()
    cm = "cm" in t
    liczby = re.findall(r"\d+(?:\.\d+)?", t)
    if len(liczby) < 2:
        raise ValueError(f"Nie widzę dwóch wymiarów w '{tekst}'. Podaj np. 1200x600")
    a, b = float(liczby[0]), float(liczby[1])
    if cm:
        a, b = a * 10, b * 10
    # Wymiary poniżej 300 to prawie na pewno centymetry wpisane bez jednostki.
    if max(a, b) < 300:
        a, b = a * 10, b * 10
    return a, b


def raport(w: Wycena) -> str:
    L = [
        f"ODPAD OSB-3 18 mm:  {w.dlugosc:.0f} x {w.szerokosc:.0f} mm "
        f"({w.pole_m2:.2f} m2)   cena {w.cena:.2f} zl   ({w.cena_za_m2:.0f} zl/m2)",
        "",
        f"  polek 855 x 495 mm : {w.polek}" + (f"   ({w.uklad_polek})" if w.polek else ""),
        f"  przegrod 495 x 187 : {w.przegrod}",
        "",
    ]
    if w.polek:
        L += [
            f"  ciec do zlecenia   : {w.ciec_polki} x {w.cena_ciecia:.0f} zl "
            f"= {w.koszt_ciecia:.0f} zl",
            f"  RAZEM              : {w.koszt_calkowity:.2f} zl "
            f"({w.cena:.0f} zl plyta + {w.koszt_ciecia:.0f} zl ciecie)",
            "",
            f"  cena za polke      : {w.cena_za_polke:.2f} zl",
            f"  z pelnego arkusza  : {w.odniesienie:.2f} zl "
            f"({ODNIESIENIE_SZTUK} polek, {OSB_18.cena_arkusza:.0f} zl "
            f"+ {CIEC_ARKUSZA} ciec)",
            f"  stosunek           : {w.stosunek*100:.0f}% ceny z arkusza",
            "",
        ]
    L.append(f"  WERDYKT: {w.werdykt}")

    if w.werdykt == "BIERZ":
        oszcz = (w.odniesienie - w.cena_za_polke) * w.polek
        L.append(f"  Oszczedzasz {oszcz:.0f} zl w porownaniu z pelnym arkuszem.")
    elif w.werdykt == "NA GRANICY":
        L.append("  Taniej, ale nieznacznie. Doliczy sie osobne ciecie i przewiezienie")
        L.append("  drugiego kawalka - przy malej roznicy nie warto.")
    elif w.werdykt == "TYLKO NA PRZEGRODY":
        L.append(f"  Polka sie nie zmiesci, ale wyjdzie {w.przegrod} przegrod po "
                 f"{w.cena_za_przegrode:.2f} zl")
        L.append(f"  (z pelnego arkusza: {cena_przegrody_z_arkusza(w.cena_ciecia):.2f} zl). "
                 f"Przegrody i tak trzeba z czegos zrobic.")
    else:
        if w.polek == 0 and w.przegrod < MIN_PRZEGROD:
            L.append("  Za maly kawalek: ani polka, ani sensowna liczba przegrod.")
        else:
            L.append("  Drozej niz z pelnego arkusza. Odpusc.")
    return "\n".join(L)


def instrukcja_ciecia(w: Wycena) -> list[str]:
    if not w.polek and not w.przegrod:
        return ["Nie ma czego ciac."]
    K = []
    if w.polek:
        K.append(f"1. Odetnij {w.polek} x polka 855 x 495 mm ({w.uklad_polek}).")
        K.append("   Zostaw 4 mm na rzaz miedzy kazda para formatek.")
        K.append("2. Krawedz przednia polki oznacz olowkiem - ta idzie do przodu.")
    if w.przegrod:
        nr = 3 if w.polek else 1
        K.append(f"{nr}. Z reszty: do {w.przegrod} x przegroda 495 x 187 mm.")
        K.append(f"{nr+1}. Przegrody mocujesz wkretami 3,5 x 30 posrodku polki.")
    K.append("Tnij po dluzszym boku jako pierwszym - latwiej prowadzic pilarke.")
    return K


def buduj_pdf(w: Wycena, sciezka: Path) -> Path:
    """Jedna kartka: werdykt, liczby i rysunek rozkroju odpadu.

    Font DejaVu, nie Helvetica: opisy układu pochodzą ze stolarz.py i mają polskie
    znaki, na których wbudowany font fpdf się wywraca (tak samo robi pdf_labels.py).
    """
    from fpdf import FPDF

    fonty = Path(__file__).resolve().parent / "fonts"
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_font("DejaVu", "", str(fonty / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(fonty / "DejaVuSans-Bold.ttf"))
    pdf.set_auto_page_break(False)
    pdf.add_page()

    pdf.set_y(16)
    pdf.set_font("DejaVu", "B", 18)
    pdf.cell(0, 10, "WYCENA ODPADU OSB", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 5, f"{w.dlugosc:.0f} x {w.szerokosc:.0f} mm   |   {w.cena:.2f} zl",
              align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    kolor = {"BIERZ": (200, 235, 200), "NA GRANICY": (250, 240, 200),
             "TYLKO NA PRZEGRODY": (215, 230, 245)}.get(w.werdykt, (245, 220, 220))
    pdf.set_x(18)
    pdf.set_fill_color(*kolor)
    pdf.set_font("DejaVu", "B", 20)
    pdf.cell(174, 14, f"  {w.werdykt}", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("DejaVu", "", 10)
    for etykieta, wartosc in (
        ("Powierzchnia", f"{w.pole_m2:.2f} m2   ({w.cena_za_m2:.0f} zl/m2)"),
        ("Polek 855 x 495", str(w.polek)),
        ("Przegrod 495 x 187", str(w.przegrod)),
        ("Ciec do zlecenia", f"{w.ciec_polki if w.polek else w.ciec_przegrod} x "
                              f"{w.cena_ciecia:.0f} zl = {w.koszt_ciecia:.0f} zl"),
        ("RAZEM z cieciem", f"{w.koszt_calkowity:.2f} zl"),
        ("Cena za polke", f"{w.cena_za_polke:.2f} zl" if w.polek else "-"),
        ("Z pelnego arkusza", f"{w.odniesienie:.2f} zl "
                               f"({ODNIESIENIE_SZTUK} szt., 104 zl + {CIEC_ARKUSZA} ciec)"),
    ):
        pdf.set_x(18)
        pdf.set_font("DejaVu", "B", 10)
        pdf.cell(52, 6, etykieta)
        pdf.set_font("DejaVu", "", 10)
        pdf.cell(0, 6, wartosc, new_x="LMARGIN", new_y="NEXT")

    # --- rysunek rozkroju ---
    pdf.ln(8)
    pdf.set_x(18)
    pdf.set_font("DejaVu", "B", 12)
    pdf.cell(0, 7, "Rozkroj", new_x="LMARGIN", new_y="NEXT")

    dostepne = 174.0
    skala = min(dostepne / w.dlugosc, 90.0 / w.szerokosc)
    x0, y0 = 18.0, pdf.get_y() + 4
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.5)
    pdf.set_fill_color(252, 250, 245)
    pdf.rect(x0, y0, w.dlugosc * skala, w.szerokosc * skala, style="FD")

    if w.polek:
        # Rysujemy tylko ten układ, który dał więcej sztuk - żeby kartka pokazywała
        # to, co realnie masz zrobić, a nie obie możliwości naraz.
        #
        # Orientację liczymy z wymiarów, a NIE z opisu tekstowego. Opis ze stolarz.py
        # jest dla człowieka ("formatka obrócona o 90 stopni") i sprawdzanie w nim
        # podłańcucha już raz zawiodło przez polski znak - rysunek pokazywał wtedy
        # 2 półki zamiast 3.
        fd, fs = ukladanie(w.dlugosc, w.szerokosc, POLKA.dlugosc, POLKA.glebokosc)
        pdf.set_fill_color(205, 232, 205)
        pdf.set_line_width(0.3)
        n = 0
        y = y0
        while y + fs * skala <= y0 + w.szerokosc * skala + 0.1 and n < w.polek:
            x = x0
            while x + fd * skala <= x0 + w.dlugosc * skala + 0.1 and n < w.polek:
                pdf.rect(x, y, fd * skala, fs * skala, style="FD")
                pdf.set_font("DejaVu", "B", 7)
                pdf.set_xy(x, y + fs * skala / 2 - 2)
                pdf.cell(fd * skala, 4, f"POLKA {n+1}", align="C")
                x += (fd + 4.0) * skala
                n += 1
            y += (fs + 4.0) * skala

    pdf.set_y(y0 + w.szerokosc * skala + 6)
    pdf.set_x(18)
    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 6, "Jak ciac", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9.5)
    for linia in instrukcja_ciecia(w):
        pdf.set_x(18)
        pdf.cell(0, 5.2, linia, new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(-16)
    pdf.set_font("DejaVu", "", 8)
    pdf.cell(0, 4, "Wygenerowane przez zrzynki.py  |  rzaz 4 mm, polka 855 x 495 mm",
              align="C")

    sciezka.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(sciezka))
    return sciezka


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Czy odpad OSB w markecie sie oplaca - wycena przy polce w sklepie.")
    p.add_argument("wymiary", help="np. 1200x600 (mm) albo '120x60 cm'")
    p.add_argument("cena", type=float, help="cena odpadu w zlotych")
    p.add_argument("--express", action="store_true",
                   help=f"ciecie tego samego dnia ({CIECIE_EXPRESS:.0f} zl zamiast "
                        f"{CIECIE_ZWYKLE:.0f} zl za ciecie)")
    p.add_argument("--bez-ciecia", action="store_true",
                   help="tniesz sam - nie doliczaj kosztu uslugi")
    p.add_argument("--pdf", action="store_true", help="zapisz kartke PDF")
    p.add_argument("--mail", metavar="ADRES", nargs="?", const="dominikmaslak11@gmail.com",
                   help="wyslij PDF na e-mail (domyslnie na wlasny adres)")
    a = p.parse_args(argv)

    try:
        dl, szer = wymiary_z_tekstu(a.wymiary)
    except ValueError as e:
        print(f"BLAD: {e}", file=sys.stderr)
        return 1
    if dl < szer:
        dl, szer = szer, dl  # dłuższy bok zawsze pierwszy

    stawka = 0.0 if a.bez_ciecia else (CIECIE_EXPRESS if a.express else CIECIE_ZWYKLE)
    w = wyceniaj(dl, szer, a.cena, stawka)
    print(raport(w))

    if a.pdf or a.mail:
        # Domyślnie obok kodu, ale na serwerze katalog z kodem to klon gita -
        # sypanie do niego wygenerowanych plików brudzi produkcję. Stąd
        # LOZYSKA_WYNIKI, ustawiane po stronie serwera.
        katalog = Path(os.environ.get("LOZYSKA_WYNIKI",
                                       Path(__file__).resolve().parent / "warsztat"))
        cel = katalog / f"odpad-{dl:.0f}x{szer:.0f}-{a.cena:.0f}zl.pdf"
        buduj_pdf(w, cel)
        print(f"\n  PDF: {cel}")
        if a.mail:
            from wysylka import wyslij_email
            print("  " + wyslij_email(
                a.mail,
                f"Odpad OSB {dl:.0f}x{szer:.0f} - {w.werdykt}",
                raport(w) + "\n\n" + "\n".join(instrukcja_ciecia(w)),
                [cel]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
