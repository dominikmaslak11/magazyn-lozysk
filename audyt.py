"""Audyt bazy łożysk: co się nie zgadza i co z tym zrobić.

Po co osobne narzędzie, skoro appka ma już podpowiedzi: tamte pilnują MAGAZYNU
(gdzie co leży, ile zostało), a to pilnuje DANYCH (czy symbol, wymiary i typ
w ogóle mogą być prawdziwe). To dwie różne robocze pory dnia - podpowiedzi
czyta się przy regale, audyt uruchamia się po sesji wpisywania.

ZASADA NACZELNA: narzędzie NICZEGO nie zmienia samo z siebie. Domyślnie tylko
raportuje. Poprawki stosuje wyłącznie na wyraźne żądanie (--zastosuj) i tylko
te, które wynikają z KATALOGU - czyli ze źródła, które da się wskazać palcem.
Propozycji od modeli AI nie zapisuje NIGDY, bo pomyłka w bazie magazynowej
wygląda potem dokładnie tak samo jak prawda.

Użycie:
    python audyt.py                  # raport
    python audyt.py --oznaczone      # SAMA lista pozycji z ptaszkiem "do sprawdzenia"
    python audyt.py --ai             # raport + zapytanie modeli o brakujące wymiary
    python audyt.py --zastosuj       # zapisz poprawki pewne (z katalogu)

Umówiony tryb pracy: użytkownik zaznacza ptaszek "do sprawdzenia" przy pozycjach,
których nie da się rozpoznać przy regale (nieczytelne oznaczenie, nieznana seria,
podejrzany wymiar) i opisuje w uwagach, co budzi wątpliwość. Potem `--oznaczone`
daje gotową listę do rozpracowania: sprawdzenia w katalogach producentów i - gdy
trzeba - dopisania nowej serii do reguł rozpoznawania.

Tak powstały dotąd: rozdzielenie UC/ES, calowe 37431A i seria RAE (INA), gdzie
liczba w oznaczeniu to otwór w milimetrach, a nie kod otworu.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

import bearing_types
import database as db
from bearing_data import BEARING_DB, BEARING_TYPE

# Ile milimetrów różnicy między wpisem a katalogiem uznajemy za to samo. Suwmiarka
# i zaokrąglenia katalogowe potrafią się rozjechać o ułamek milimetra i nie jest to
# błąd; różnica rzędu milimetra to już inne łożysko.
TOLERANCJA_MM = 0.6

# Wagi - te same trzy poziomy co w powiadomieniach w appce, żeby nie mnożyć skal.
KRYTYCZNA = "krytyczna"       # dane wewnętrznie sprzeczne, nie da się na nich polegać
OSTRZEZENIE = "ostrzezenie"   # coś się nie zgadza i wymaga oka
INFORMACJA = "informacja"     # brak danych, ale nic nie jest sprzeczne


@dataclass
class Uwaga:
    """Jedno spostrzeżenie audytu."""
    bearing_id: str
    symbol: str
    rodzaj: str
    waga: str
    opis: str
    # Gotowa poprawka do zapisania, jeśli jest PEWNA (pochodzi z katalogu).
    # None = trzeba obejrzeć/zmierzyć, program nie ma czym tego rozstrzygnąć.
    poprawka: dict | None = None


@dataclass
class Wynik:
    uwagi: list[Uwaga] = field(default_factory=list)
    sprawdzonych: int = 0

    def wagi(self) -> dict[str, int]:
        liczniki = {KRYTYCZNA: 0, OSTRZEZENIE: 0, INFORMACJA: 0}
        for u in self.uwagi:
            liczniki[u.waga] += 1
        return liczniki


def _rozne(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) > TOLERANCJA_MM


def audyt() -> Wynik:
    """Przechodzi całą bazę i zbiera wszystko, co nie trzyma się kupy."""
    wynik = Wynik()
    lozyska = db.get_bearings()
    wynik.sprawdzonych = len(lozyska)

    for b in lozyska:
        symbol = (b.symbol or "").strip()

        # 1. Wymiary wewnętrznie sprzeczne. Nie da się tego zinterpretować inaczej
        #    niż jako pomyłkę przy wpisywaniu - otwór nie może być większy niż całość.
        if b.d is not None and b.D is not None and b.d >= b.D:
            wynik.uwagi.append(Uwaga(
                b.id, symbol, "wymiary_sprzeczne", KRYTYCZNA,
                f"otwór {b.d:g} mm nie jest mniejszy od średnicy zewnętrznej {b.D:g} mm"))
        if b.B is not None and b.B <= 0:
            wynik.uwagi.append(Uwaga(
                b.id, symbol, "wymiary_sprzeczne", KRYTYCZNA,
                f"szerokość {b.B:g} mm jest niedodatnia"))

        # 2. Zgodność z katalogiem. Katalog jest źródłem, które da się wskazać palcem,
        #    więc rozbieżność z nim to konkretna poprawka, a nie zgadywanka.
        kat = BEARING_DB.get(symbol.upper())
        if kat:
            kd, kD, kB = kat
            rozbieznosci = []
            if _rozne(b.d, kd):
                rozbieznosci.append(f"otwór {b.d:g} -> {kd:g}")
            if _rozne(b.D, kD):
                rozbieznosci.append(f"śr. zewn. {b.D:g} -> {kD:g}")
            if _rozne(b.B, kB):
                rozbieznosci.append(f"szerokość {b.B:g} -> {kB:g}")
            brakujace = [n for n, v in (("d", b.d), ("D", b.D), ("B", b.B)) if v is None]

            if rozbieznosci or brakujace:
                poprawka = {"d": kd, "D": kD, "B": kB}
                opis = (f"katalog podaje {kd:g} x {kD:g} x {kB:g} mm"
                        + (f"; różnice: {', '.join(rozbieznosci)}" if rozbieznosci else "")
                        + (f"; brak wymiarów: {', '.join(brakujace)}" if brakujace else ""))
                wynik.uwagi.append(Uwaga(
                    b.id, symbol, "niezgodny_z_katalogiem",
                    OSTRZEZENIE if rozbieznosci else INFORMACJA, opis, poprawka))

            typ_kat = BEARING_TYPE.get(symbol.upper())
            if typ_kat and b.typ != typ_kat:
                wynik.uwagi.append(Uwaga(
                    b.id, symbol, "typ_niezgodny_z_katalogiem", OSTRZEZENIE,
                    f"typ wpisany {b.typ!r}, katalog mówi {typ_kat!r}", {"typ": typ_kat}))
            continue        # katalog rozstrzyga; dalsze heurystyki są już niepotrzebne

        # 3. Kontrola kodu otworu (ISO 15). Działa tylko dla oznaczeń metrycznych -
        #    dla calowych bore_from_symbol świadomie zwraca None (patrz bearing_types).
        oczekiwany = bearing_types.bore_from_symbol(symbol)
        if oczekiwany is not None and b.d is not None and abs(b.d - oczekiwany) > 1.0:
            wynik.uwagi.append(Uwaga(
                b.id, symbol, "otwor_nie_pasuje_do_oznaczenia", KRYTYCZNA,
                f"z oznaczenia wynika otwór {oczekiwany:g} mm, a wpisano {b.d:g} mm - "
                f"albo symbol, albo wymiar jest błędny"))

        # 4. Typ nie do rozpoznania z oznaczenia. To NIE jest błąd - tak wygląda
        #    numeracja calowa i oznaczenia producenckie - ale takie pozycje warto
        #    obejrzeć, bo program nie ma jak ich sprawdzić.
        if bearing_types.classify_symbol(symbol) is None and not b.do_weryfikacji:
            wynik.uwagi.append(Uwaga(
                b.id, symbol, "symbol_nierozpoznany", INFORMACJA,
                "oznaczenia nie da się rozpoznać regułami ISO (numeracja calowa albo "
                "producencka) - warto oznaczyć do sprawdzenia",
                {"do_weryfikacji": True}))

        # 5. Brak średnicy zewnętrznej blokuje rachunek pojemności półki.
        if b.D is None:
            wynik.uwagi.append(Uwaga(
                b.id, symbol, "brak_srednicy", OSTRZEZENIE,
                "brak średnicy zewnętrznej - bez niej nie policzymy, ile miejsca zajmuje"))

    return wynik


def propozycje_ai(wynik: Wynik) -> list[tuple[str, str]]:
    """Pyta modele o wymiary pozycji, których nie ma w katalogu.

    Wynik jest WYŁĄCZNIE do przeczytania przez człowieka - nie trafia do bazy nawet
    przy --zastosuj. Modele bywają zgodne i bywają zgodnie w błędzie (realny przypadek:
    dla serii ES podawały szerokości 38, 19 i 20 mm dla kolejnych rozmiarów tej samej
    serii), a błędny wymiar w magazynie wygląda potem tak samo jak prawdziwy.
    """
    try:
        import ai_assist
    except ImportError:
        return []
    if not ai_assist.is_available():
        return []

    # Pierwszeństwo mają pozycje oznaczone RĘCZNIE ptaszkiem "do sprawdzenia" - to
    # użytkownik stoi przy regale i wie, co jest nieczytelne. Reszta to te, przy
    # których audyt sam czegoś nie umiał rozstrzygnąć.
    oznaczone = {b.symbol.strip() for b in db.do_weryfikacji()}
    z_audytu = {u.symbol for u in wynik.uwagi
                if u.rodzaj in ("brak_srednicy", "symbol_nierozpoznany")}
    symbole = sorted(oznaczone) + sorted(z_audytu - oznaczone)
    propozycje = []
    for s in symbole:
        try:
            r = ai_assist.lookup(s)
        except Exception as e:                       # brak sieci, limit, cokolwiek
            propozycje.append((s, f"zapytanie nieudane: {e}"))
            continue
        if r.znaleziono:
            gwiazdka = "*" if s in oznaczone else " "
            propozycje.append((s, f"{gwiazdka} {r.d:g} x {r.D:g} x {r.B:g} mm "
                                   f"(zgodnych {r.zgodnych}/{r.odpytanych}) - {r.uwaga}"))
        else:
            gwiazdka = "*" if s in oznaczone else " "
            propozycje.append((s, f"{gwiazdka} " + (r.uwaga or "modele nie znają tego oznaczenia")))
    return propozycje


def zastosuj(wynik: Wynik) -> int:
    """Zapisuje TYLKO poprawki pewne, czyli wynikające z katalogu. Zwraca ich liczbę."""
    zmienionych = 0
    for u in wynik.uwagi:
        if not u.poprawka:
            continue
        b = db.get_bearing(u.bearing_id)
        if b is None:
            continue
        if "do_weryfikacji" in u.poprawka:
            db.oznacz_do_weryfikacji(b.id, bool(u.poprawka["do_weryfikacji"]))
            zmienionych += 1
            continue
        # reczny_przydzial=True celowo: poprawka wymiarów nie może PRZENIEŚĆ łożyska
        # na inną półkę, bo ono fizycznie leży tam, gdzie leży.
        db.update_bearing(
            b.id, symbol=b.symbol, typ=u.poprawka.get("typ", b.typ),
            d=u.poprawka.get("d", b.d), D=u.poprawka.get("D", b.D), B=u.poprawka.get("B", b.B),
            ilosc=b.ilosc, zrodlo=b.zrodlo, uwagi=b.uwagi,
            regal_id=b.regal_id, reczny_przydzial=True,
        )
        zmienionych += 1
    return zmienionych


def lista_oznaczonych() -> str:
    """Robocza lista pozycji z ptaszkiem - wszystko, co potrzebne do rozpoznania serii."""
    oznaczone = db.do_weryfikacji()
    if not oznaczone:
        return "Nic nie czeka na weryfikację."

    wezly = {s.id: s for s in db.get_shelves()}
    linie = [f"Do sprawdzenia: {len(oznaczone)} pozycji.\n"]
    for b in oznaczone:
        wymiary = " x ".join(f"{v:g}" if v is not None else "?" for v in (b.d, b.D, b.B))
        linie.append(f"  {b.symbol}")
        linie.append(f"      wymiary:     {wymiary} mm    ilość: {b.ilosc} szt.")
        linie.append(f"      typ wpisany: {b.typ or '(brak)'}")
        linie.append(f"      lokalizacja: {db.shelf_path(b.regal_id, wezly) or 'bez lokalizacji'}")
        linie.append(f"      wątpliwość:  {b.uwagi or '(nie opisano)'}")
        rozpoznany = bearing_types.classify_symbol(b.symbol)
        otwor = bearing_types.bore_from_symbol(b.symbol)
        linie.append(f"      reguły mówią: typ={rozpoznany or 'nie wiem'}, "
                      f"otwór={f'{otwor:g} mm' if otwor else 'nie wiem'}")
        linie.append("")
    return "\n".join(linie)


def raport(wynik: Wynik, propozycje: list[tuple[str, str]] | None = None) -> str:
    linie = [f"Sprawdzono {wynik.sprawdzonych} pozycji."]
    oznaczone = db.do_weryfikacji()
    if oznaczone:
        linie.append(f"\nOznaczone przez Ciebie do sprawdzenia ({len(oznaczone)}):")
        for b in oznaczone:
            wymiary = " x ".join(f"{v:g}" if v is not None else "?" for v in (b.d, b.D, b.B))
            linie.append(f"    {b.symbol:10} {wymiary:22} {b.uwagi or '(bez opisu)'}")
        linie.append("")
    liczniki = wynik.wagi()
    if not wynik.uwagi:
        linie.append("Nic nie budzi wątpliwości.")
        return "\n".join(linie)

    linie.append(f"Uwag: {liczniki[KRYTYCZNA]} krytycznych, "
                  f"{liczniki[OSTRZEZENIE]} ostrzeżeń, {liczniki[INFORMACJA]} informacji.\n")
    kolejnosc = {KRYTYCZNA: 0, OSTRZEZENIE: 1, INFORMACJA: 2}
    for u in sorted(wynik.uwagi, key=lambda x: (kolejnosc[x.waga], x.symbol)):
        znacznik = "[popr.]" if u.poprawka else "      "
        linie.append(f"  {znacznik} [{u.waga:11}] {u.symbol:10} {u.opis}")

    do_poprawy = sum(1 for u in wynik.uwagi if u.poprawka)
    if do_poprawy:
        linie.append(f"\n{do_poprawy} uwag ma gotową poprawkę z katalogu "
                      f"(oznaczone [popr.]). Zapisz je: python audyt.py --zastosuj")

    if propozycje:
        linie.append("\nPropozycje modeli AI - DO PRZECZYTANIA, NIE DO ZAPISANIA")
        linie.append("(* = pozycja oznaczona przez Ciebie ptaszkiem „do sprawdzenia”):")
        for symbol, opis in propozycje:
            linie.append(f"    {symbol:10} {opis}")
    return "\n".join(linie)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audyt danych w bazie łożysk.")
    parser.add_argument("--oznaczone", action="store_true",
                         help="pokaż tylko pozycje z ptaszkiem \"do sprawdzenia\"")
    parser.add_argument("--zastosuj", action="store_true",
                         help="zapisz poprawki pewne (wyłącznie te z katalogu)")
    parser.add_argument("--ai", action="store_true",
                         help="dopytaj modele o pozycje spoza katalogu (tylko raport)")
    args = parser.parse_args()

    db.init_db()
    if args.oznaczone:
        print(lista_oznaczonych())
        return 0

    wynik = audyt()
    propozycje = propozycje_ai(wynik) if args.ai else None
    print(raport(wynik, propozycje))

    if args.zastosuj:
        ile = zastosuj(wynik)
        print(f"\nZapisano {ile} poprawek z katalogu. Propozycji AI nie zapisano.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
