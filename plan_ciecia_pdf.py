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

# --- rysunek montażowy (strona 2) ---
REGAL_SZER = 860.0        # wewnętrzna szerokość regału
PRZESTRZEN = 1420.0       # prześwit dolnej półki - tyle dzielimy
POLKA_GRUB = 18.0
DESKA_GRUB = 20.0         # stara deska z biurka
POLEK = 6
SKALA_M = 0.09


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
        if self.page_no() != 1:
            return
        self.set_font("Helvetica", "B", 15)
        self.cell(0, 8, "Plan ciecia - 6 polek + material na przegrody", align="C", new_x="LMARGIN",
                   new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, f"Arkusz OSB-3 18 mm, 2500 x 1250 mm   |   skala 1:{1/SKALA:.0f}   |   "
                         f"rzaz tarczy {RZAZ:.0f} mm uwzgledniony",
                   align="C", new_x="LMARGIN", new_y="NEXT")

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 5, "Magazyn Lozysk - warsztat/plan-ciecia.md", align="C")


def rysuj(pdf, u) -> None:
    """Arkusz z pasami, cieciami i odpadem.

    KOLEJNOSC: najpierw JEDNO ciecie w poprzek calego arkusza (odcina pas na polki
    od pasa odpadowego), potem cztery ciecia wzdluz - tylko w pasie na polki.
    To pomysl uzytkownika i jest lepszy od odwrotnego: 5 ciec zamiast 9, a odpad
    zostaje jednym kawalkiem 2500 x 391 zamiast pieciu osobnych.
    """
    wys_polki = POLKA_DL * SKALA
    wys_odpadu = (ARKUSZ_SZER - POLKA_DL - RZAZ) * SKALA
    szer_pasa = PAS * SKALA
    szer_ark = ARKUSZ_DL * SKALA

    # pas na półki
    pdf.set_fill_color(207, 226, 243)
    pdf.set_draw_color(90, 90, 90)
    pdf.set_line_width(0.4)
    pdf.rect(u.px(0), u.py(0), szer_ark, wys_polki, style="FD")

    # DOLNY PAS: 7. polka (wezsza) + material na przegrody
    y_pas = u.py(POLKA_DL + RZAZ)
    pdf.set_fill_color(236, 236, 236)
    pdf.rect(u.px(0), y_pas, szer_ark, wys_odpadu, style="FD")

    # 7. polka - wezsza, na pelna szerokosc pasa
    pdf.set_fill_color(197, 224, 180)
    pdf.set_draw_color(90, 90, 90)
    pdf.rect(u.px(0), y_pas, POLKA_DL * SKALA, wys_odpadu, style="FD")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_xy(u.px(0), y_pas + wys_odpadu / 2 - 5)
    pdf.cell(POLKA_DL * SKALA, 4, "POLKA 7 (wezsza)", align="C")
    pdf.set_font("Helvetica", "", 7)
    pdf.set_xy(u.px(0), y_pas + wys_odpadu / 2 - 1)
    pdf.cell(POLKA_DL * SKALA, 4,
              f"{POLKA_DL:.0f} x {ARKUSZ_SZER - POLKA_DL - RZAZ:.0f}", align="C")

    # material na przegrody - trzy kawalki po 495
    x2 = POLKA_DL + RZAZ
    for i in range(3):
        pdf.set_fill_color(207, 226, 243)
        pdf.rect(u.px(x2), y_pas, PAS * SKALA, wys_odpadu, style="FD")
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(u.px(x2), y_pas + wys_odpadu / 2 - 4)
        pdf.cell(PAS * SKALA, 4, "2 przegrody", align="C")
        pdf.set_xy(u.px(x2), y_pas + wys_odpadu / 2)
        pdf.cell(PAS * SKALA, 4, f"{PAS:.0f} x 391", align="C")
        x2 += PAS + RZAZ
    pdf.set_text_color(0, 0, 0)

    # podział pasa na półki
    x = 0.0
    for nr in range(1, PASOW + 1):
        lx = u.px(x)
        pdf.set_draw_color(90, 90, 90)
        pdf.set_line_width(0.3)
        pdf.rect(lx, u.py(0), szer_pasa, wys_polki)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_xy(lx, u.py(0) + wys_polki / 2 - 5)
        pdf.cell(szer_pasa, 5, f"POLKA {nr}", align="C")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_xy(lx, u.py(0) + wys_polki / 2 + 1)
        pdf.cell(szer_pasa, 5, f"{POLKA_DL:.0f} x {PAS:.0f}", align="C")
        x += PAS
        if nr < PASOW:
            xc = u.px(x + RZAZ / 2)
            pdf.set_draw_color(200, 0, 0)
            pdf.set_line_width(0.7)
            pdf.line(xc, u.py(0) - 7, xc, u.py(POLKA_DL) + 2)   # tylko w pasie na półki
            pdf.set_fill_color(200, 0, 0)
            pdf.ellipse(xc - 2.6, u.py(0) - 12.5, 5.2, 5.2, style="F")
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_xy(xc - 4, u.py(0) - 12)
            pdf.cell(8, 4, str(nr + 1), align="C")
            pdf.set_text_color(0, 0, 0)
            x += RZAZ

    # cięcie nr 1 - w poprzek CAŁEGO arkusza
    yc = u.py(POLKA_DL + RZAZ / 2)
    pdf.set_draw_color(200, 0, 0)
    pdf.set_line_width(1.0)
    pdf.line(u.px(0) - 8, yc, u.px(ARKUSZ_DL) + 8, yc)
    pdf.set_fill_color(200, 0, 0)
    pdf.ellipse(u.px(0) - 15, yc - 2.6, 5.2, 5.2, style="F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_xy(u.px(0) - 17, yc - 2.1)
    pdf.cell(8, 4, "1", align="C")
    pdf.set_text_color(0, 0, 0)

    # obrys arkusza
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.9)
    pdf.rect(u.px(0), u.py(0), szer_ark, ARKUSZ_SZER * SKALA)

    # wymiary
    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(u.px(0), u.py(ARKUSZ_SZER) + 4)
    pdf.cell(szer_ark, 5, f"{ARKUSZ_DL:.0f} mm", align="C")
    pdf.set_xy(u.px(0) - 26, u.py(POLKA_DL / 2) - 2)
    pdf.cell(22, 5, f"{POLKA_DL:.0f}", align="R")
    pdf.set_xy(u.px(0) - 26, u.py(POLKA_DL + RZAZ + (ARKUSZ_SZER - POLKA_DL) / 2) - 2)
    pdf.cell(22, 5, f"{ARKUSZ_SZER - POLKA_DL - RZAZ:.0f}", align="R")


def zbuduj(sciezka: Path) -> Path:
    pdf = PlanCiecia(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()

    u = Ustawienie(x=38, y=40)
    rysuj(pdf, u)

    y = u.y + ARKUSZ_SZER * SKALA + 11
    pdf.set_xy(16, y)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Kolejnosc ciec - NAJPIERW POPRZECZNE", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)
    linie = [
        ("1", f"JEDNO ciecie w poprzek calego arkusza, na {POLKA_DL:.0f} mm. "
               f"Gorny pas idzie na 5 polek, dolny ({ARKUSZ_DL:.0f} x "
               f"{ARKUSZ_SZER - POLKA_DL - RZAZ:.0f}) na 7. polke i przegrody."),
        ("2-5", f"cztery ciecia wzdluz pasa na polki: piec kawalkow po {PAS:.0f} mm "
                 f"(NIE po 500 - cztery rzazy zabieraja {4*RZAZ:.0f} mm i ostatni "
                 f"wyszedlby na {ARKUSZ_DL - 4*PAS - 4*RZAZ:.0f} mm)"),
    ]
    for nr, tresc in linie:
        pdf.set_x(16)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.cell(10, 5, nr)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.cell(0, 4.4, tresc, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 8)
    for linia in (
        f"6-9  z dolnego pasa: 7. polka {POLKA_DL:.0f} x 391 (wezsza, na gora regalu),",
        f"     potem 3 kawalki po {PAS:.0f} mm -> po dwie przegrody z kazdego.",
        "",
        "Pierwsza polke przymierz do regalu, ZANIM potniesz reszte pasa.",
        f"Szosta polka: stara deska z blatu biurka, tnij w domu na {POLKA_DL:.0f} x {PAS:.0f} mm",
        "(z jej odpadu 381 x 495 wychodza jeszcze 2 przegrody).",
    ):
        pdf.set_x(16)
        pdf.cell(0, 5, linia, new_x="LMARGIN", new_y="NEXT")

    rysunek_montazowy(pdf)
    plan_przegrod(pdf)
    pdf.output(str(sciezka))
    return sciezka


def komora_wys() -> float:
    """Prześwit jednej komory po odjęciu grubości wszystkich półek."""
    return (PRZESTRZEN - (POLEK - 1) * POLKA_GRUB - DESKA_GRUB) / (POLEK + 1)


def rysunek_montazowy(pdf) -> None:
    """Widok z przodu: co z czego powstaje i na jakiej wysokosci."""
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_y(12)
    pdf.cell(0, 7, "Regal 2 - podzial dolnej przestrzeni na 7 poziomow", align="C",
              new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"widok z przodu   |   skala 1:{1/SKALA_M:.0f}   |   glebokosc polek {PAS:.0f} mm",
              align="C", new_x="LMARGIN", new_y="NEXT")

    k = komora_wys()
    x0, y0 = 42.0, 32.0
    szer = REGAL_SZER * SKALA_M
    wys = PRZESTRZEN * SKALA_M
    X_OPIS = x0 + szer + 5          # kolumna z wysokosciami
    X_WYKAZ = 178.0                 # kolumna z wykazem - osobno, bez kolizji

    def py(z: float) -> float:
        return y0 + wys - z * SKALA_M

    # scianki, dno, sufit
    pdf.set_draw_color(60, 60, 60)
    pdf.set_line_width(0.4)
    pdf.set_fill_color(175, 175, 175)
    for x in (x0 - 20 * SKALA_M, x0 + szer):
        pdf.rect(x, y0, 20 * SKALA_M, wys, style="FD")
    pdf.set_fill_color(150, 150, 150)
    pdf.rect(x0 - 20 * SKALA_M, y0 + wys, szer + 40 * SKALA_M, 20 * SKALA_M, style="FD")
    pdf.rect(x0 - 20 * SKALA_M, y0 - 20 * SKALA_M, szer + 40 * SKALA_M, 20 * SKALA_M, style="FD")

    z = k
    for i in range(1, POLEK + 1):
        ostatnia = i == POLEK
        grub = DESKA_GRUB if ostatnia else POLKA_GRUB
        pdf.set_fill_color(207, 226, 243)
        pdf.set_draw_color(60, 60, 60)
        pdf.rect(x0 + szer / 2 - POLKA_GRUB * SKALA_M / 2, py(z), POLKA_GRUB * SKALA_M,
                  k * SKALA_M, style="FD")
        pdf.set_fill_color(*((140, 96, 62) if ostatnia else (212, 184, 130)))
        pdf.rect(x0, py(z + grub), szer, grub * SKALA_M, style="FD")

        # linia odniesienia i opis
        yy = py(z + grub / 2)
        pdf.set_draw_color(120, 120, 120)
        pdf.set_line_width(0.2)
        pdf.line(x0 + szer, yy, X_OPIS - 1, yy)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(0, 0, 0)
        pdf.set_xy(X_OPIS, yy - 2)
        pdf.cell(16, 4, f"{z + grub:.0f}")
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(X_OPIS + 14, yy - 2)
        pdf.cell(50, 4, "stara deska, 20 mm" if ostatnia else f"OSB 18 mm  (polka {i})")
        z += grub + k

    pdf.set_fill_color(207, 226, 243)
    pdf.set_draw_color(60, 60, 60)
    pdf.rect(x0 + szer / 2 - POLKA_GRUB * SKALA_M / 2, py(z), POLKA_GRUB * SKALA_M,
              k * SKALA_M, style="FD")

    # wymiar calkowity
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.3)
    xw = x0 - 16
    pdf.line(xw, y0, xw, y0 + wys)
    for yy in (y0, y0 + wys):
        pdf.line(xw - 1.5, yy, xw + 1.5, yy)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_xy(xw - 16, y0 + wys / 2 - 2)
    pdf.cell(14, 4, f"{PRZESTRZEN:.0f}", align="R")

    # wymiar komory
    pdf.set_draw_color(200, 0, 0)
    pdf.set_line_width(0.4)
    xk = x0 + 6
    pdf.line(xk, py(0), xk, py(k))
    for yy in (py(0), py(k)):
        pdf.line(xk - 1.5, yy, xk + 1.5, yy)
    pdf.set_text_color(200, 0, 0)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_xy(xk + 2, (py(0) + py(k)) / 2 - 2)
    pdf.cell(26, 4, f"{k:.0f} przeswitu")
    pdf.set_text_color(0, 0, 0)

    pdf.set_draw_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_xy(x0 - 10, y0 + wys + 24 * SKALA_M + 2)
    pdf.cell(szer + 20, 5, f"{REGAL_SZER:.0f} wewnatrz / polka {POLKA_DL:.0f}", align="C")

    # ----- wykaz, osobna kolumna -----
    pdf.set_xy(X_WYKAZ, 34)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Wykaz elementow", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    for linia in (
        f"5 x  polka OSB-3 18 mm       {POLKA_DL:.0f} x {PAS:.0f}   z arkusza",
        f"1 x  polka ze starej deski   {POLKA_DL:.0f} x {PAS:.0f}   blat biurka, 20 mm",
        f"7 x  przegroda pionowa       {k:.0f} x {PAS:.0f}   z odpadu 2500 x 391",
        f"12 x listwa podporowa        20 x 30 x 500   do kupienia (ok. 6 m)",
    ):
        pdf.set_x(X_WYKAZ)
        pdf.cell(0, 5, linia, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)
    pdf.set_x(X_WYKAZ)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, "Po co przegroda pionowa", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    for linia in (
        "Dzieli rozpietosc polki z 860 na 428 mm.",
        "Ugiecie spada z 5,7 mm do 0,35 mm - szesnastokrotnie.",
        "Wychodzi z odpadu, wiec nic nie kosztuje.",
        "MUSZA stac jedna nad druga - przenosza",
        "obciazenie az na dno regalu.",
        "",
        "Przy okazji dzieli kazda polke na dwie czesci,",
        "co samo porzadkuje lozyska wg rozmiaru.",
    ):
        pdf.set_x(X_WYKAZ)
        pdf.cell(0, 4.5, linia, new_x="LMARGIN", new_y="NEXT")




# ============================================ PRZEGRODY Z ODPADU (strona 3) ===

PASEK_DL = ARKUSZ_DL
PASEK_SZER = ARKUSZ_SZER - POLKA_DL - RZAZ      # 391 mm
PRZEGRODA_WYS = 187.0                            # = prześwit komory
PRZEGROD_POTRZEBA = 7
KAWALKOW = 4                                     # 4 kawałki x 2 = 8 przegród
SKALA_P = 0.088


def plan_przegrod(pdf) -> None:
    """Jak z kawalkow zrobic przegrody - wszystkie zrodla w jednym rzedzie."""
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_y(12)
    pdf.cell(0, 7, "Przegrody - 8 sztuk 187 x 495 mm", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Kazdy kawalek JEDNYM cieciem daje dwie przegrody. Potrzeba 7, wychodzi 8.",
              align="C", new_x="LMARGIN", new_y="NEXT")

    S = 0.12
    y0 = 42.0
    dl = PAS * S
    odstep = 12.0
    zrodla = [("z arkusza", 391.0), ("z arkusza", 391.0), ("z arkusza", 391.0),
              ("ze starej deski", 381.0)]
    x = 22.0
    nr = 1
    for opis, szer_kawalka in zrodla:
        wys = szer_kawalka * S
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_xy(x, y0 - 11)
        pdf.cell(dl, 4, f"{PAS:.0f} x {szer_kawalka:.0f}", align="C")
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_xy(x, y0 - 7)
        pdf.cell(dl, 4, opis, align="C")

        pdf.set_draw_color(90, 90, 90)
        pdf.set_line_width(0.4)
        for r in (0, 1):
            pdf.set_fill_color(207, 226, 243)
            yy = y0 + r * (PRZEGRODA_WYS + RZAZ) * S
            pdf.rect(x, yy, dl, PRZEGRODA_WYS * S, style="FD")
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_xy(x, yy + PRZEGRODA_WYS * S / 2 - 2)
            pdf.cell(dl, 4, str(nr), align="C")
            nr += 1
        reszta = szer_kawalka - 2 * PRZEGRODA_WYS - RZAZ
        if reszta > 2:
            pdf.set_fill_color(245, 235, 200)
            pdf.rect(x, y0 + 2 * (PRZEGRODA_WYS + RZAZ) * S, dl, reszta * S, style="FD")

        yc = y0 + (PRZEGRODA_WYS + RZAZ / 2) * S
        pdf.set_draw_color(200, 0, 0)
        pdf.set_line_width(0.7)
        pdf.line(x - 3, yc, x + dl + 3, yc)
        x += dl + odstep

    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.set_xy(22, y0 + 391.0 * S + 3)
    pdf.cell(0, 4, "zolty pasek u dolu = 13 mm odpadu, do kosza")
    pdf.set_text_color(0, 0, 0)

    yt = y0 + 391.0 * S + 16
    pdf.set_xy(16, yt)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Zanim utniesz", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    for linia in (
        "WYSOKOSC TNIJ NA MIEJSCU, po zamontowaniu pierwszej polki. 187 mm to wyliczenie;",
        "realne grubosci plyt roznia sie o ulamki milimetra, a bledy sumuja sie przez szesc poziomow.",
        "Za krotka przegroda nie robi nic, za dluga podnosi polke nad podpory boczne.",
        "",
        "Przegroda pracuje na SCISKANIE - wkrety maja ja tylko trzymac przed przewroceniem.",
        "Dwa wkrety 3,5 x 30 od gory wystarcza, ale NAWIERC otwor 2,5 mm: wkret wbity na sile",
        "w kant plyty rozwarstwia ja wzdluz i przegroda traci sztywnosc, czyli to, po co tam jest.",
        "",
        "Wszystkie przegrody MUSZA stac w jednej pionowej linii - obciazenie schodzi przez nie",
        "az na dno regalu. Odmierz srodek (430 mm od scianki) i zaznaczaj poziomica, nie na oko.",
    ):
        pdf.set_x(16)
        pdf.cell(0, 4.6, linia, new_x="LMARGIN", new_y="NEXT")


def POLKA_GLEB_P() -> float:
    """Glebokosc polki - tyle ma przegroda na dlugosc."""
    return PAS


if __name__ == "__main__":
    import sys
    cel = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("warsztat/plan-ciecia.pdf")
    cel.parent.mkdir(parents=True, exist_ok=True)
    print("Zapisano:", zbuduj(cel))
