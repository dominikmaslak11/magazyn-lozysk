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
        self.cell(0, 5,
                   "Projekt wygenerowany automatycznie - Magazyn Lozysk"
                   if WARIANT == "sklep" else "Magazyn Lozysk - warsztat/plan-ciecia.md",
                   align="C")


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


# Wariant dokumentu. "wlasny" ma kody i ceny Leroya - do reki przy zakupach.
# "sklep" jest neutralny: bez kodow konkurencji i bez cen, za to z kolumnami
# do wypelnienia. Ten sam rysunek techniczny, inna ostatnia strona.
WARIANT = "wlasny"


def zbuduj(sciezka: Path, wariant: str = "wlasny") -> Path:
    global WARIANT
    WARIANT = wariant
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
    plan_deski(pdf)
    plan_szaf(pdf)
    lista_zakupow(pdf)
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




# ============================================ STARA DESKA (strona 4) ===

DESKA_DL, DESKA_SZER, DESKA_GRUB = 1240.0, 520.0, 20.0


def plan_deski(pdf) -> None:
    """Stara deska z blatu biurka: co jest polka, a co przegroda."""
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_y(12)
    pdf.cell(0, 7, "Stara deska z blatu biurka - 1 polka + 2 przegrody", align="C",
              new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"{DESKA_DL:.0f} x {DESKA_SZER:.0f} x {DESKA_GRUB:.0f} mm   |   "
                    f"3 ciecia   |   wykorzystanie 94%",
              align="C", new_x="LMARGIN", new_y="NEXT")

    S = 0.17
    x0, y0 = 40.0, 46.0
    dl, szer = DESKA_DL * S, DESKA_SZER * S

    # --- POLKA ---
    pdf.set_draw_color(90, 90, 90)
    pdf.set_line_width(0.4)
    pdf.set_fill_color(197, 224, 180)
    pdf.rect(x0, y0, POLKA_DL * S, POLKA_GLEB_P() * S, style="FD")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_xy(x0, y0 + POLKA_GLEB_P() * S / 2 - 7)
    pdf.cell(POLKA_DL * S, 6, "POLKA", align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(x0, y0 + POLKA_GLEB_P() * S / 2)
    pdf.cell(POLKA_DL * S, 5, f"{POLKA_DL:.0f} x {POLKA_GLEB_P():.0f} mm", align="C")
    pdf.set_font("Helvetica", "", 7)
    pdf.set_xy(x0, y0 + POLKA_GLEB_P() * S / 2 + 6)
    pdf.cell(POLKA_DL * S, 4, "(najwyzsza w dolnej przestrzeni)", align="C")

    # --- PRZEGRODY ---
    x_p = x0 + (POLKA_DL + RZAZ) * S
    reszta = DESKA_DL - POLKA_DL - RZAZ
    for r in (0, 1):
        yy = y0 + r * (PRZEGRODA_WYS + RZAZ) * S
        pdf.set_fill_color(207, 226, 243)
        pdf.rect(x_p, yy, reszta * S, PRZEGRODA_WYS * S, style="FD")
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_xy(x_p, yy + PRZEGRODA_WYS * S / 2 - 5)
        pdf.cell(reszta * S, 4, f"PRZEGRODA {7+r}", align="C")
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(x_p, yy + PRZEGRODA_WYS * S / 2 - 1)
        pdf.cell(reszta * S, 4, f"{PRZEGRODA_WYS:.0f} x {POLKA_GLEB_P():.0f}", align="C")

    # pasek 3 mm pod przegrodami
    pdf.set_fill_color(245, 235, 200)
    pdf.rect(x_p, y0 + 2 * (PRZEGRODA_WYS + RZAZ) * S, reszta * S,
              (POLKA_GLEB_P() - 2 * PRZEGRODA_WYS - RZAZ) * S, style="FD")

    # --- pasek odpadowy ze zwezenia ---
    pdf.set_fill_color(245, 235, 200)
    pdf.rect(x0, y0 + (POLKA_GLEB_P() + RZAZ) * S, dl,
              (DESKA_SZER - POLKA_GLEB_P() - RZAZ) * S, style="FD")
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.set_xy(x0, y0 + (POLKA_GLEB_P() + RZAZ) * S + 0.5)
    pdf.cell(dl, 4, f"odpad ze zwezenia: {DESKA_DL:.0f} x 21 mm", align="C")
    pdf.set_text_color(0, 0, 0)

    # obrys deski
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.9)
    pdf.rect(x0, y0, dl, szer)

    # linie ciec
    pdf.set_draw_color(200, 0, 0)
    pdf.set_line_width(0.8)
    y1 = y0 + (POLKA_GLEB_P() + RZAZ / 2) * S
    pdf.line(x0 - 6, y1, x0 + dl + 3, y1)                                  # 1 - zwezenie
    x2 = x0 + (POLKA_DL + RZAZ / 2) * S
    pdf.line(x2, y0 - 6, x2, y0 + (POLKA_GLEB_P()) * S + 2)                # 2 - polka
    y3 = y0 + (PRZEGRODA_WYS + RZAZ / 2) * S
    pdf.line(x_p - 3, y3, x0 + dl + 3, y3)                                 # 3 - przegrody
    for xc, yc, nr in ((x0 - 12, y1, "1"), (x2, y0 - 12, "2"), (x0 + dl + 7, y3, "3")):
        pdf.set_fill_color(200, 0, 0)
        pdf.ellipse(xc - 2.6, yc - 2.6, 5.2, 5.2, style="F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_xy(xc - 4, yc - 2.1)
        pdf.cell(8, 4, nr, align="C")
        pdf.set_text_color(0, 0, 0)

    # wymiary
    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(x0, y0 + szer + 5)
    pdf.cell(dl, 5, f"{DESKA_DL:.0f} mm", align="C")

    yt = y0 + szer + 20
    pdf.set_xy(16, yt)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Kolejnosc", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    for nr, tresc in (
        ("1", f"wzdluz calej deski: zwezenie {DESKA_SZER:.0f} -> {POLKA_GLEB_P():.0f} mm "
               f"(odpada pasek {DESKA_DL:.0f} x 21 mm)"),
        ("2", f"w poprzek na {POLKA_DL:.0f} mm -> POLKA {POLKA_DL:.0f} x {POLKA_GLEB_P():.0f}, "
               f"zostaje kawalek {reszta:.0f} x {POLKA_GLEB_P():.0f}"),
        ("3", f"ten kawalek na pol -> DWIE PRZEGRODY {PRZEGRODA_WYS:.0f} x {POLKA_GLEB_P():.0f} "
               f"(2 x 187 + rzaz = 378 <= {reszta:.0f}, zapas 3 mm)"),
    ):
        pdf.set_x(16)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.cell(10, 5, nr)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.cell(0, 5, tresc, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 8.5)
    for linia in (
        "Deska ma 20 mm, reszta polek 18 - to nie przeszkadza, rozstaw jest przeliczony.",
        "Blat biurka to laminowana plyta wiorowa: ZABEZPIECZ KRAWEDZIE po cieciu",
        "(obrzeze, silikon albo farba) - laminat chroni tylko plaszczyzny, odsloniety kant pecznieje.",
        "Ta deska daje polke NAJWYZSZA W DOLNEJ PRZESTRZENI (spod na 1233 mm nad dnem).",
    ):
        pdf.set_x(16)
        pdf.cell(0, 4.6, linia, new_x="LMARGIN", new_y="NEXT")


# ================================================ SZAFY NA UBRANIA (str. 5) ===

SZAFA = (1200.0, 760.0, 470.0)     # wysokosc x szerokosc x glebokosc wnetrza
SZAFA_SCIANKA = 16.0
SZAFA_POLEK = 3
SZAFA_POLKA = (755.0, 450.0)
SZAFA_GRUB = 18.0
SZAF = 2


def plan_szaf(pdf) -> None:
    """Drugi projekt: polki do dwoch szaf na ubrania."""
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_y(12)
    pdf.cell(0, 7, "Szafy na ubrania - 3 polki w kazdej z dwoch", align="C",
              new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    k = (SZAFA[0] - SZAFA_POLEK * SZAFA_GRUB) / (SZAFA_POLEK + 1)
    pdf.cell(0, 5, f"Przestrzen {SZAFA[0]:.0f} x {SZAFA[1]:.0f} x {SZAFA[2]:.0f} mm, "
                    f"scianka {SZAFA_SCIANKA:.0f} mm   |   4 poziomy po {k:.0f} mm",
              align="C", new_x="LMARGIN", new_y="NEXT")

    S = 0.105
    x0, y0 = 40.0, 34.0
    szer, wys = SZAFA[1] * S, SZAFA[0] * S

    def py(z):
        return y0 + wys - z * S

    pdf.set_draw_color(60, 60, 60)
    pdf.set_line_width(0.4)
    pdf.set_fill_color(205, 200, 190)
    for x in (x0 - SZAFA_SCIANKA * S, x0 + szer):
        pdf.rect(x, y0, SZAFA_SCIANKA * S, wys, style="FD")
    for z in (-SZAFA_SCIANKA, SZAFA[0]):
        pdf.rect(x0 - SZAFA_SCIANKA * S, py(z + SZAFA_SCIANKA),
                  szer + 2 * SZAFA_SCIANKA * S, SZAFA_SCIANKA * S, style="FD")

    z = k
    for i in range(1, SZAFA_POLEK + 1):
        pdf.set_fill_color(250, 250, 248)
        pdf.rect(x0, py(z + SZAFA_GRUB), szer, SZAFA_GRUB * S, style="FD")
        yy = py(z + SZAFA_GRUB / 2)
        pdf.set_draw_color(140, 140, 140)
        pdf.set_line_width(0.2)
        pdf.line(x0 + szer, yy, x0 + szer + 5, yy)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_xy(x0 + szer + 6, yy - 2)
        pdf.cell(40, 4, f"{z + SZAFA_GRUB:.0f} mm")
        pdf.set_draw_color(60, 60, 60)
        pdf.set_line_width(0.4)
        z += SZAFA_GRUB + k

    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.8)
    pdf.rect(x0, y0, szer, wys)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(x0, y0 + wys + 4)
    pdf.cell(szer, 5, f"{SZAFA[1]:.0f} mm", align="C")

    X = 150.0
    pdf.set_xy(X, 36)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Formatki do zamowienia (na wymiar)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for linia in (
        f"{SZAF * SZAFA_POLEK} x   {SZAFA_POLKA[0]:.0f} x {SZAFA_POLKA[1]:.0f} mm",
        "plyta meblowa laminowana BIALA 18 mm",
        "",
        f"755 = {SZAFA[1]:.0f} minus 5 mm luzu",
        f"450 zamiast {SZAFA[2]:.0f} - 2 cm zapasu na zawiasy",
        f"razem {SZAF * SZAFA_POLEK * SZAFA_POLKA[0] * SZAFA_POLKA[1] / 1e6:.2f} m2",
    ):
        pdf.set_x(X)
        pdf.cell(0, 5, linia, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)
    pdf.set_x(X)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, "Dlaczego 18 mm, a nie 16 jak scianki", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    for linia in (
        "Rozpietosc 76 cm. Ugiecie po latach, granica 3,8 mm:",
        "   16 mm:  15 kg -> 3,8 mm   20 kg -> 5,1 mm  za duzo",
        "   18 mm:  15 kg -> 2,7 mm   20 kg -> 3,6 mm  OK",
        "",
        "POSCIELI I KOCOW (25-30 kg) na te polki nie kladz -",
        "wygna kazda plyte na tej rozpietosci.",
        "",
        "Cieta krawedz bialej plyty to gola wiorowa - oklej",
        "obrzezem przednie krawedzie, razem 4,5 m.",
    ):
        pdf.set_x(X)
        pdf.cell(0, 4.6, linia, new_x="LMARGIN", new_y="NEXT")


# ==================================================== LISTA ZAKUPOW (str. 6) ===

def lista_zakupow(pdf) -> None:
    if WARIANT == "sklep":
        return lista_dla_sklepu(pdf)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_y(12)
    pdf.cell(0, 7, "LISTA ZAKUPOW - jeden wyjazd, dwa projekty", align="C",
              new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "ulozona dzialami sklepu", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    dzialy = [
        ("DZIAL PLYT", [
            ("OSB-3 18 mm, arkusz 250 x 125 cm (kod 43226043)", "1 szt.", "104 zl"),
            ("plyta laminowana BIALA 18 mm - DOCIETA NA WYMIAR", "2,04 m2", "~78 zl"),
            ("     zamowienie: 6 formatek 755 x 450 mm", "", ""),
        ]),
        ("DZIAL DREWNA", [
            ("listwa montazowa sosnowa 20 x 30 x 2700 (kod 45216185)", "4 szt.", "~48 zl"),
        ]),
        ("DZIAL METALOWY", [
            ("wkrety do drewna 4 x 35 mm, OCYNKOWANE", "100 szt.", "~25 zl"),
            ("wkrety do drewna 3,5 x 30 mm, OCYNKOWANE", "100 szt.", "~20 zl"),
            ("podporki do polek, kolek 5 mm", "24 szt.", "~15 zl"),
        ]),
        ("DZIAL WYKONCZENIA", [
            ("obrzeze melaminowe biale 18-19 mm, rolka 5 m", "1-2 szt.", "~30 zl"),
        ]),
    ]
    for naglowek, pozycje in dzialy:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_x(18)
        pdf.cell(0, 6, naglowek, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for co, ile, cena in pozycje:
            pdf.set_x(22)
            pdf.cell(150, 5.4, co)
            pdf.cell(28, 5.4, ile)
            pdf.cell(0, 5.4, cena, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_x(18)
    pdf.cell(150, 6, "RAZEM")
    pdf.cell(0, 6, "~320 zl", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_x(18)
    pdf.cell(0, 5, "   (regal na lozyska ~197 zl + szafy ~123 zl, plus oplata za dociecie)",
              new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_x(18)
    pdf.cell(0, 5, "NA CO UWAZAC", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    for linia in (
        "Wkretow NIE zaokraglaj w gore: scianka regalu ma 20 mm, scianka szafy 16 -",
        "wkret 40 mm przebije jedna i druga na wylot.",
        "Nie bierz wkretow nierdzewnych, sa kilka razy drozsze i do wnetrza niepotrzebne.",
        "Nie bierz calego arkusza bialej plyty: 220 zl za 5,8 m2, gdy potrzebujesz 2 m2.",
        "Zapytaj PRZEZ TELEFON o cene dociecia - zalezy od sklepu i potrafi zaskoczyc.",
    ):
        pdf.set_x(22)
        pdf.cell(0, 4.8, linia, new_x="LMARGIN", new_y="NEXT")


def lista_dla_sklepu(pdf) -> None:
    """Ostatnia strona w wersji dla sklepu: zapotrzebowanie bez kodow i cen konkurencji,
    za to z kolumnami do wypelnienia przez sprzedawce."""
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_y(12)
    pdf.cell(0, 7, "ZAPOTRZEBOWANIE MATERIALOWE", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "dwa projekty - regal warsztatowy i polki do dwoch szaf",
              align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    kol = (96, 24, 26, 26, 26)
    pdf.set_x(14)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(228, 228, 228)
    for tekst, szer in zip(("Pozycja", "Ilosc", "Macie?", "Cena j.", "Termin"), kol):
        pdf.cell(szer, 7, tekst, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    pozycje = [
        ("Plyta OSB-3 18 mm, arkusz 2500 x 1250 mm", "1 szt."),
        ("Plyta wiorowa laminowana BIALA 18 mm, dociecie na wymiar", "2,04 m2"),
        ("     -> 6 formatek 755 x 450 mm, obrzeze na 1 dluzszym boku", ""),
        ("Listwa sosnowa 20 x 30 mm, dl. 2,7 m (lub kantowka 20x30)", "4 szt."),
        ("Wkrety do drewna 4 x 35 mm, ocynkowane", "100 szt."),
        ("Wkrety do drewna 3,5 x 30 mm, ocynkowane", "100 szt."),
        ("Podporki do polek, kolek 5 mm, metalowe", "24 szt."),
        ("Obrzeze melaminowe biale 18-19 mm z klejem, rolka 5 m", "2 szt."),
        ("USLUGA: ciecie plyty na wymiar", "9 ciec"),
        ("Uzyteczne odpady po docinaniu, od ok. 40 x 40 cm", "wg dostepnosci"),
    ]
    for opis, ile in pozycje:
        pdf.set_x(14)
        pdf.cell(kol[0], 7.5, opis, border=1)
        pdf.cell(kol[1], 7.5, ile, border=1, align="C")
        for szer in kol[2:]:
            pdf.cell(szer, 7.5, "", border=1)
        pdf.ln()

    pdf.ln(6)
    pdf.set_x(14)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Uwagi do zamowienia", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    for linia in (
        "Wkrety NIE dluzsze niz podane: scianka regalu ma 20 mm, scianka szafy 16 mm.",
        "Dluzszy wkret przebije ja na wylot.",
        "",
        "Plyta biala jest widoczna w otwartej szafie - ciete krawedzie wymagaja obrzeza.",
        "Jesli oklejacie w ramach uslugi, prosze o wycene zamiast rolki.",
        "",
        "Jesli czesc pozycji odpada, prosze o wycene reszty - i tak wole kupic na miejscu.",
        "",
        "Rysunki na poprzednich stronach pokazuja, do czego te materialy sluza:",
        "plan ciecia arkusza, widok zabudowy regalu i widok zabudowy szafy.",
    ):
        pdf.set_x(14)
        pdf.cell(0, 4.8, linia, new_x="LMARGIN", new_y="NEXT")


if __name__ == "__main__":
    import sys
    wariant = "sklep" if "--sklep" in sys.argv else "wlasny"
    argi = [a for a in sys.argv[1:] if not a.startswith("--")]
    domyslny = "warsztat/projekt-arsen.pdf" if wariant == "sklep" else "warsztat/plan-ciecia.pdf"
    cel = Path(argi[0]) if argi else Path(domyslny)
    cel.parent.mkdir(parents=True, exist_ok=True)
    print("Zapisano:", zbuduj(cel, wariant))
