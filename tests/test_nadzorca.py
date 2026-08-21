"""Logika nadzorcy — ta część, która nie potrzebuje żywej Vikunji.

Wywołań sieciowych tu nie ma świadomie. Test, który wymaga działającego serwera,
przestaje działać przy każdej awarii serwera i po dwóch takich razach
przestaje się go uruchamiać. Sprawdzamy to, co realnie może się zepsuć przy
edycji pliku: zamianę dat, skracanie odpowiedzi i odmowę czytania konfiguracji
o zbyt luźnych prawach.

Połączenie sprawdza się osobno: ./venv/bin/python nadzorca.py --sprawdz
"""

import json
import os
import sys
from pathlib import Path

import pytest

KATALOG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG))

import nadzorca  # noqa: E402


class TestZamianaDat:
    def test_sama_data_dostaje_godzine(self):
        assert nadzorca._data("2026-09-01") == "2026-09-01T09:00:00Z"

    def test_pelny_znacznik_zostaje_bez_zmian(self):
        znacznik = "2026-09-01T14:30:00Z"
        assert nadzorca._data(znacznik) == znacznik

    def test_brak_wartosci_to_brak_zmiany(self):
        # None znaczy "nie ruszaj tego pola", a nie "wyczyść".
        assert nadzorca._data(None) is None

    def test_pusty_string_kasuje_date(self):
        # Vikunja rozpoznaje rok zerowy jako brak daty.
        assert nadzorca._data("").startswith("0001-")

    def test_spacje_tez_kasuja(self):
        assert nadzorca._data("   ").startswith("0001-")


class TestCzyDataUstawiona:
    def test_rok_zerowy_to_brak(self):
        assert not nadzorca._ustawiona("0001-01-01T00:00:00Z")

    def test_pusty_to_brak(self):
        assert not nadzorca._ustawiona("")
        assert not nadzorca._ustawiona(None)

    def test_prawdziwa_data(self):
        assert nadzorca._ustawiona("2026-09-01T09:00:00Z")


class TestSkrot:
    """Skrót ma odciąć ~40 pól Vikunji do tych, o których się rozmawia."""

    def test_procent_z_ulamka(self):
        # Vikunja trzyma 0..1, człowiek myśli w procentach.
        assert nadzorca._skrot({"id": 1, "percent_done": 0.25})["postep_proc"] == 25

    def test_brak_procentu_to_zero(self):
        assert nadzorca._skrot({"id": 1})["postep_proc"] == 0

    def test_daty_obciete_do_dnia(self):
        s = nadzorca._skrot({"id": 1, "start_date": "2026-09-01T09:00:00Z"})
        assert s["start"] == "2026-09-01"

    def test_pusta_data_to_none_a_nie_pusty_string(self):
        assert nadzorca._skrot({"id": 1, "end_date": ""})["koniec"] is None

    def test_priorytet_slownie(self):
        assert nadzorca._skrot({"id": 1, "priority": 5})["priorytet"] == "TERAZ"
        assert nadzorca._skrot({"id": 1, "priority": 0})["priorytet"] == "-"

    def test_nieznany_priorytet_nie_wywraca(self):
        assert nadzorca._skrot({"id": 1, "priority": 99})["priorytet"] == "?"

    def test_nie_przepuszcza_smieci(self):
        # Załączniki i reakcje nie mają po co trafiać do kontekstu modelu.
        s = nadzorca._skrot({"id": 1, "attachments": [1] * 50, "reactions": {"a": 1}})
        assert "attachments" not in s and "reactions" not in s


class TestPrawaDoKonfiguracji:
    """Token daje pełny dostęp do zadań — plik czytelny dla innych to wyciek."""

    def _konfig(self, tmp_path, prawa):
        p = tmp_path / "vikunja.json"
        p.write_text(json.dumps({"url": "http://x/api/v1", "token": "tk_x"}))
        os.chmod(p, prawa)
        return p

    def test_odmawia_przy_luznych_prawach(self, tmp_path, monkeypatch):
        monkeypatch.setattr(nadzorca, "KONFIG", self._konfig(tmp_path, 0o644))
        with pytest.raises(nadzorca.BladVikunji, match="chmod 600"):
            nadzorca._konfiguracja()

    def test_przyjmuje_600(self, tmp_path, monkeypatch):
        monkeypatch.setattr(nadzorca, "KONFIG", self._konfig(tmp_path, 0o600))
        url, token = nadzorca._konfiguracja()
        assert (url, token) == ("http://x/api/v1", "tk_x")

    def test_ucina_ukosnik_na_koncu(self, tmp_path, monkeypatch):
        p = tmp_path / "vikunja.json"
        p.write_text(json.dumps({"url": "http://x/api/v1/", "token": "tk_x"}))
        os.chmod(p, 0o600)
        monkeypatch.setattr(nadzorca, "KONFIG", p)
        assert nadzorca._konfiguracja()[0] == "http://x/api/v1"

    def test_czytelny_blad_gdy_brak_pliku(self, tmp_path, monkeypatch):
        monkeypatch.setattr(nadzorca, "KONFIG", tmp_path / "nie-ma.json")
        with pytest.raises(nadzorca.BladVikunji, match="Brak"):
            nadzorca._konfiguracja()


class TestNarzedziaMCP:
    def test_serwer_wystawia_komplet(self):
        # Nazwy są w umowie z modelem — zmiana nazwy psuje wywołania.
        import asyncio

        serwer = nadzorca.zbuduj_serwer()
        nazwy = {n.name for n in asyncio.run(serwer.list_tools())}
        assert nazwy == {"projekty", "nowy_projekt", "zadania", "nowe_zadanie",
                         "zmien_zadanie", "zaleznosc", "stan"}
