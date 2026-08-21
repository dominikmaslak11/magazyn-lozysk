"""Wycena odpadu OSB — narzędzie używane pod presją, więc musi się nie mylić.

Kontekst: stoisz w markecie przy koszu ze zrzynkami i masz kilkanaście sekund
na decyzję. Zła odpowiedź kosztuje albo niepotrzebnie wydane pieniądze, albo
przegapioną okazję. Dlatego testy pilnują dwóch rzeczy: progu opłacalności
i rozpoznawania wymiarów wpisanych po ludzku.
"""

import sys
from pathlib import Path

import pytest

KATALOG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG))

import zrzynki as z  # noqa: E402


class TestOdniesienie:
    def test_pelny_arkusz_daje_piec_polek(self):
        # 2500 x 1250 przy formatce 855 x 495 i rzazie 4 mm.
        assert z.ODNIESIENIE_SZTUK == 5

    def test_cena_odniesienia(self):
        assert z.ODNIESIENIE_CENA == pytest.approx(104.0 / 5)


class TestIleSieZmiesci:
    def test_kawalek_na_jedna_polke(self):
        w = z.wyceniaj(900, 520, 12)
        assert w.polek == 1

    def test_o_wlos_za_maly_to_zero_polek(self):
        # 850 < 855: brakuje 5 mm i półka po prostu nie wyjdzie.
        assert z.wyceniaj(850, 520, 12).polek == 0

    def test_rzaz_jest_liczony(self):
        # Dwie półki 495 obok siebie to 990 mm materiału + 4 mm rzazu.
        assert z.wyceniaj(900, 994, 30).polek == 2
        assert z.wyceniaj(900, 989, 30).polek == 1

    def test_obrocenie_formatki_jest_brane_pod_uwage(self):
        # 500 x 900: półka mieści się tylko po obróceniu o 90 stopni.
        w = z.wyceniaj(900, 500, 15)
        assert w.polek == 1

    def test_maly_kawalek_liczy_sie_na_przegrody(self):
        w = z.wyceniaj(600, 500, 8)
        assert w.polek == 0
        assert w.przegrod >= 2


class TestWerdykt:
    def test_wyraznie_taniej_to_bierz(self):
        # 1 półka za 12 zł wobec 20,80 zł z arkusza = 58 procent.
        assert z.wyceniaj(900, 520, 12).werdykt == "BIERZ"

    def test_drozej_niz_arkusz_to_nie(self):
        assert z.wyceniaj(900, 520, 25).werdykt == "NIE"

    def test_tuz_pod_cena_arkusza_to_granica(self):
        # 95 procent ceny odniesienia: taniej, ale nie na tyle, żeby się opłacało
        # wozić i ciąć osobny kawałek.
        w = z.wyceniaj(900, 520, z.ODNIESIENIE_CENA * 0.95)
        assert w.werdykt == "NA GRANICY"

    def test_prog_okazji_dokladnie(self):
        assert z.wyceniaj(900, 520, z.ODNIESIENIE_CENA * z.PROG_OKAZJA).werdykt == "BIERZ"
        assert z.wyceniaj(900, 520, z.ODNIESIENIE_CENA * 0.86).werdykt == "NA GRANICY"

    def test_bez_polki_ale_z_przegrodami(self):
        w = z.wyceniaj(600, 500, 5)
        assert w.werdykt == "TYLKO NA PRZEGRODY"

    def test_zlom_to_nie(self):
        assert z.wyceniaj(400, 300, 5).werdykt == "NIE"

    def test_darmowy_odpad_zawsze_sie_oplaca(self):
        assert z.wyceniaj(900, 520, 0).werdykt == "BIERZ"

    def test_cena_za_polke_gdy_zero_polek(self):
        # Nie może rzucić dzieleniem przez zero - to by wywaliło narzędzie w sklepie.
        assert z.wyceniaj(400, 300, 5).cena_za_polke is None
        assert z.wyceniaj(400, 300, 5).stosunek is None


class TestRozpoznawanieWymiarow:
    def test_zwykly_zapis(self):
        assert z.wymiary_z_tekstu("1200x600") == (1200.0, 600.0)

    def test_spacje_wokol_iksa(self):
        assert z.wymiary_z_tekstu("1200 x 600") == (1200.0, 600.0)

    def test_jawne_centymetry(self):
        assert z.wymiary_z_tekstu("120x60 cm") == (1200.0, 600.0)

    def test_przecinek_jako_kropka(self):
        assert z.wymiary_z_tekstu("120,5x60 cm") == (1205.0, 600.0)

    def test_male_liczby_traktujemy_jak_centymetry(self):
        # Nikt nie kupuje odpadu 120 x 60 MILIMETRÓW, więc to na pewno centymetry.
        assert z.wymiary_z_tekstu("120x60") == (1200.0, 600.0)

    def test_duze_liczby_zostaja_milimetrami(self):
        assert z.wymiary_z_tekstu("1200x600") == (1200.0, 600.0)

    def test_brak_drugiego_wymiaru_to_czytelny_blad(self):
        with pytest.raises(ValueError, match="dwóch wymiarów"):
            z.wymiary_z_tekstu("1200")

    def test_granica_heurystyki_jest_udokumentowana(self):
        # ŚWIADOME OGRANICZENIE: kawałek 290 x 200 mm zostanie odczytany jako
        # centymetry i urośnie do 2900 x 2000. Taki wymiar w milimetrach to
        # skrawek bez wartości, więc pomyłka jest nieszkodliwa - ale gdyby
        # kiedyś przeszkadzała, to jest jej miejsce.
        assert z.wymiary_z_tekstu("290x200") == (2900.0, 2000.0)
        assert z.wymiary_z_tekstu("290x200 mm") == (2900.0, 2000.0)


class TestWytworyPliku:
    def test_pdf_powstaje_i_nie_jest_pusty(self, tmp_path):
        w = z.wyceniaj(1300, 1050, 32)
        p = z.buduj_pdf(w, tmp_path / "wycena.pdf")
        assert p.exists() and p.stat().st_size > 3000

    def test_pdf_dziala_gdy_nic_sie_nie_miesci(self, tmp_path):
        # Rysunek rozkroju bez ani jednej formatki nie może wywalić generatora.
        w = z.wyceniaj(400, 300, 5)
        assert z.buduj_pdf(w, tmp_path / "maly.pdf").exists()

    def test_raport_wspomina_werdykt(self):
        assert "BIERZ" in z.raport(z.wyceniaj(900, 520, 12))

    def test_instrukcja_dla_zlomu_nie_klamie(self):
        assert z.instrukcja_ciecia(z.wyceniaj(400, 300, 5)) == ["Nie ma czego ciac."]
