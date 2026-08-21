"""Nazwane tokeny — warstwa, która decyduje, kto wejdzie do magazynu.

Dlaczego akurat te testy: serwer jest wystawiony do internetu przez Tailscale Funnel
(telefon, który nie jest w tailnecie, musi się jakoś połączyć). Od tego momentu token
jest JEDYNĄ zaporą, więc każda pomyłka w tym pliku to otwarte drzwi albo zablokowany
dostęp wszystkim naraz.

Trzy rzeczy pilnowane najostrzej:
  * unieważnienie działa NATYCHMIAST, bez restartu usługi,
  * uszkodzony tokeny.json nie odcina właściciela (inaczej literówka = utrata dostępu),
  * plik z tokenami nie może podszyć się pod token właściciela.

CZEGO TE TESTY NIE SPRAWDZAJĄ - sprawdzone mutacjami kodu, nie założone:

  * Odporności na atak czasowy. Podmiana secrets.compare_digest na zwykłe ==
    NIE psuje żadnego testu, bo różnica jest wyłącznie w czasie odpowiedzi.
    Tego nie da się rzetelnie zmierzyć testem jednostkowym. Jeśli ktoś kiedyś
    "uprości" tam porównanie, testy tego nie zauważą - pilnuje tego tylko
    komentarz w server.py.
  * Odcięcia pustych wartości w _tokeny(). Ta osłona jest nieosiągalna z zewnątrz,
    bo _dopasuj_token odrzuca pusty token wcześniej. Zostaje jako druga warstwa,
    ale testy nie odróżnią jej usunięcia.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

KATALOG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG))

# Katalog danych na czas testów. Musi być ustawiony PRZED importem database/server,
# bo DB_DIR wylicza się raz, przy imporcie modułu.
os.environ.setdefault("LOZYSKA_DATA_DIR", tempfile.mkdtemp(prefix="lozyska_tokeny_"))

import database as db  # noqa: E402
import server  # noqa: E402
import tokeny  # noqa: E402

TOKEN_WLASCICIELA = "token-wlasciciela-do-testow"
TOKEN_TATY = "token-taty-do-testow"


@pytest.fixture(autouse=True)
def srodowisko(tmp_path, monkeypatch):
    """Świeży plik z tokenami i znany token właściciela na każdy test."""
    if not db.DB_PATH.exists():
        db.init_db()
    monkeypatch.setattr(server, "AUTH_TOKEN", TOKEN_WLASCICIELA)
    monkeypatch.setattr(server, "TOKENY_PATH", tmp_path / "tokeny.json")
    monkeypatch.setattr(tokeny, "TOKENY_PATH", tmp_path / "tokeny.json")
    return tmp_path


@pytest.fixture
def klient():
    return server.app.test_client()


def zapisz_tokeny(sciezka: Path, dane) -> None:
    sciezka.write_text(json.dumps(dane) if not isinstance(dane, str) else dane)


CHRONIONY = "/api/bearings"


class TestKtoWchodzi:
    def test_wlasciciel_naglowkiem(self, klient):
        r = klient.get(CHRONIONY, headers={"X-Auth-Token": TOKEN_WLASCICIELA})
        assert r.status_code == 200

    def test_urzadzenie_naglowkiem(self, klient, srodowisko):
        zapisz_tokeny(srodowisko / "tokeny.json", {"tata": TOKEN_TATY})
        r = klient.get(CHRONIONY, headers={"X-Auth-Token": TOKEN_TATY})
        assert r.status_code == 200

    def test_urzadzenie_przez_bearer(self, klient, srodowisko):
        # Appka Android używa X-Auth-Token, ale Bearer musi działać tak samo -
        # inaczej skrypty i curl zachowywałyby się inaczej niż telefon.
        zapisz_tokeny(srodowisko / "tokeny.json", {"tata": TOKEN_TATY})
        r = klient.get(CHRONIONY, headers={"Authorization": f"Bearer {TOKEN_TATY}"})
        assert r.status_code == 200

    def test_zmyslony_token_odrzucony(self, klient):
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": "nie-ten"}).status_code == 401

    def test_brak_tokenu_odrzucony(self, klient):
        assert klient.get(CHRONIONY).status_code == 401

    def test_pusty_token_odrzucony(self, klient):
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": ""}).status_code == 401

    def test_prefiks_tokenu_nie_wystarczy(self, klient):
        # compare_digest porównuje całość; fragment nie może przejść.
        czesc = TOKEN_WLASCICIELA[:-1]
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": czesc}).status_code == 401

    def test_wersja_dostepna_bez_tokenu(self, klient):
        # Appka sprawdza zgodność wersji ZANIM się uwierzytelni - to świadomy wyjątek.
        assert klient.get("/api/version").status_code == 200


class TestUniewaznianieNaZywo:
    """Sedno modelu: odebranie dostępu nie może wymagać restartu usługi."""

    def test_uniewaznienie_dziala_natychmiast(self, klient, srodowisko):
        plik = srodowisko / "tokeny.json"
        zapisz_tokeny(plik, {"tata": TOKEN_TATY})
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": TOKEN_TATY}).status_code == 200

        zapisz_tokeny(plik, {})  # tak wygląda plik po tokeny.py --uniewaznij
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": TOKEN_TATY}).status_code == 401

    def test_dodanie_dziala_natychmiast(self, klient, srodowisko):
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": TOKEN_TATY}).status_code == 401
        zapisz_tokeny(srodowisko / "tokeny.json", {"tata": TOKEN_TATY})
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": TOKEN_TATY}).status_code == 200

    def test_uniewaznienie_urzadzenia_nie_rusza_wlasciciela(self, klient, srodowisko):
        plik = srodowisko / "tokeny.json"
        zapisz_tokeny(plik, {"tata": TOKEN_TATY})
        zapisz_tokeny(plik, {})
        r = klient.get(CHRONIONY, headers={"X-Auth-Token": TOKEN_WLASCICIELA})
        assert r.status_code == 200, "unieważnienie telefonu odcięło właściciela"


class TestPlikNieMozeZablokowacDostepu:
    """Uszkodzony albo dziwny tokeny.json nie może zamknąć drzwi właścicielowi."""

    def test_brak_pliku(self, klient):
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": TOKEN_WLASCICIELA}).status_code == 200

    def test_uszkodzony_json(self, klient, srodowisko):
        (srodowisko / "tokeny.json").write_text("{to nie jest json")
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": TOKEN_WLASCICIELA}).status_code == 200

    def test_json_nie_jest_slownikiem(self, klient, srodowisko):
        (srodowisko / "tokeny.json").write_text('["lista", "zamiast", "slownika"]')
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": TOKEN_WLASCICIELA}).status_code == 200

    def test_pusty_plik(self, klient, srodowisko):
        (srodowisko / "tokeny.json").write_text("")
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": TOKEN_WLASCICIELA}).status_code == 200


class TestSmieciWPliku:
    def test_pusta_wartosc_nie_daje_dostepu(self, klient, srodowisko):
        # Gdyby pusty string trafił do zbioru, żądanie bez tokenu mogłoby przejść.
        zapisz_tokeny(srodowisko / "tokeny.json", {"puste": "", "spacje": "   "})
        assert klient.get(CHRONIONY).status_code == 401
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": ""}).status_code == 401
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": "   "}).status_code == 401

    def test_wartosc_nie_bedaca_tekstem_jest_pomijana(self, klient, srodowisko):
        zapisz_tokeny(srodowisko / "tokeny.json", {"liczba": 12345, "null": None,
                                                     "tata": TOKEN_TATY})
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": "12345"}).status_code == 401
        # a poprawny wpis obok śmieci nadal działa
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": TOKEN_TATY}).status_code == 200

    def test_plik_nie_moze_podszyc_sie_pod_wlasciciela(self, klient, srodowisko):
        # Wpis o nazwie 'wlasciciel' w tokeny.json nie może przesłonić token.txt.
        zapisz_tokeny(srodowisko / "tokeny.json", {server.WLASCICIEL: "podszywka"})
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": "podszywka"}).status_code == 401
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": TOKEN_WLASCICIELA}).status_code == 200

    def test_biale_znaki_wokol_tokenu_sa_ucinane(self, klient, srodowisko):
        zapisz_tokeny(srodowisko / "tokeny.json", {"tata": f"  {TOKEN_TATY}  "})
        assert klient.get(CHRONIONY, headers={"X-Auth-Token": TOKEN_TATY}).status_code == 200


class TestRozpoznawanieNazwy:
    """Serwer musi wiedzieć, KTÓRE urządzenie przyszło - na tym oprze się
    późniejszy zapis autora ruchu magazynowego."""

    def test_nazwa_wlasciciela(self):
        assert server._dopasuj_token(TOKEN_WLASCICIELA) == server.WLASCICIEL

    def test_nazwa_urzadzenia(self, srodowisko):
        zapisz_tokeny(srodowisko / "tokeny.json", {"tata": TOKEN_TATY})
        assert server._dopasuj_token(TOKEN_TATY) == "tata"

    def test_brak_dopasowania(self):
        assert server._dopasuj_token("cokolwiek") is None
        assert server._dopasuj_token(None) is None
        assert server._dopasuj_token("") is None

    def test_wlasciwa_nazwa_przy_wielu_urzadzeniach(self, srodowisko):
        # Pętla w _dopasuj_token celowo nie przerywa się na trafieniu (stały czas),
        # więc musi zwrócić nazwę TEGO tokenu, a nie ostatniego sprawdzanego.
        zapisz_tokeny(srodowisko / "tokeny.json",
                      {"tata": TOKEN_TATY, "warsztat": "trzeci", "zapas": "czwarty"})
        assert server._dopasuj_token(TOKEN_TATY) == "tata"
        assert server._dopasuj_token("trzeci") == "warsztat"
        assert server._dopasuj_token("czwarty") == "zapas"

    def test_zbior_zawiera_wlasciciela_i_urzadzenia(self, srodowisko):
        zapisz_tokeny(srodowisko / "tokeny.json", {"tata": TOKEN_TATY})
        assert server._tokeny() == {server.WLASCICIEL: TOKEN_WLASCICIELA,
                                     "tata": TOKEN_TATY}


class TestLogowanieWeb:
    def test_urzadzenie_moze_zalogowac_sie_w_przegladarce(self, klient, srodowisko):
        zapisz_tokeny(srodowisko / "tokeny.json", {"tata": TOKEN_TATY})
        r = klient.post("/login", data={"token": TOKEN_TATY})
        assert r.status_code == 302
        assert klient.get(CHRONIONY).status_code == 200, "sesja nie została zapamiętana"

    def test_zly_token_nie_loguje(self, klient):
        r = klient.post("/login", data={"token": "nie-ten"})
        assert r.status_code == 401
        assert klient.get(CHRONIONY).status_code == 401

    def test_sesja_ginie_po_uniewaznieniu(self, klient, srodowisko):
        # Ciasteczko trzyma sam token, więc po jego unieważnieniu sesja ma przestać
        # działać - inaczej odebranie dostępu nie obejmowałoby przeglądarki.
        plik = srodowisko / "tokeny.json"
        zapisz_tokeny(plik, {"tata": TOKEN_TATY})
        klient.post("/login", data={"token": TOKEN_TATY})
        assert klient.get(CHRONIONY).status_code == 200
        zapisz_tokeny(plik, {})
        assert klient.get(CHRONIONY).status_code == 401


class TestNarzedzieTokeny:
    def test_dodaj_zwraca_rozne_tokeny(self, srodowisko):
        a = tokeny.dodaj("tata")
        b = tokeny.dodaj("warsztat")
        assert a != b
        assert len(a) >= 32, "token zbyt krótki jak na jedyną zaporę w internecie"
        assert set(tokeny.wczytaj()) == {"tata", "warsztat"}

    def test_nie_nadpisuje_istniejacego(self, srodowisko):
        tokeny.dodaj("tata")
        with pytest.raises(SystemExit, match="uniewaznij"):
            tokeny.dodaj("tata")

    def test_nazwa_wlasciciela_zarezerwowana(self, srodowisko):
        with pytest.raises(SystemExit, match="zarezerwowana"):
            tokeny.dodaj(tokeny.WLASCICIEL)

    def test_uniewaznij_usuwa(self, srodowisko):
        tokeny.dodaj("tata")
        tokeny.uniewaznij("tata")
        assert tokeny.wczytaj() == {}

    def test_uniewaznienie_nieistniejacego_mowi_wprost(self, srodowisko):
        with pytest.raises(SystemExit, match="Nie ma urządzenia"):
            tokeny.uniewaznij("kogo-nie-ma")

    def test_plik_tylko_dla_wlasciciela(self, srodowisko):
        tokeny.dodaj("tata")
        prawa = (srodowisko / "tokeny.json").stat().st_mode & 0o777
        assert prawa == 0o600, f"plik z tokenami ma prawa {oct(prawa)}"

    def test_nie_zostaje_plik_tymczasowy(self, srodowisko):
        # Zapis idzie przez .tmp i replace(); gdyby .tmp zostawał, leżałby obok
        # z tokenami w środku.
        tokeny.dodaj("tata")
        assert list(srodowisko.glob("*.tmp")) == []

    def test_uszkodzony_plik_zglasza_blad_zamiast_kasowac(self, srodowisko):
        # Cicha zamiana uszkodzonego pliku na pusty odcięłaby wszystkie urządzenia.
        (srodowisko / "tokeny.json").write_text("{niepoprawny")
        with pytest.raises(SystemExit, match="JSON"):
            tokeny.wczytaj()
