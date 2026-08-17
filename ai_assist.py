"""
Podpowiedzi wymiarów łożysk od modeli AI (Claude, Gemini, DeepSeek, OpenAI).

PO CO TO JEST
Wbudowany katalog ma ~250 rozmiarów. Dla oznaczeń spoza katalogu dotąd zostawał
scraping wyszukiwarki, który potrafi zwrócić wymiary ZUPEŁNIE innego łożyska
(realny przypadek: dla 6204 przychodziło 60x80 zamiast 20x47). Modele językowe
znają oznaczenia łożysk znacznie lepiej niż regex po HTML-u wyszukiwarki.

DLACZEGO TO NIE JEST NIEBEZPIECZNE
Model potrafi podać błędne wymiary z pełnym przekonaniem, a w magazynie zła liczba
jest gorsza niż jej brak. Dlatego KAŻDA odpowiedź przechodzi przez te same
zabezpieczenia co scraping (patrz bearing_types.dimensions_are_plausible):

  1. kod otworu z oznaczenia (ISO 15) - dla 6204 otwór MUSI mieć 20 mm,
  2. podstawowa geometria: 0 < d < D oraz B > 0,
  3. porównanie odpowiedzi kilku niezależnych modeli - zgodność dwóch z nich
     to znacznie mocniejsza przesłanka niż odpowiedź jednego.

Wynik jest zawsze PROPOZYCJĄ oznaczoną źródłem "ai" - nigdy nie zapisuje się sam.

PRYWATNOŚĆ I BEZPIECZEŃSTWO
  * Klucze leżą w ~/.lozyska_data/ai_keys.json (poza repo, chmod 600) i NIGDY nie
    trafiają na telefon - appka pyta własny serwer, serwer pyta modele.
  * Wysyłamy wyłącznie samo oznaczenie łożyska. Nigdy stanu magazynu, nazw regałów
    ani czegokolwiek innego z bazy.
  * Bez kluczy funkcja po prostu nie istnieje - reszta programu działa jak dotąd.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import database as db
from bearing_types import bore_from_symbol, classify_symbol, dimensions_are_plausible

KEYS_PATH = db.DB_DIR / "ai_keys.json"

# Krótkie limity: odpowiedź to kilka liczb, nie esej. Chroni przed kosztami i zwieszką.
MAX_TOKENS = 400
TIMEOUT_S = 25

# Model pytamy WYŁĄCZNIE o samo oznaczenie - żadnych danych z magazynu.
SYSTEM_PROMPT = (
    "Jesteś ekspertem od łożysk tocznych. Podajesz wymiary katalogowe łożyska "
    "na podstawie jego oznaczenia. Odpowiadasz wyłącznie danymi, bez komentarzy. "
    "Jeśli nie znasz danego oznaczenia albo nie masz pewności, ustaw pewnosc na "
    "\"niska\" i pozostaw wymiary puste - zmyślone wymiary są gorsze niż ich brak."
)

USER_PROMPT = (
    "Podaj wymiary katalogowe łożyska o oznaczeniu: {symbol}\n\n"
    "d = średnica wewnętrzna (otworu) w mm\n"
    "D = średnica zewnętrzna w mm\n"
    "B = szerokość/wysokość w mm\n"
    "typ = rodzaj konstrukcji po polsku (np. kulkowe zwykłe, stożkowe, walcowe, "
    "wahliwe baryłkowe, igiełkowe, oporowe, skośne, wstawkowe)"
)

# Schemat wymuszany po stronie API tam, gdzie się da (Claude/OpenAI/Gemini) -
# dzięki temu nie parsujemy prozy, tylko gotowy JSON.
ODPOWIEDZ_SCHEMA = {
    "type": "object",
    "properties": {
        "d": {"type": ["number", "null"]},
        "D": {"type": ["number", "null"]},
        "B": {"type": ["number", "null"]},
        "typ": {"type": ["string", "null"]},
        "pewnosc": {"type": "string", "enum": ["wysoka", "srednia", "niska"]},
    },
    "required": ["d", "D", "B", "typ", "pewnosc"],
    "additionalProperties": False,
}


@dataclass
class OdpowiedzModelu:
    dostawca: str
    d: float | None = None
    D: float | None = None
    B: float | None = None
    typ: str | None = None
    pewnosc: str = "niska"
    blad: str | None = None
    odrzucona: str | None = None   # powód odrzucenia przez walidację

    @property
    def ma_wymiary(self) -> bool:
        return self.d is not None and self.D is not None and self.B is not None


@dataclass
class WynikAI:
    symbol: str
    d: float | None = None
    D: float | None = None
    B: float | None = None
    typ: str | None = None
    zgodnych: int = 0                       # ile modeli podało ten sam wynik
    odpytanych: int = 0
    odpowiedzi: list[OdpowiedzModelu] = field(default_factory=list)
    uwaga: str = ""

    @property
    def znaleziono(self) -> bool:
        return self.d is not None and self.D is not None and self.B is not None


def load_keys() -> dict[str, str]:
    """Klucze API albo pusty słownik, gdy plik nie istnieje (funkcja wtedy nieaktywna)."""
    if not KEYS_PATH.exists():
        return {}
    try:
        dane = json.loads(KEYS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    return {k: v for k, v in dane.items() if isinstance(v, str) and v.strip()}


def is_available() -> bool:
    return bool(load_keys())


# ------------------------------------------------------------- dostawcy ----
# Każda funkcja zwraca surowy słownik z modelu albo rzuca wyjątek.

def _zapytaj_anthropic(klucz: str, symbol: str) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=klucz, timeout=TIMEOUT_S)
    resp = client.messages.create(
        model="claude-opus-5",
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": ODPOWIEDZ_SCHEMA}},
        messages=[{"role": "user", "content": USER_PROMPT.format(symbol=symbol)}],
    )
    # Klasyfikatory bezpieczeństwa mogą odmówić - wtedy content bywa pusty.
    if resp.stop_reason == "refusal":
        raise RuntimeError("model odmówił odpowiedzi")
    tekst = next((b.text for b in resp.content if b.type == "text"), "")
    return json.loads(tekst)


def _zapytaj_openai(klucz: str, symbol: str) -> dict:
    import requests

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {klucz}", "Content-Type": "application/json"},
        json={
            "model": "gpt-4o-mini",
            "max_tokens": MAX_TOKENS,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT.format(symbol=symbol)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "wymiary", "schema": ODPOWIEDZ_SCHEMA, "strict": True},
            },
        },
        timeout=TIMEOUT_S,
    )
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])


def _zapytaj_deepseek(klucz: str, symbol: str) -> dict:
    import requests

    r = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {klucz}", "Content-Type": "application/json"},
        json={
            "model": "deepseek-chat",
            "max_tokens": MAX_TOKENS,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT + " Zwróć obiekt JSON o polach: "
                    "d, D, B (liczby albo null), typ (tekst albo null), pewnosc "
                    "(\"wysoka\"/\"srednia\"/\"niska\")."},
                {"role": "user", "content": USER_PROMPT.format(symbol=symbol)},
            ],
        },
        timeout=TIMEOUT_S,
    )
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])


def _zapytaj_gemini(klucz: str, symbol: str) -> dict:
    import requests

    # Gemini nie przyjmuje typów unijnych (["number","null"]) - podajemy prostszy schemat.
    schemat = {
        "type": "object",
        "properties": {
            "d": {"type": "number"}, "D": {"type": "number"}, "B": {"type": "number"},
            "typ": {"type": "string"}, "pewnosc": {"type": "string"},
        },
        "required": ["pewnosc"],
    }
    r = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-3.6-flash:generateContent",
        headers={"x-goog-api-key": klucz, "Content-Type": "application/json"},
        json={
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": USER_PROMPT.format(symbol=symbol)}]}],
            "generationConfig": {
                "maxOutputTokens": MAX_TOKENS,
                "responseMimeType": "application/json",
                "responseSchema": schemat,
            },
        },
        timeout=TIMEOUT_S,
    )
    r.raise_for_status()
    return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])


_DOSTAWCY = {
    "anthropic": ("Claude", _zapytaj_anthropic),
    "gemini": ("Gemini", _zapytaj_gemini),
    "deepseek": ("DeepSeek", _zapytaj_deepseek),
    "openai": ("OpenAI", _zapytaj_openai),
}


def _liczba(wartosc) -> float | None:
    try:
        w = float(wartosc)
    except (TypeError, ValueError):
        return None
    return w if w > 0 else None


def _pytaj_jednego(dostawca: str, klucz: str, symbol: str) -> OdpowiedzModelu:
    nazwa, funkcja = _DOSTAWCY[dostawca]
    wynik = OdpowiedzModelu(dostawca=nazwa)
    try:
        surowe = funkcja(klucz, symbol)
    except Exception as e:                      # sieć, limit, zła odpowiedź - to nie ma wywracać całości
        wynik.blad = f"{type(e).__name__}: {e}"[:160]
        return wynik

    wynik.d = _liczba(surowe.get("d"))
    wynik.D = _liczba(surowe.get("D"))
    wynik.B = _liczba(surowe.get("B"))
    typ = surowe.get("typ")
    wynik.typ = typ.strip() if isinstance(typ, str) and typ.strip() else None
    pewnosc = surowe.get("pewnosc")
    wynik.pewnosc = pewnosc if pewnosc in ("wysoka", "srednia", "niska") else "niska"

    # TA SAMA walidacja co dla wyników z wyszukiwarki - model nie dostaje taryfy ulgowej.
    if wynik.ma_wymiary and not dimensions_are_plausible(symbol, wynik.d, wynik.D, wynik.B):
        oczekiwane = bore_from_symbol(symbol)
        wynik.odrzucona = (f"otwór powinien mieć ok. {oczekiwane:g} mm" if oczekiwane
                            else "wymiary niespójne geometrycznie")
        wynik.d = wynik.D = wynik.B = None
    return wynik


def lookup(symbol: str) -> WynikAI:
    """Pyta wszystkie skonfigurowane modele równolegle i uzgadnia odpowiedź.

    Przyjmujemy wymiary dopiero, gdy przejdą walidację. Zgodność dwóch niezależnych
    modeli podnosimy wyżej niż pojedynczą odpowiedź, nawet deklarowaną jako pewna.
    """
    symbol = (symbol or "").strip()
    wynik = WynikAI(symbol=symbol)
    if not symbol:
        wynik.uwaga = "Puste oznaczenie."
        return wynik

    klucze = load_keys()
    if not klucze:
        wynik.uwaga = "Podpowiedzi AI nieskonfigurowane (brak ~/.lozyska_data/ai_keys.json)."
        return wynik

    do_zapytania = [(d, k) for d, k in klucze.items() if d in _DOSTAWCY]
    wynik.odpytanych = len(do_zapytania)

    with ThreadPoolExecutor(max_workers=len(do_zapytania)) as pula:
        zadania = {pula.submit(_pytaj_jednego, d, k, symbol): d for d, k in do_zapytania}
        for zadanie in as_completed(zadania):
            wynik.odpowiedzi.append(zadanie.result())
    wynik.odpowiedzi.sort(key=lambda o: o.dostawca)

    poprawne = [o for o in wynik.odpowiedzi if o.ma_wymiary]
    if not poprawne:
        odrzucone = [o for o in wynik.odpowiedzi if o.odrzucona]
        if odrzucone:
            wynik.uwaga = ("Modele podały wymiary niepasujące do tego oznaczenia - odrzucone. "
                            f"({odrzucone[0].odrzucona})")
        else:
            wynik.uwaga = "Modele nie znają tego oznaczenia."
        return wynik

    # Uzgodnienie: najczęstszy zestaw wymiarów (0,1 mm tolerancji na zaokrąglenia).
    def klucz_wymiarow(o: OdpowiedzModelu) -> tuple:
        return (round(o.d, 1), round(o.D, 1), round(o.B, 1))

    licznik = Counter(klucz_wymiarow(o) for o in poprawne)
    najczestszy, ile = licznik.most_common(1)[0]
    zgodne = [o for o in poprawne if klucz_wymiarow(o) == najczestszy]

    wzorzec = zgodne[0]
    wynik.d, wynik.D, wynik.B = wzorzec.d, wzorzec.D, wzorzec.B
    wynik.zgodnych = ile
    # Typ wolimy z reguły ISO (deterministyczna) niż z modelu.
    wynik.typ = classify_symbol(symbol) or next((o.typ for o in zgodne if o.typ), None)

    if ile >= 2:
        wynik.uwaga = (f"{ile} niezależne modele podały te same wymiary i przeszły kontrolę "
                        "oznaczenia. Mimo to zweryfikuj suwmiarką przed zapisem.")
    else:
        wynik.uwaga = ("Tylko jeden model podał wymiary (pozostałe nie znały oznaczenia albo "
                        "się nie zgodziły). Traktuj jako wskazówkę - zmierz suwmiarką.")
    return wynik


# ============================================================ CZAT ============
#
# Asystent rozmowy o magazynie. Domyślnie Claude (najnowszy dostępny model), z
# możliwością przełączenia na pozostałych dostawców.
#
# Co dostaje model: pytanie użytkownika + ZWIĘZŁY spis magazynu (symbol, wymiary,
# ilość, regał). Bez tego asystent jest bezużyteczny ("czy mam coś 25x52?"), ale
# trzeba wiedzieć, że te dane wychodzą do zewnętrznej usługi - dlatego jest to
# jawnie opisane w UI i w README, a spis da się wyłączyć (bez_magazynu=True).

CZAT_MODELE = {
    "anthropic": "claude-opus-5",      # domyślny - najnowszy Claude
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-chat",
    "gemini": "gemini-3.6-flash",
}
CZAT_DOMYSLNY = "anthropic"
CZAT_MAX_TOKENS = 1200

CZAT_SYSTEM = (
    "Jesteś asystentem magazynu łożysk tocznych w warsztacie. Odpowiadasz po polsku, "
    "zwięźle i konkretnie, jak doświadczony mechanik - bez marketingowego lania wody.\n\n"
    "Zasady:\n"
    "- Gdy pytanie dotyczy stanu magazynu, opieraj się WYŁĄCZNIE na przekazanym spisie. "
    "Jeśli czegoś w nim nie ma, powiedz wprost, że tego nie ma.\n"
    "- Wymiary łożysk spoza spisu podawaj tylko wtedy, gdy jesteś ich pewien; w razie "
    "wątpliwości powiedz, że trzeba zmierzyć suwmiarką. Zmyślone wymiary są gorsze niż "
    "przyznanie się do niewiedzy.\n"
    "- Pamiętaj, że oznaczenie koduje otwór: dwie ostatnie cyfry x 5 mm "
    "(00/01/02/03 = 10/12/15/17 mm). Używaj tego do sprawdzania własnych odpowiedzi.\n"
    "- Nie proponuj zmian w magazynie jako faktów dokonanych - to użytkownik decyduje."
)


def _spis_magazynu(limit: int = 400) -> str:
    """Zwięzły spis stanu - tylko to, co potrzebne do odpowiedzi na pytania."""
    try:
        lozyska = db.get_bearings()
    except Exception:
        return "(nie udało się odczytać magazynu)"
    if not lozyska:
        return "Magazyn jest pusty."
    regaly = {s.id: s.nazwa for s in db.get_shelves()}
    linie = []
    for b in lozyska[:limit]:
        wym = f"{b.d or '?'}x{b.D or '?'}x{b.B or '?'}"
        linie.append(f"{b.symbol} | {wym} mm | {b.typ or '?'} | {b.ilosc} szt. | "
                      f"{regaly.get(b.regal_id, 'bez regału')}")
    tekst = "STAN MAGAZYNU (symbol | d x D x B | typ | ilość | regał):\n" + "\n".join(linie)

    # Podpowiedzi przełożenia liczy deterministyczna reguła (database.sugestie_przeniesien),
    # NIE model. Model dostaje gotową listę tylko po to, żeby ładnie o niej opowiedzieć -
    # dzięki temu nie zmyśli, że coś leży źle, i nie będzie za każdym razem mówił czegoś innego.
    try:
        sugestie = db.sugestie_przeniesien(min_sztuk=2)[:10]
    except Exception:
        sugestie = []
    if sugestie:
        tekst += ("\n\nWARTO PRZEŁOŻYĆ (wyliczone regułami, nie zgaduj tu nic od siebie;"
                   " wspominaj o tym tylko, gdy pytanie tego dotyczy):\n")
        tekst += "\n".join(
            f"{s.symbol} ({s.ilosc} szt.): {s.obecna} -> {s.sugerowana} [{s.powod}]"
            for s in sugestie)
    try:
        scalenia = db.sugestie_scalenia()[:5]
    except Exception:
        scalenia = []
    if scalenia:
        tekst += "\n\nDO SCALENIA (to samo łożysko w kilku wpisach/miejscach):\n"
        tekst += "\n".join(
            f"{s.symbol}: {' + '.join(str(w['ilosc']) + ' szt. w ' + w['lokalizacja'] for w in s.wpisy)}"
            f" -> razem {s.lacznie} szt. w {s.cel}" for s in scalenia)
    try:
        niezgodne = db.niezgodnosci_stanu()[:5]
    except Exception:
        niezgodne = []
    if niezgodne:
        tekst += ("\n\nWYMAGAJĄ PRZELICZENIA (stan bez pokrycia w dzienniku ruchów - "
                   "poinformuj o tym, ale NIE zgaduj, która liczba jest prawdziwa):\n")
        tekst += "\n".join(n.komunikat for n in niezgodne)
    return tekst


def _czat_anthropic(klucz: str, wiadomosci: list[dict], kontekst: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=klucz, timeout=60)
    resp = client.messages.create(
        model=CZAT_MODELE["anthropic"],
        max_tokens=CZAT_MAX_TOKENS,
        system=CZAT_SYSTEM + ("\n\n" + kontekst if kontekst else ""),
        messages=wiadomosci,
    )
    if resp.stop_reason == "refusal":
        return "Model odmówił odpowiedzi na to pytanie."
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def _czat_openai_zgodny(url: str, model: str, klucz: str,
                         wiadomosci: list[dict], kontekst: str) -> str:
    import requests

    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {klucz}", "Content-Type": "application/json"},
        json={
            "model": model, "max_tokens": CZAT_MAX_TOKENS,
            "messages": [{"role": "system", "content": CZAT_SYSTEM + ("\n\n" + kontekst if kontekst else "")}]
                        + wiadomosci,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _czat_gemini(klucz: str, wiadomosci: list[dict], kontekst: str) -> str:
    import requests

    tresci = [{"role": "model" if w["role"] == "assistant" else "user",
               "parts": [{"text": w["content"]}]} for w in wiadomosci]
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{CZAT_MODELE['gemini']}:generateContent",
        headers={"x-goog-api-key": klucz, "Content-Type": "application/json"},
        json={
            "system_instruction": {"parts": [{"text": CZAT_SYSTEM + ("\n\n" + kontekst if kontekst else "")}]},
            "contents": tresci,
            "generationConfig": {"maxOutputTokens": CZAT_MAX_TOKENS},
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def chat(wiadomosci: list[dict], dostawca: str | None = None,
          bez_magazynu: bool = False) -> dict:
    """Odpowiedź asystenta na rozmowę.

    `wiadomosci` to lista {"role": "user"/"assistant", "content": str}.
    Zwraca {"odpowiedz", "dostawca", "model", "blad"}.
    """
    klucze = load_keys()
    if not klucze:
        return {"blad": "Brak skonfigurowanych kluczy AI.", "odpowiedz": "",
                "dostawca": None, "model": None}

    wybrany = dostawca if dostawca in klucze else (
        CZAT_DOMYSLNY if CZAT_DOMYSLNY in klucze else next(iter(klucze)))
    klucz = klucze[wybrany]
    kontekst = "" if bez_magazynu else _spis_magazynu()

    czyste = [{"role": w.get("role", "user"), "content": str(w.get("content", ""))[:4000]}
              for w in wiadomosci if str(w.get("content", "")).strip()][-20:]
    if not czyste:
        return {"blad": "Pusta wiadomość.", "odpowiedz": "", "dostawca": wybrany,
                "model": CZAT_MODELE.get(wybrany)}

    try:
        if wybrany == "anthropic":
            tekst = _czat_anthropic(klucz, czyste, kontekst)
        elif wybrany == "gemini":
            tekst = _czat_gemini(klucz, czyste, kontekst)
        elif wybrany == "deepseek":
            tekst = _czat_openai_zgodny("https://api.deepseek.com/chat/completions",
                                         CZAT_MODELE["deepseek"], klucz, czyste, kontekst)
        else:
            tekst = _czat_openai_zgodny("https://api.openai.com/v1/chat/completions",
                                         CZAT_MODELE["openai"], klucz, czyste, kontekst)
    except Exception as e:
        return {"blad": f"{type(e).__name__}: {e}"[:200], "odpowiedz": "",
                "dostawca": wybrany, "model": CZAT_MODELE.get(wybrany)}

    return {"odpowiedz": tekst, "dostawca": wybrany,
            "model": CZAT_MODELE.get(wybrany), "blad": None}
