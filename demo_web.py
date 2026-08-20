"""Pokaz działania aplikacji webowej — prowadzony automatycznie w Chrome.

Po co: pokazywanie na żywo kończy się szukaniem zakładki i literówkami w polu
wyszukiwania. Ten skrypt przechodzi tę samą ścieżkę za każdym razem, z opisem
na głos i pauzami, więc można mówić zamiast klikać.

    python demo_web.py                # pokaz na serwerze produkcyjnym
    python demo_web.py --adres http://localhost:8420
    python demo_web.py --tempo 3      # wolniej, jeśli ktoś zadaje pytania
    python demo_web.py --zrzuty       # zapisz zrzuty do warsztat/pokaz/

Okno zostaje otwarte po zakończeniu — można dalej klikać ręcznie.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

ADRES_DOMYSLNY = "http://100.94.180.125:8420"
TOKEN_PLIK = Path.home() / ".lozyska_data" / "token.txt"
ZRZUTY = Path(__file__).resolve().parent / "warsztat" / "pokaz"

# Ile sekund trwa jeden "krok" pokazu. Celowo dłużej niż potrzeba technicznie -
# widz musi zdążyć przeczytać, co się zmieniło na ekranie.
TEMPO = 2.0


class Pokaz:
    def __init__(self, adres: str, tempo: float, zrzuty: bool):
        self.adres = adres.rstrip("/")
        self.tempo = tempo
        self.zrzuty = zrzuty
        self.krok = 0
        opcje = Options()
        opcje.add_argument("--window-size=1500,950")
        # Bez tego Chrome zamyka się razem ze skryptem, a chcemy zostawić okno.
        opcje.add_experimental_option("detach", True)
        opcje.add_argument("--disable-infobars")
        opcje.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.d = webdriver.Chrome(options=opcje)
        self.czekaj = WebDriverWait(self.d, 15)

    # ------------------------------------------------------------ pomocnicze ----

    def powiedz(self, tekst: str, pauza: float = 1.0) -> None:
        self.krok += 1
        print(f"\n[{self.krok}] {tekst}")
        time.sleep(self.tempo * pauza)

    def zrzut(self, nazwa: str) -> None:
        if not self.zrzuty:
            return
        ZRZUTY.mkdir(parents=True, exist_ok=True)
        sciezka = ZRZUTY / f"{self.krok:02d}-{nazwa}.png"
        self.d.save_screenshot(str(sciezka))
        print(f"      zrzut: {sciezka.name}")

    def klik(self, selektor: str) -> None:
        el = self.czekaj.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selektor)))
        self.d.execute_script("arguments[0].scrollIntoView({block:'center'})", el)
        time.sleep(0.3)
        el.click()

    def wpisz(self, selektor: str, tekst: str, znak_po_znaku: bool = True) -> None:
        """Pisze wolno, żeby na pokazie było widać, co się wpisuje."""
        el = self.czekaj.until(EC.presence_of_element_located((By.CSS_SELECTOR, selektor)))
        el.clear()
        if znak_po_znaku:
            for z in tekst:
                el.send_keys(z)
                time.sleep(0.06)
        else:
            el.send_keys(tekst)

    # ---------------------------------------------------------------- sceny ----

    def logowanie(self) -> None:
        self.powiedz(f"Otwieram aplikację: {self.adres}")
        self.d.get(f"{self.adres}/login")
        time.sleep(1)

        if "login" not in self.d.current_url:
            print("      (sesja już aktywna, logowanie pominięte)")
            return

        token = TOKEN_PLIK.read_text().strip() if TOKEN_PLIK.exists() else ""
        if not token:
            print(f"      BRAK TOKENU w {TOKEN_PLIK} - zaloguj się ręcznie")
            input("      naciśnij Enter, gdy się zalogujesz...")
            return

        self.powiedz("Logowanie tokenem. Aplikacja nie jest wystawiona do internetu, "
                      "ale i tak ma własną autoryzację")
        self.wpisz("input[name='token']", token, znak_po_znaku=False)
        self.zrzut("logowanie")
        self.d.find_element(By.CSS_SELECTOR, "form").submit()
        self.czekaj.until(EC.presence_of_element_located((By.ID, "bearingsGrid")))

    def lista_lozysk(self) -> None:
        self.powiedz("Lista łożysk. Każda pozycja ma symbol, wymiary, typ i lokalizację "
                      "z pełną ścieżką", pauza=1.5)
        self.zrzut("lista")

        self.powiedz("Na górze pasek podpowiedzi wyliczonych przez serwer: duplikaty, "
                      "pozycje do sprawdzenia, zawartość buforów", pauza=1.5)

    def wyszukiwanie(self) -> None:
        self.powiedz("Wyszukiwanie po symbolu")
        self.wpisz("#searchInput", "6203")
        time.sleep(self.tempo)
        self.zrzut("szukanie-symbol")

        self.powiedz("To samo pole przyjmuje WYMIARY. Wpisuję 25x52 - szuka łożyska "
                      "o takim otworze i średnicy, z tolerancją", pauza=1.2)
        self.wpisz("#searchInput", "25x52")
        time.sleep(self.tempo)
        self.zrzut("szukanie-wymiary")

        self.powiedz("Szuka też po uwagach - wpisując zastosowanie znajdziesz część")
        self.wpisz("#searchInput", "corncracker")
        time.sleep(self.tempo)
        self.zrzut("szukanie-uwagi")

        self.wpisz("#searchInput", "", znak_po_znaku=False)
        time.sleep(0.8)

    def rozpoznawanie_typu(self) -> None:
        self.powiedz("Dodawanie łożyska. Kluczowa rzecz: typ rozpoznaje się "
                      "z samego oznaczenia, bez internetu", pauza=1.2)
        self.klik("#addBearingBtn")
        time.sleep(0.8)

        for symbol, opis in (("6205", "kulkowe zwykłe"),
                              ("EX208", "wstawkowe SNR - inne niż UC208 o tych samych 40x80"),
                              ("RAE35", "INA - tu liczba to wprost otwór w milimetrach"),
                              ("37431A", "calowe Timkena - program mówi 'nie wiem' zamiast zgadywać")):
            self.powiedz(f"Wpisuję {symbol} - {opis}")
            self.wpisz("#f_symbol", symbol)
            time.sleep(self.tempo)
            typ = self.d.find_element(By.ID, "f_typ").get_attribute("value")
            print(f"      rozpoznany typ: {typ or '(brak - nieznane oznaczenie)'}")
            self.zrzut(f"typ-{symbol}")

        self.powiedz("Zamykam bez zapisywania")
        self.klik("#btnCancelBearing")
        time.sleep(0.8)

    def regaly(self) -> None:
        self.powiedz("Zakładka Regały: hierarchia lokalizacji z prawdziwymi wymiarami "
                      "półek i wyliczonym zapełnieniem", pauza=1.5)
        self.klik("[data-view='shelves']")
        time.sleep(self.tempo)
        self.zrzut("regaly")

    def asystent(self) -> None:
        self.powiedz("Zakładka Asystent: pytania o magazyn w języku naturalnym. "
                      "Klucze API zostają na serwerze, nigdy nie trafiają na telefon", pauza=1.5)
        self.klik("[data-view='asystent']")
        time.sleep(self.tempo)
        self.zrzut("asystent")

    def dane(self) -> None:
        self.powiedz("Zakładka Dane: kopie zapasowe, dziennik ruchów magazynowych, "
                      "import i eksport", pauza=1.5)
        self.klik("#dataTabBtn")
        time.sleep(self.tempo)
        self.zrzut("dane")

    def zakoncz(self) -> None:
        self.powiedz("Koniec pokazu. Okno zostaje otwarte.", pauza=0.5)
        self.klik("[data-view='bearings']")


def main() -> int:
    p = argparse.ArgumentParser(description="Pokaz aplikacji webowej Magazyn Łożysk.")
    p.add_argument("--adres", default=ADRES_DOMYSLNY)
    p.add_argument("--tempo", type=float, default=TEMPO,
                    help="mnożnik czasu na krok (domyślnie 2 s)")
    p.add_argument("--zrzuty", action="store_true", help="zapisuj zrzuty ekranu")
    args = p.parse_args()

    pokaz = Pokaz(args.adres, args.tempo, args.zrzuty)
    try:
        pokaz.logowanie()
        pokaz.lista_lozysk()
        pokaz.wyszukiwanie()
        pokaz.rozpoznawanie_typu()
        pokaz.regaly()
        pokaz.asystent()
        pokaz.dane()
        pokaz.zakoncz()
    except Exception as e:
        print(f"\nBŁĄD na kroku {pokaz.krok}: {type(e).__name__}: {e}")
        pokaz.zrzut("blad")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
