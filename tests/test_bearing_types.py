"""
Testy klasyfikatora typu łożyska (bearing_types.py).

Uruchomienie:
    python -m pytest tests/ -q          (jeśli masz pytest)
    python tests/test_bearing_types.py  (bez żadnych zależności)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bearing_data import SERIES, TYPY_NIEROZPOZNAWALNE_Z_OZNACZENIA
from bearing_data import TYP_IGIELKOWE, TYP_WSTAWKOWE, TYP_WSTAWKOWE_ES, TYP_WSTAWKOWE_RAE
from bearing_types import bore_from_symbol, classify_symbol


def test_zgodnosc_z_wbudowanym_katalogiem():
    """Najmocniejszy test: dla KAŻDEGO wpisu katalogu znamy typ na pewno,
    więc klasyfikator musi się z nim zgadzać co do jednego.

    Wyjątek: serie w numeracji innej niż ISO (calowe). Ich oznaczenia nie kodują
    ani typu, ani otworu, więc klasyfikator ma prawo powiedzieć "nie wiem" - i test
    tego pilnuje ZAMIAST wymuszać zgadywanie.
    """
    bledy = []
    for typ, tabela in SERIES.items():
        if typ in TYPY_NIEROZPOZNAWALNE_Z_OZNACZENIA:
            for symbol in tabela:
                assert classify_symbol(symbol) is None, (
                    f"{symbol}: oznaczenie calowe nie może dawać typu z reguł ISO")
                assert bore_from_symbol(symbol) is None, (
                    f"{symbol}: kod otworu ISO nie obowiązuje w numeracji calowej")
            continue
        for symbol in tabela:
            rozpoznany = classify_symbol(symbol)
            if rozpoznany != typ:
                bledy.append(f"{symbol}: oczekiwano {typ!r}, dostano {rozpoznany!r}")
    assert not bledy, "Rozbieżności z katalogiem:\n  " + "\n  ".join(bledy)


def test_pulapka_liczby_cyfr():
    """O typie decyduje NIE tylko prefiks, ale i długość ciągu cyfr.
    To najłatwiejszy sposób, żeby zepsuć ten plik nieuważną zmianą."""
    assert classify_symbol("3204") == "skośne (kulkowe)"
    assert classify_symbol("30204") == "stożkowe"
    assert classify_symbol("2205") == "wahliwe kulkowe"
    assert classify_symbol("22205") == "wahliwe baryłkowe"
    assert classify_symbol("3306") == "skośne (kulkowe)"
    assert classify_symbol("33006") == "stożkowe"


def test_igielkowe_maja_pierwszenstwo_przed_walcowymi():
    """Reguła na 'N' (walcowe) połknęłaby NA/NK/NKI, gdyby kolejność się odwróciła."""
    assert classify_symbol("NA4900") == "igiełkowe"
    assert classify_symbol("NKI25/20") == "igiełkowe"
    assert classify_symbol("NK1010") == "igiełkowe"
    assert classify_symbol("NU205") == "walcowe"
    assert classify_symbol("NJ2308") == "walcowe"
    assert classify_symbol("NNU4920") == "walcowe"


def test_typy_spoza_katalogu():
    """Cała wartość klasyfikatora: rozpoznaje oznaczenia, których NIE ma w katalogu."""
    assert classify_symbol("7205") == "skośne (kulkowe)"
    assert classify_symbol("QJ308") == "skośne (kulkowe)"
    assert classify_symbol("51105") == "oporowe"
    assert classify_symbol("29412") == "oporowe"
    assert classify_symbol("HK1010") == "igiełkowe"
    assert classify_symbol("NUP310") == "walcowe"


def test_zapis_jaki_wpisuje_uzytkownik():
    """Marka z przodu, przyrostki, małe litery, spacje i łączniki."""
    assert classify_symbol("SKF 6205-2RS1") == "kulkowe zwykłe"
    assert classify_symbol("FAG NU205") == "walcowe"
    assert classify_symbol("nsk-6008 zz") == "kulkowe zwykłe"
    assert classify_symbol("nu 205 ecp") == "walcowe"
    assert classify_symbol("30204 A") == "stożkowe"
    assert classify_symbol("UC 211 D1") == "wstawkowe (UC)"
    assert classify_symbol("7310BEP") == "skośne (kulkowe)"


def test_uczciwe_nie_wiem():
    """Lepiej nie odpowiedzieć niż zgadnąć - błędna kategoria jest gorsza niż jej brak."""
    for smiec in ["", "   ", "ABC", "ABC123", "xyz", "??", "-", "SKF"]:
        assert classify_symbol(smiec) is None, f"{smiec!r} nie powinno dostać typu"
    # Zbyt krótkie, żeby być oznaczeniem łożyska
    assert classify_symbol("12") is None
    assert classify_symbol("5") is None


def test_srednica_z_oznaczenia_zgodna_z_katalogiem():
    """Dla każdego wpisu katalogu znamy prawdziwe d - reguła kodu otworu (ISO 15)
    musi się z nim zgadzać wszędzie tam, gdzie w ogóle obowiązuje."""
    from bearing_types import bore_from_symbol
    bledy = []
    for typ, tabela in SERIES.items():
        for symbol, (d, _D, _B) in tabela.items():
            wyliczone = bore_from_symbol(symbol)
            if wyliczone is not None and abs(wyliczone - d) > 1.0:
                bledy.append(f"{symbol}: katalog d={d}, z oznaczenia={wyliczone}")
    assert not bledy, "Rozbieżności otworu:\n  " + "\n  ".join(bledy)


def test_srednica_z_oznaczenia_spoza_katalogu():
    from bearing_types import bore_from_symbol
    assert bore_from_symbol("6204") == 20.0
    assert bore_from_symbol("NU205") == 25.0
    assert bore_from_symbol("UC206") == 30.0
    assert bore_from_symbol("30204") == 20.0
    assert bore_from_symbol("22210") == 50.0
    assert bore_from_symbol("6000") == 10.0     # wyjątek: kod 00
    assert bore_from_symbol("6003") == 17.0     # wyjątek: kod 03
    # Serie, w których reguła NIE obowiązuje - lepiej nie sprawdzać niż sprawdzić źle
    assert bore_from_symbol("HK1010") is None
    assert bore_from_symbol("126") is None      # gołe 3 cyfry są niejednoznaczne
    assert bore_from_symbol("") is None


def test_odsiewanie_blednych_wymiarow_z_internetu():
    """Realny przypadek: dla 6204 wyszukiwarka zwracała 60x80 zamiast 20x47."""
    from bearing_types import dimensions_are_plausible
    assert dimensions_are_plausible("6204", 20, 47, 14) is True
    assert dimensions_are_plausible("6204", 60, 80, 0) is False     # zły otwór i B=0
    assert dimensions_are_plausible("6204", 60, 80, 18) is False    # zły otwór
    assert dimensions_are_plausible("6205", 52, 25, 15) is False    # d >= D
    assert dimensions_are_plausible("6205", 25, 52, 0) is False     # zerowa szerokość
    # Tam, gdzie reguły otworu nie ma, sprawdzamy tylko geometrię
    assert dimensions_are_plausible("HK1010", 10, 14, 10) is True


def test_uc_i_es_to_rozne_typy():
    """UC208 i ES208 dzielą otwór i średnicę zewnętrzną, ale to inne konstrukcje.

    Zlanie ich w jeden typ oznaczałoby, że przy naprawie maszyny appka podpowiada
    część, która nie pasuje - a wygląda na tę właściwą.
    """
    for s in ("UC208", "UC209", "UCP208", "SB208", "UK209"):
        assert classify_symbol(s) == TYP_WSTAWKOWE, s
    for s in ("ES208", "ES209", "ES210", "ESP208"):
        assert classify_symbol(s) == TYP_WSTAWKOWE_ES, s
    assert classify_symbol("UC208") != classify_symbol("ES208")

    # Kod otworu obowiązuje w obu seriach tak samo (ISO 15).
    assert bore_from_symbol("ES208") == 40.0
    assert bore_from_symbol("ES210") == 50.0


def test_es_nie_redukuje_sie_do_golych_cyfr():
    """Regresja: "ES208" -> "208" kazałoby szukać wymiarów zwykłego łożyska kulkowego.

    Dokładnie ta sama pułapka, przez którą kiedyś NU205 stawało się 205 i wyszukiwarka
    zwracała 205x285x38 zamiast 25x52x15.
    """
    from lookup import normalize_symbol
    for symbol in ("ES208", "ES209", "ES210", "ESP208"):
        assert normalize_symbol(symbol) == symbol, (
            f"{symbol} nie może zredukować się do samych cyfr")


def test_seria_ina_liczy_otwor_wprost_w_milimetrach():
    """Trzecia konwencja oznaczeń w tym magazynie - i najłatwiejsza do przeoczenia.

    ISO:        6205  -> kod "05" -> otwór 25 mm
    Timken:     37431A -> brak reguły
    INA:        RAE35 -> otwór 35 mm WPROST, a nie 35 x 5 = 175 mm

    Bez osobnej reguły program uznałby prawdziwe wymiary RAE35 (35 x 72 x 39) za
    niepasujące do oznaczenia i by je odrzucił.
    """
    for symbol, otwor in (("RAE35", 35.0), ("GRAE35", 35.0), ("RAE30", 30.0),
                           ("RALE40", 40.0), ("RA35", 35.0)):
        assert classify_symbol(symbol) == TYP_WSTAWKOWE_RAE, symbol
        assert bore_from_symbol(symbol) == otwor, symbol

    # Prawdziwe wymiary RAE35 muszą przechodzić kontrolę sensowności.
    from bearing_types import dimensions_are_plausible
    assert dimensions_are_plausible("RAE35", 35, 72, 39)
    # A wymiary innego łożyska - nie.
    assert not dimensions_are_plausible("RAE35", 175, 320, 68)


def test_ina_nie_kradnie_igielkowych():
    """Reguła na "RA" nie może połknąć igiełkowych RNA/NA - stąd kolejność reguł."""
    assert classify_symbol("RNA4900") == TYP_IGIELKOWE
    assert classify_symbol("NA4900") == TYP_IGIELKOWE
    assert bore_from_symbol("RNA4900") is None


def test_ina_nie_redukuje_sie_do_golych_cyfr():
    from lookup import normalize_symbol
    for symbol in ("RAE35", "GRAE35", "RALE40"):
        assert normalize_symbol(symbol) == symbol, symbol


if __name__ == "__main__":
    testy = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    niepowodzenia = 0
    for t in testy:
        try:
            t()
            print(f"  OK   {t.__name__}")
        except AssertionError as e:
            niepowodzenia += 1
            print(f"  BŁĄD {t.__name__}\n       {e}")
    print(f"\n{len(testy) - niepowodzenia}/{len(testy)} testów przeszło")
    sys.exit(1 if niepowodzenia else 0)
