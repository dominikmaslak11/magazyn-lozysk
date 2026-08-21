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

    def test_bez_ciecia_to_sama_cena_plyty(self):
        assert z.cena_polki_z_arkusza(0.0) == pytest.approx(104.0 / 5)

    def test_ciecie_podnosi_cene_odniesienia(self):
        # 5 ciec po 3 zl na arkusz -> 119 zl / 5 polek.
        assert z.cena_polki_z_arkusza(3.0) == pytest.approx((104.0 + 5 * 3) / 5)

    def test_express_kosztuje_dwa_razy_tyle(self):
        assert z.cena_polki_z_arkusza(6.0) == pytest.approx((104.0 + 5 * 6) / 5)


class TestLiczbaCiec:
    """Model gilotynowy: najpierw pasy, potem formatki w pasie."""

    def test_arkusz_na_piec_polek(self):
        ciec, sztuk = z.liczba_ciec(2500, 1250, 855, 495)
        assert (ciec, sztuk) == (5, 5)

    def test_kawalek_dokladnie_na_formatke_nie_wymaga_ciecia(self):
        # Jesli odpad ma juz wymiar polki, nie ma czego ciac.
        ciec, sztuk = z.liczba_ciec(855, 495, 855, 495)
        assert (ciec, sztuk) == (0, 1)

    def test_resztka_ponizej_progu_nie_liczy_sie_jako_ciecie(self):
        # 10 mm nadmiaru to obrzyn krawedzi, nie osobna usluga.
        ciec, _ = z.liczba_ciec(865, 505, 855, 495)
        assert ciec == 0

    def test_resztka_powyzej_progu_to_dodatkowe_ciecie(self):
        ciec, _ = z.liczba_ciec(1000, 495, 855, 495)
        assert ciec == 1

    def test_formatka_wieksza_niz_plyta(self):
        _, sztuk = z.liczba_ciec(400, 300, 855, 495)
        assert sztuk == 0


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
        assert z.wyceniaj(900, 520, 12, 0.0).werdykt == "BIERZ"

    def test_drozej_niz_arkusz_to_nie(self):
        assert z.wyceniaj(900, 520, 25, 0.0).werdykt == "NIE"

    def test_tuz_pod_cena_arkusza_to_granica(self):
        prog = z.cena_polki_z_arkusza(0.0)
        assert z.wyceniaj(900, 520, prog * 0.95, 0.0).werdykt == "NA GRANICY"

    def test_prog_okazji_dokladnie(self):
        prog = z.cena_polki_z_arkusza(0.0)
        assert z.wyceniaj(900, 520, prog * z.PROG_OKAZJA, 0.0).werdykt == "BIERZ"
        assert z.wyceniaj(900, 520, prog * 0.86, 0.0).werdykt == "NA GRANICY"

    def test_bez_polki_ale_z_przegrodami(self):
        assert z.wyceniaj(600, 500, 5, 0.0).werdykt == "TYLKO NA PRZEGRODY"

    def test_zlom_to_nie(self):
        assert z.wyceniaj(400, 300, 5, 0.0).werdykt == "NIE"

    def test_darmowy_odpad_zawsze_sie_oplaca(self):
        assert z.wyceniaj(900, 520, 0, 0.0).werdykt == "BIERZ"

    def test_darmowy_odpad_z_platnym_cieciem_nadal_sie_oplaca(self):
        # Nawet gdy za samo ciecie trzeba zaplacic, darmowa plyta wygrywa.
        assert z.wyceniaj(900, 520, 0, 3.0).werdykt == "BIERZ"


class TestKosztCiecia:
    """Zlecanie ciecia zmienia werdykty - male odpady traca przewage."""

    def test_ciecie_jest_doliczane_do_kosztu(self):
        w = z.wyceniaj(1300, 1050, 32, 3.0)
        assert w.koszt_ciecia == w.ciec_polki * 3.0
        assert w.koszt_calkowity == 32 + w.koszt_ciecia

    def test_ten_sam_odpad_gorszy_gdy_ciecie_platne(self):
        bez = z.wyceniaj(1300, 1050, 32, 0.0)
        zc = z.wyceniaj(1300, 1050, 32, 3.0)
        assert zc.cena_za_polke > bez.cena_za_polke
        # To jest sedno: doliczenie uslugi potrafi zmienic decyzje.
        assert bez.werdykt == "BIERZ" and zc.werdykt == "NA GRANICY"

    def test_express_jest_gorszy_od_zwyklego(self):
        zw = z.wyceniaj(1300, 1050, 32, z.CIECIE_ZWYKLE)
        ex = z.wyceniaj(1300, 1050, 32, z.CIECIE_EXPRESS)
        assert ex.cena_za_polke > zw.cena_za_polke

    def test_odpad_w_rozmiarze_polki_nie_placi_za_ciecie(self):
        w = z.wyceniaj(855, 495, 10, 3.0)
        assert w.polek == 1 and w.ciec_polki == 0 and w.koszt_ciecia == 0

    def test_porownanie_jest_uczciwe_po_obu_stronach(self):
        # Odniesienie tez musi miec doliczone ciecie - inaczej rachunek klamie
        # na korzysc odpadow.
        w = z.wyceniaj(900, 520, 12, 3.0)
        assert w.odniesienie == pytest.approx(z.cena_polki_z_arkusza(3.0))
        assert w.odniesienie > z.cena_polki_z_arkusza(0.0)

    def test_cena_za_polke_gdy_zero_polek(self):
        # Nie może rzucić dzieleniem przez zero - to by wywaliło narzędzie w sklepie.
        assert z.wyceniaj(400, 300, 5).cena_za_polke is None
        assert z.wyceniaj(400, 300, 5).stosunek is None
        assert z.wyceniaj(400, 300, 5).cena_za_przegrode is None


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
        assert "BIERZ" in z.raport(z.wyceniaj(900, 520, 12, 0.0))

    def test_raport_pokazuje_koszt_ciecia(self):
        r = z.raport(z.wyceniaj(1300, 1050, 32, 3.0))
        assert "ciec do zlecenia" in r and "RAZEM" in r

    def test_instrukcja_dla_zlomu_nie_klamie(self):
        assert z.instrukcja_ciecia(z.wyceniaj(400, 300, 5)) == ["Nie ma czego ciac."]


class TestRysunekZgadzaSieZTabela:
    """Rysunek na kartce musi pokazywać tyle formatek, ile mówi tabela.

    Regresja: orientację brano z opisu tekstowego ze stolarz.py przez sprawdzenie
    podłańcucha "obrocona". Opis zawiera "obrócona" z polskim znakiem, więc warunek
    nigdy nie trafiał i przy 1700 x 1000 rysunek pokazywał 2 półki zamiast 3 -
    w sklepie ucięłoby się o jedną za mało.
    """

    @pytest.mark.parametrize("dl,szer", [(1700, 1000), (1300, 1050), (900, 520),
                                          (2500, 1250), (2400, 600)])
    def test_uklad_daje_tyle_samo_co_wycena(self, dl, szer):
        fd, fs = z.ukladanie(dl, szer, z.POLKA.dlugosc, z.POLKA.glebokosc)
        nx = int((dl + z.RZAZ) // (fd + z.RZAZ))
        ny = int((szer + z.RZAZ) // (fs + z.RZAZ))
        assert nx * ny == z.wyceniaj(dl, szer, 1).polek

    def test_wybiera_orientacje_z_wieksza_liczba_sztuk(self):
        # 1700 x 1000: wzdluz 855 miesci sie 1 raz (2 szt.), wzdluz 495 - 3 razy.
        assert z.ukladanie(1700, 1000, 855, 495) == (495.0, 855.0)
