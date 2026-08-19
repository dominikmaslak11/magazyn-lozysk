"""Wysyłanie wiadomości z magazynu: e-mail, WhatsApp, SMS.

Po co: magazyn wie, czego brakuje i ile domówić, ale ta wiedza siedzi na serwerze,
a zamawia ktoś inny - tata, dziadek, dostawca. Ten moduł zamienia stan magazynu
w wiadomość, którą da się wysłać człowiekowi.

TRZY DROGI, świadomie różnej wagi:

  * E-MAIL (SMTP) - działa od razu, za darmo, dowolna długość treści. Wymaga hasła
    aplikacji do skrzynki (Gmail: konto -> bezpieczeństwo -> hasła do aplikacji).
    Do list zakupów i zamówień - czyli tam, gdzie treść jest dłuższa niż zdanie.

  * WHATSAPP przez link wa.me - NIE wymaga żadnego API, konta firmowego ani opłat.
    Program buduje link z gotową treścią, kliknięcie otwiera WhatsAppa z wpisaną
    wiadomością, a Ty naciskasz "wyślij". Świadomie NIE używamy bibliotek typu
    whatsapp-web.js: łamią regulamin WhatsAppa i realnie kończą się blokadą numeru,
    a numer prywatny to zły zakład o wygodę.

  * SMS - jedyna droga PŁATNA i jedyna wymagająca konta u zewnętrznego dostawcy.
    Sensowna tylko dla krótkich alarmów do kogoś, kto nie używa WhatsAppa.

Dane dostępowe leżą w ~/.lozyska_data/ (poza repozytorium, chmod 600) - tak samo jak
klucze do modeli AI. Nigdy nie trafiają do kodu ani do gita.
"""

from __future__ import annotations

import argparse
import json
import smtplib
import sys
import urllib.parse
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

import database as db

KATALOG_DANYCH = Path.home() / ".lozyska_data"
SMTP_CONFIG = KATALOG_DANYCH / "smtp.json"


@dataclass
class UstawieniaSmtp:
    host: str
    port: int
    user: str
    haslo: str
    nadawca: str

    @classmethod
    def wczytaj(cls) -> "UstawieniaSmtp | None":
        if not SMTP_CONFIG.exists():
            return None
        try:
            d = json.loads(SMTP_CONFIG.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        brakujace = [k for k in ("host", "port", "user", "haslo") if not d.get(k)]
        if brakujace:
            return None
        return cls(d["host"], int(d["port"]), d["user"], d["haslo"],
                    d.get("nadawca") or d["user"])


# ----------------------------------------------------------------- treści ----

def tresc_brakow() -> str:
    """Czego brakuje i ile domówić - prosto z progów magazynowych.

    Formułujemy to jak prośbę do człowieka, a nie jak zrzut z bazy: odbiorca ma
    wiedzieć, co kupić i ile, bez tłumaczenia, co znaczą kolumny.
    """
    alerty = [a for a in db.alerty_stanu() if a.poziom in ("brak", "pilne")]
    if not alerty:
        return ""

    linie = ["Cześć! Kończą się łożyska w magazynie - proszę o dopisanie do listy zamówień:", ""]
    for a in alerty:
        opis = f" ({a.uwagi})" if a.uwagi else ""
        linie.append(f"- {a.symbol}{opis}: zostało {a.ilosc} szt., domówić {a.brakuje} szt.")
    linie += ["", "Nie ma pośpiechu z samym zamówieniem, ważne żeby nie umknęło.",
              "", "Wiadomość wygenerowana automatycznie z Magazynu Łożysk."]
    return "\n".join(linie)


def tresc_z_pliku(sciezka: Path) -> str:
    """Treść z pliku - np. gotowej listy zakupów z katalogu warsztat/."""
    return sciezka.read_text(encoding="utf-8")


# ------------------------------------------------------------------ drogi ----

def link_whatsapp(tresc: str, numer: str = "") -> str:
    """Link, który otwiera WhatsAppa z wpisaną treścią. Wysyłkę zatwierdza człowiek.

    Bez API, bez konta firmowego, bez opłat i bez ryzyka blokady numeru. `numer`
    w formacie międzynarodowym bez plusa i spacji (48601234567); pusty = WhatsApp
    zapyta o odbiorcę.
    """
    numer = "".join(c for c in numer if c.isdigit())
    return f"https://wa.me/{numer}?text={urllib.parse.quote(tresc)}"


def wyslij_email(do: str, temat: str, tresc: str, na_sucho: bool = False) -> str:
    """Wysyła e-mail przez SMTP. `na_sucho` pokazuje, co by poszło, i nic nie wysyła."""
    ust = UstawieniaSmtp.wczytaj()
    if ust is None:
        return (f"Brak konfiguracji SMTP. Utwórz {SMTP_CONFIG} wg wzoru:\n"
                f'  {{"host": "smtp.gmail.com", "port": 587, "user": "adres@gmail.com",\n'
                f'   "haslo": "haslo-aplikacji-16-znakow", "nadawca": "adres@gmail.com"}}\n'
                f"Potem: chmod 600 {SMTP_CONFIG}")

    wiadomosc = EmailMessage()
    wiadomosc["From"] = ust.nadawca
    wiadomosc["To"] = do
    wiadomosc["Subject"] = temat
    wiadomosc.set_content(tresc)

    if na_sucho:
        return (f"[PRÓBA NA SUCHO - nic nie wysłano]\n"
                f"Od:     {ust.nadawca}\nDo:     {do}\nTemat:  {temat}\n"
                f"Serwer: {ust.host}:{ust.port}\n\n{tresc}")

    with smtplib.SMTP(ust.host, ust.port, timeout=20) as s:
        s.starttls()
        s.login(ust.user, ust.haslo)
        s.send_message(wiadomosc)
    return f"Wysłano do {do}: {temat!r}"


# -------------------------------------------------------------------- CLI ----

def main() -> int:
    p = argparse.ArgumentParser(description="Wyślij wiadomość z magazynu łożysk.")
    zrodlo = p.add_mutually_exclusive_group(required=True)
    zrodlo.add_argument("--braki", action="store_true",
                         help="treść: czego brakuje i ile domówić (z progów magazynowych)")
    zrodlo.add_argument("--plik", type=Path, help="treść: zawartość pliku, np. listy zakupów")

    p.add_argument("--email", help="adres odbiorcy")
    p.add_argument("--temat", default="Magazyn Łożysk", help="temat wiadomości")
    p.add_argument("--whatsapp", nargs="?", const="", metavar="NUMER",
                    help="wypisz link otwierający WhatsAppa z gotową treścią")
    p.add_argument("--na-sucho", action="store_true",
                    help="pokaż, co poszłoby, ale NIE wysyłaj")
    args = p.parse_args()

    db.init_db()
    if args.braki:
        tresc = tresc_brakow()
        if not tresc:
            print("Nic nie brakuje - żadna pozycja nie jest poniżej minimum.")
            return 0
    else:
        if not args.plik.exists():
            print(f"Nie ma pliku {args.plik}")
            return 1
        tresc = tresc_z_pliku(args.plik)

    if not args.email and args.whatsapp is None:
        print(tresc)
        return 0

    if args.whatsapp is not None:
        print("Link do WhatsAppa (otwórz w przeglądarce, treść będzie już wpisana):\n")
        print(link_whatsapp(tresc, args.whatsapp))
        print()

    if args.email:
        print(wyslij_email(args.email, args.temat, tresc, na_sucho=args.na_sucho))
    return 0


if __name__ == "__main__":
    sys.exit(main())
