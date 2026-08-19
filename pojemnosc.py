"""Ile łożysk zmieści się na półce i ile miejsca już zajmują.

Po co osobny moduł: dobór lokalizacji opierał się dotąd na WYMYŚLONYCH zakresach
średnic ("regał 8 to 30-42 mm"), które nie odpowiadały niczemu w rzeczywistości.
Odkąd znamy prawdziwe wymiary półek, o tym, czy coś się zmieści, może decydować
rachunek zamiast konwencji.

ZAŁOŻENIA MODELU - świadomie zgrubne, bo dokładne pakowanie 2D byłoby przerostem
formy nad treścią przy magazynie tej wielkości, a i tak nikt nie układa łożysk
z dokładnością do milimetra:

  * Łożyska leżą PŁASKO. Zajmują wtedy kwadrat o boku równym średnicy zewnętrznej
    (okrąg wpisany w kwadrat), a nie stoją na obrzeżu - stojące się przewracają.
  * Sztuki tego samego oznaczenia układa się w STOS. Bez tego półka o prześwicie
    21 cm marnowałaby 95% wysokości na łożyska szerokie na 2 cm.
  * Stos może być najwyżej DWA RAZY wyższy niż szeroki. Łożyska to precyzyjne
    pierścienie, więc układają się współosiowo i stos jest stabilniejszy niż stos
    byle czego - ale przy wyciąganiu sztuki z sąsiedniego stosu smukła wieża i tak
    się przewraca, a użytkownik chce wyjmować łożyska "nie przewracając innych".
  * Między sąsiednimi pozycjami zostaje odstęp na rękę, a nad stosem zapas na
    chwyt i wyjęcie - inaczej rachunek pokazywałby półkę pełną w 100%, na której
    fizycznie nie da się nic wziąć.

Wszystkie wymiary w MILIMETRACH - tak jak wymiary łożysk w reszcie programu.
Interfejs pokazuje centymetry, bo w takich mierzy się regały miarą.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Odstęp między sąsiednimi pozycjami, żeby dało się włożyć rękę i wyjąć jedno
# łożysko bez ruszania sąsiadów.
ODSTEP_MM = 30.0

# Zapas nad stosem: tyle miejsca trzeba, żeby chwycić górne łożysko i je unieść.
REZERWA_NAD_STOSEM_MM = 50.0

# Ile razy stos może być wyższy niż szeroki. 1.0 (stos nie wyższy niż szeroki) było
# zbyt ostrożne i marnowało półki: dziesięć 6005 to zaledwie 12 cm przy 4.7 cm średnicy
# i taki stos stoi pewnie. To JEDNA liczba do zmiany, gdyby w praktyce okazało się,
# że stosy się przewracają (w dół) albo że spokojnie można wyżej (w górę).
MAKS_SMUKLOSC_STOSU = 2.0

# Straty na krawędziach: półka nie jest idealną siatką, przy ścianach i z przodu
# zostają nieużyteczne paski. 0.85 to zgrubna, celowo ostrożna wartość.
WSPOLCZYNNIK_UKLADU = 0.85

# Od tego zapełnienia półka jest zgłaszana jako ciasna. Nie 100%, bo długo przed
# zapełnieniem co do kwadratowego centymetra przestaje się dać cokolwiek wyjąć.
PROG_CIASNO = 0.85


@dataclass
class Pozycja:
    """Jedno oznaczenie łożyska na półce, po przeliczeniu na zajmowane miejsce."""
    symbol: str
    ilosc: int
    warstwy: int            # ile sztuk w jednym stosie
    stosy: int              # ile stosów trzeba postawić
    powierzchnia_mm2: float
    miesci_sie: bool
    powod: str = ""


@dataclass
class Obciazenie:
    """Zapełnienie jednej półki."""
    shelf_id: str
    nazwa: str
    powierzchnia_mm2: float          # użyteczna, po odjęciu strat na krawędziach
    zajete_mm2: float
    pozycje: list[Pozycja] = field(default_factory=list)
    niemieszczace: list[Pozycja] = field(default_factory=list)

    @property
    def procent(self) -> float:
        if self.powierzchnia_mm2 <= 0:
            return 0.0
        return 100.0 * self.zajete_mm2 / self.powierzchnia_mm2

    @property
    def wolne_mm2(self) -> float:
        return max(0.0, self.powierzchnia_mm2 - self.zajete_mm2)

    @property
    def ciasno(self) -> bool:
        return self.powierzchnia_mm2 > 0 and self.zajete_mm2 / self.powierzchnia_mm2 >= PROG_CIASNO

    @property
    def znane_wymiary(self) -> bool:
        return self.powierzchnia_mm2 > 0


def warstwy_w_stosie(D: float | None, B: float | None, wysokosc_mm: float | None) -> int:
    """Ile sztuk tego samego łożyska można bezpiecznie ułożyć jedna na drugiej.

    Zwraca 0, gdy łożysko nie mieści się na tej półce nawet pojedynczo.
    Ograniczają dwie rzeczy naraz: prześwit półki i stabilność stosu.
    """
    if not B or B <= 0:
        return 1 if not wysokosc_mm else 1
    if wysokosc_mm:
        dostepne = wysokosc_mm - REZERWA_NAD_STOSEM_MM
        if dostepne < B:
            return 0                      # nie wejdzie nawet jedna sztuka z zapasem na rękę
        z_wysokosci = int(dostepne // B)
    else:
        z_wysokosci = 1                   # nie znamy prześwitu - nie ryzykujemy stosu
    # Granica smukłości, żeby stos się nie przewracał przy sięganiu obok.
    ze_stabilnosci = max(1, int((D or 0) * MAKS_SMUKLOSC_STOSU // B)) if D else 1
    return max(1, min(z_wysokosci, ze_stabilnosci))


def powierzchnia_pozycji(symbol: str, D: float | None, B: float | None, ilosc: int,
                          szerokosc_mm: float | None, glebokosc_mm: float | None,
                          wysokosc_mm: float | None) -> Pozycja:
    """Miejsce zajmowane przez wszystkie sztuki jednego oznaczenia."""
    if ilosc <= 0:
        return Pozycja(symbol, ilosc, 0, 0, 0.0, True)
    if not D:
        # Bez średnicy zewnętrznej nie ma z czego liczyć. Mówimy o tym wprost,
        # zamiast podstawiać wymyśloną wartość i udawać, że rachunek się zgadza.
        return Pozycja(symbol, ilosc, 1, ilosc, 0.0, True, "brak średnicy zewnętrznej - nie policzono")

    bok = D + ODSTEP_MM
    if glebokosc_mm and bok > glebokosc_mm:
        return Pozycja(symbol, ilosc, 0, 0, 0.0, False,
                        f"średnica {D:g} mm nie mieści się w głębokości {glebokosc_mm / 10:g} cm")
    if szerokosc_mm and bok > szerokosc_mm:
        return Pozycja(symbol, ilosc, 0, 0, 0.0, False,
                        f"średnica {D:g} mm nie mieści się w szerokości {szerokosc_mm / 10:g} cm")

    warstwy = warstwy_w_stosie(D, B, wysokosc_mm)
    if warstwy == 0:
        return Pozycja(symbol, ilosc, 0, 0, 0.0, False,
                        f"szerokość łożyska {B:g} mm nie mieści się w prześwicie "
                        f"{(wysokosc_mm or 0) / 10:g} cm (z zapasem na rękę)")

    stosy = -(-ilosc // warstwy)          # zaokrąglenie w górę
    return Pozycja(symbol, ilosc, warstwy, stosy, stosy * bok * bok, True)


def obciazenie_polki(shelf_id: str, nazwa: str,
                      szerokosc_mm: float | None, glebokosc_mm: float | None,
                      wysokosc_mm: float | None,
                      lozyska: list[tuple[str, float | None, float | None, int]]) -> Obciazenie:
    """Zapełnienie półki przez podane łożyska: (symbol, D, B, ilość)."""
    if szerokosc_mm and glebokosc_mm:
        uzyteczna = szerokosc_mm * glebokosc_mm * WSPOLCZYNNIK_UKLADU
    else:
        uzyteczna = 0.0                   # nie znamy wymiarów - nie zgadujemy

    wynik = Obciazenie(shelf_id, nazwa, uzyteczna, 0.0)
    for symbol, D, B, ilosc in lozyska:
        p = powierzchnia_pozycji(symbol, D, B, ilosc, szerokosc_mm, glebokosc_mm, wysokosc_mm)
        if p.miesci_sie:
            wynik.pozycje.append(p)
            wynik.zajete_mm2 += p.powierzchnia_mm2
        else:
            wynik.niemieszczace.append(p)
    return wynik


def proponowany_podzial(wysokosc_mm: float, najwyzszy_stos_mm: float) -> tuple[int, float]:
    """Na ile półek warto podzielić wysoką, pustą przestrzeń i co ile centymetrów.

    Wysoka przestrzeń nad półką to zmarnowany magazyn: łożysko ma kilka centymetrów
    grubości, a stos wyżej niż szeroki i tak się przewraca. Zwraca (liczba półek,
    rozstaw w mm) dla rozstawu, który mieści najwyższy sensowny stos plus zapas na rękę.
    """
    potrzebny_rozstaw = najwyzszy_stos_mm + REZERWA_NAD_STOSEM_MM
    if potrzebny_rozstaw <= 0 or wysokosc_mm < potrzebny_rozstaw:
        return 1, wysokosc_mm
    ile = int(wysokosc_mm // potrzebny_rozstaw)
    return ile, wysokosc_mm / ile
