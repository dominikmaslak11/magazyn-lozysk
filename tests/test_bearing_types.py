"""
Testy klasyfikatora typu łożyska (bearing_types.py).

Uruchomienie:
    python -m pytest tests/ -q          (jeśli masz pytest)
    python tests/test_bearing_types.py  (bez żadnych zależności)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bearing_data import SERIES
from bearing_data import (TYP_IGIELKOWE, TYP_OPOROWE, TYP_SKOSNE, TYP_STOZKOWE_CALOWE,
                           TYP_TULEJA_WCIAGANA,
                           TYP_WSTAWKOWE_UD,
                           TYP_WSTAWKOWE, TYP_WSTAWKOWE_ES, TYP_WSTAWKOWE_EX,
                           TYP_WSTAWKOWE_RAE)
from bearing_types import bore_from_symbol, classify_symbol


def test_zgodnosc_z_wbudowanym_katalogiem():
    """Najmocniejszy test: dla KAŻDEGO wpisu katalogu znamy typ na pewno,
    więc klasyfikator musi się z nim zgadzać co do jednego.

    Dotyczy to także oznaczeń CALOWYCH. Kiedyś były tu wyjątkiem ("nie wiem" było
    uczciwsze niż zgadywanie), ale odkąd serie calowe są zarejestrowane w
    serie_lozysk.py, klasyfikator ma je znać tak samo jak resztę.
    """
    bledy = []
    for typ, tabela in SERIES.items():
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

    ISO:        6205   -> kod "05" -> otwór 25 mm
    Timken:     37431A -> numer katalogowy, brak reguły otworu
    INA:        RAE35  -> otwór 35 mm WPROST, a nie 35 x 5 = 175 mm

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


def test_serie_calowe_timkena():
    """Czwarta konwencja oznaczeń: numer KATALOGOWY, który nie koduje nic.

    L (light), M (medium), H (heavy) i złożenia LL/LM/HM/HH, plus EE i EH.
    """
    for symbol in ("LM11949", "LM11910", "L44643", "L44610", "M12649", "M12610",
                    "HM89449", "H414242", "EE640192", "LL264648", "HH221449"):
        assert classify_symbol(symbol) == TYP_STOZKOWE_CALOWE, symbol
        assert bore_from_symbol(symbol) is None, (
            f"{symbol}: numer calowy nie koduje otworu, a program coś policzył")


def test_przedrostek_J_u_timkena_to_seria_metryczna():
    """JLM/JH/JM/JW to u Timkena bore i O.D. METRYCZNE, więc NIE są "calowe".

    Wpisanie ich na listę serii calowych byłoby błędem merytorycznym, nie literówką -
    stąd osobny test, żeby nikt ich tam nie dopisał "dla kompletu".
    """
    for symbol in ("JLM104948", "JH415647", "JM205149", "JW5049"):
        assert classify_symbol(symbol) != TYP_STOZKOWE_CALOWE, symbol


def test_prog_czterech_cyfr_odsiewa_nielozyska():
    """Reguła calowa wymaga 4 cyfr i to jest jedyne, co ją broni przed fałszywkami.

    H208  - tuleja wciągana do łożysk wahliwych, nie łożysko stożkowe.
    LM8UU - łożysko LINIOWE (tuleiowe), spotykane przy drukarkach 3D.

    Obniżenie progu do trzech cyfr wpuściłoby oba i nadałoby im pewnie brzmiący,
    ale fałszywy typ - dokładnie to, czego ten plik ma nie robić.
    """
    for symbol in ("H208", "M208", "L208", "LM8UU", "H308"):
        assert classify_symbol(symbol) != TYP_STOZKOWE_CALOWE, symbol


def test_tuleja_wciagana_seria_H():
    """H2/H3 to tuleje wciągane (adapter sleeves), nie łożyska - 3 cyfry po H.

    H210 = wałek 50 mm. Trzy cyfry odróżniają tuleję od calowego stożka Timkena
    H (heavy), który ma ich 4+ (H414242) i dalej idzie do stożkowych calowych.
    """
    for symbol in ("H208", "H210", "H308", "H220", "H232"):
        assert classify_symbol(symbol) == TYP_TULEJA_WCIAGANA, symbol
    assert classify_symbol("FAG H210") == TYP_TULEJA_WCIAGANA
    # kod otworu ISO: H208 -> 40 mm, H210 -> 50 mm
    assert bore_from_symbol("H208") == 40.0
    assert bore_from_symbol("H210") == 50.0
    # calowy Timken H (heavy, 4+ cyfr) nie jest tuleją
    assert classify_symbol("H414242") == TYP_STOZKOWE_CALOWE
    assert bore_from_symbol("H414242") is None


def test_numer_katalogowy_357234():
    """357234 to numer katalogowy OEM (skośne dwurzędowe 35x72x34), nie seria ISO.

    Żadna reguła go nie rozpozna, więc typ i wymiary są wpisane JAWNIE - jak przy
    calowych 37431A/37625, tylko z innym typem (skośne, nie calowe).
    """
    from lookup import normalize_symbol
    from bearing_data import BEARING_DB, BEARING_TYPE
    assert classify_symbol("357234") == TYP_SKOSNE
    assert bore_from_symbol("357234") is None  # numer nie koduje otworu ISO
    assert normalize_symbol("357234") == "357234"
    assert BEARING_DB["357234"] == (35, 72, 34)
    assert BEARING_TYPE["357234"] == TYP_SKOSNE


def test_calowe_nie_kradna_igielkowych_ani_walcowych():
    """Reguła na "H" nie może połknąć HK (igiełkowe), a "L"/"M" niczego z ISO."""
    assert classify_symbol("HK1010") == TYP_IGIELKOWE
    assert classify_symbol("HK2016") == TYP_IGIELKOWE
    assert classify_symbol("NU205") == "walcowe"
    assert classify_symbol("6205") == "kulkowe zwykłe"
    assert classify_symbol("30204") == "stożkowe"


def test_komplet_stozek_z_miska_nie_gubi_drugiego_czlonu():
    """Komplet zapisuje się przez ukośnik i MUSI przetrwać normalizację w całości.

    "37431A/37625" obcięte do "37431A" to sam stożek - inne wymiary (132,745 zamiast
    158,75 mm średnicy zewnętrznej) i inne miejsce na półce. Skrócenie do "37431"
    gubi z kolei literę i nie trafia we własny wpis katalogu.
    """
    from lookup import normalize_symbol

    assert normalize_symbol("37431A/37625") == "37431A/37625"
    assert normalize_symbol("TIMKEN 37431A/37625") == "37431A/37625"
    assert normalize_symbol("37431A") == "37431A"
    assert classify_symbol("37431A/37625") == TYP_STOZKOWE_CALOWE
    assert bore_from_symbol("37431A/37625") is None

    # Prawdziwe wymiary kompletu muszą przechodzić kontrolę sensowności - to jest
    # cel całej osłony na kodzie otworu.
    from bearing_types import dimensions_are_plausible
    assert dimensions_are_plausible("37431A/37625", 109.538, 158.75, 23.02)


def test_numer_calowy_nie_skraca_sie_do_czterech_cyfr():
    """Regresja: próg {3,4} w normalizacji ucinał "LM11949" do "LM1194"."""
    from lookup import normalize_symbol

    assert normalize_symbol("LM11949") == "LM11949"
    assert normalize_symbol("TIMKEN LM 11949") == "LM11949"
    assert normalize_symbol("EE640192") == "EE640192"


def test_ud_to_nie_uc():
    """Najłatwiejsza do pomylenia para w tym magazynie.

    UC205 i UD205 mają ten SAM otwór i tę SAMĄ średnicę zewnętrzną (25 x 52), ale
    UC ma poszerzony pierścień wewnętrzny z wkrętami dociskowymi (34,1 mm), a UD
    wchodzi na wał wciskiem (15 mm). Ponad dwukrotna różnica szerokości - wpisanie
    jednego zamiast drugiego daje wymiary, które wyglądają wiarygodnie i są błędne.
    """
    from bearing_data import BEARING_DB
    from lookup import normalize_symbol

    assert classify_symbol("UD205") == TYP_WSTAWKOWE_UD
    assert classify_symbol("UD205S") == TYP_WSTAWKOWE_UD
    assert classify_symbol("UC205") == TYP_WSTAWKOWE

    assert BEARING_DB["UD205"] == (25, 52, 15)
    assert BEARING_DB["UC205"] == (25, 52, 34.1)

    # Regresja: bez przedrostka "UD" symbol redukował się do gołego "205" - czwarty
    # przypadek tej samej pułapki co NU205 -> 205 i ES208 -> 208.
    assert normalize_symbol("UD205S") == "UD205"
    assert normalize_symbol("UD 205 S ZVL") == "UD205"

    # Kod otworu obowiązuje tu normalnie, w odróżnieniu od serii calowych.
    assert bore_from_symbol("UD205") == 25.0


def test_oporowe_calowe_timkena():
    """Piąta konwencja: numer T idzie za otworem w setnych CALA (T139 -> 1,385").

    "T139" to numer bazowy, "T139-904A1" numer KOMPLETU (typ TTSP) - ta sama relacja
    co 37431A do 37431A/37625. Oba muszą dać ten sam typ.
    """
    from lookup import normalize_symbol

    for symbol in ("T139", "T139-904A1", "T126-904A1", "T176-904A1"):
        assert classify_symbol(symbol) == TYP_OPOROWE, symbol
        assert bore_from_symbol(symbol) is None, (
            f"{symbol}: numer T nie koduje otworu wg ISO, a program coś policzył")

    # Regresja: bez przedrostka "T" w normalizacji symbol redukował się do "139",
    # czyli do numeru, który nie jest oznaczeniem żadnego łożyska.
    assert normalize_symbol("T139-904A1") == "T139"
    assert normalize_symbol("TIMKEN T139-904A1") == "T139"

    # Prawdziwe wymiary muszą przechodzić kontrolę sensowności. Gdyby reguła ISO
    # zadziałała, wyliczyłaby z cyfr "39" otwór 195 mm i odrzuciła te poniżej.
    from bearing_types import dimensions_are_plausible
    assert dimensions_are_plausible("T139-904A1", 35.179, 58.738, 15.875)


def test_seria_T_nie_kradnie_metrycznych_stozkowych():
    """T7FC060 to METRYCZNE łożysko stożkowe, nie oporowe calowe.

    Samo "^T\\d" by je połknęło. Broni przed tym wymaganie DWÓCH cyfr zaraz po
    literze - w T7FC po "T7" idzie litera. To jedyne, co dzieli te dwie rodziny.
    """
    for symbol in ("T7FC060", "T7FC070", "T7FC045"):
        assert classify_symbol(symbol) != TYP_OPOROWE, symbol


def test_seria_T_nie_kradnie_igielkowych():
    """Przedrostek "TA" (igiełkowe) nie ma cyfry po "T" i jego reguła jest wcześniej."""
    assert classify_symbol("TA4020Z") == TYP_IGIELKOWE
    assert classify_symbol("TA2020") == TYP_IGIELKOWE


def test_ina_nie_kradnie_igielkowych():
    """Reguła na "RA" nie może połknąć igiełkowych RNA/NA - stąd kolejność reguł."""
    assert classify_symbol("RNA4900") == TYP_IGIELKOWE
    assert classify_symbol("NA4900") == TYP_IGIELKOWE
    assert bore_from_symbol("RNA4900") is None


def test_ina_nie_redukuje_sie_do_golych_cyfr():
    from lookup import normalize_symbol
    for symbol in ("RAE35", "GRAE35", "RALE40"):
        assert normalize_symbol(symbol) == symbol, symbol


def test_zapis_snr_z_kropkami():
    """SNR zapisuje oznaczenia z kropkami: "EX.208.G2", "ES.208.G2".

    Dopóki kropka nie była separatorem, przedrostek się nie doklejał i całość
    redukowała się do gołego "208" - czyli program podstawiał wymiary ZWYKŁEGO
    łożyska kulkowego 40x80x18 zamiast wstawkowego 40x80x56,3. Objaw był tym
    gorszy, że otwór i średnica zewnętrzna się zgadzały, więc wynik wyglądał wiarygodnie.
    """
    from lookup import normalize_symbol
    assert normalize_symbol("EX.208.G2") == "EX208"
    assert normalize_symbol("ES.208.G2") == "ES208"
    assert normalize_symbol("UC.208") == "UC208"
    assert classify_symbol("EX.208.G2") == TYP_WSTAWKOWE_EX
    assert classify_symbol("ES.208.G2") == TYP_WSTAWKOWE_ES
    assert bore_from_symbol("EX.208.G2") == 40.0


def test_wstawkowe_o_tych_samych_gabarytach_to_rozne_czesci():
    """UC208, ES208 i EX208 to wszystko 40 x 80 mm, ale trzy różne części.

    Różni je szerokość pierścienia wewnętrznego (49,2 / 43,7 / 56,3 mm) i sposób
    mocowania. Zlanie ich w jeden typ znaczyłoby, że program podpowiada część,
    która wygląda na właściwą i nie pasuje.
    """
    from bearing_data import BEARING_DB
    typy = {classify_symbol(s) for s in ("UC208", "ES208", "EX208")}
    assert len(typy) == 3, f"każdy powinien mieć własny typ, dostano {typy}"
    szerokosci = {BEARING_DB[s][2] for s in ("UC208", "ES208", "EX208")}
    assert len(szerokosci) == 3, f"katalog musi je odróżniać, dostano {szerokosci}"


def test_seria_52xx_to_skosne_a_nie_oporowe():
    """Realny błąd znaleziony przy walidacji bazy użytkownika.

    Łożysko 5202 (15 x 35 x 15,9 mm) było klasyfikowane jako OPOROWE, bo reguła
    obejmowała 4-cyfrowe 51/52/53/54. Tymczasem 52xx i 53xx to SKOŚNE DWURZĘDOWE -
    starsze oznaczenie tej samej konstrukcji co 32xx/33xx (5202 = 3202). Oporowe
    kulkowe mają oznaczenia pięciocyfrowe: 51100, 51200, 52200.

    Pomyłka nie jest kosmetyczna: oporowe przenosi obciążenie osiowe, skośne promieniowo
    i osiowo - to inne zastosowanie w maszynie.
    """
    for s in ("5202", "5200", "5305", "3202", "3302"):
        assert classify_symbol(s) == TYP_SKOSNE, s
    for s in ("51100", "51205", "52205", "51405"):
        assert classify_symbol(s) == TYP_OPOROWE, s


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


def test_us206_to_kulkowe_samonastawne_a_nie_wstawkowe():
    """US206 (30x62x16) to odpowiednik 1206, nie UC206 (30x62x38,1). Goły przedrostek
    "US" jest samonastawny; wstawkowe to dopiero USFE."""
    from bearing_data import TYP_WAHLIWE_KULKOWE, TYP_WSTAWKOWE
    for symbol in ("US206", "US208", "US206G2"):
        assert classify_symbol(symbol) == TYP_WAHLIWE_KULKOWE
    assert classify_symbol("USFE208") == TYP_WSTAWKOWE
    assert bore_from_symbol("US206") == 30.0


def test_seria_bg_bd_to_skosne_dwurzedowe_z_otworem_na_poczatku():
    """30BG5222 2DSE (NACHI) skracało się do "5222" - wahliwego baryłkowego 110x200."""
    from bearing_data import BEARING_DB
    from lookup import lookup_by_symbol, normalize_symbol
    for zapis in ("30BG5222 2DSE", "30BG5222-2DSE", "NACHI 30BG5222 2DSE", "30bg5222"):
        assert normalize_symbol(zapis) == "30BG5222", zapis
        assert classify_symbol(zapis) == TYP_SKOSNE, zapis
        assert bore_from_symbol(zapis) == 30.0, zapis
    # inny rozmiar tej samej rodziny: otwór 35 wprost, nie kod ISO
    assert classify_symbol("35BD5222") == TYP_SKOSNE
    assert bore_from_symbol("35BD5222") == 35.0
    assert BEARING_DB["30BG5222"] == (30, 52, 22)
    r = lookup_by_symbol("30BG5222 2DSE")
    assert (r.d, r.D, r.B, r.typ) == (30, 52, 22, TYP_SKOSNE)
    # wąski wzorzec: zwykłe łożyska nie mogą wpaść w regułę BG/BD
    assert classify_symbol("6205") != TYP_SKOSNE and bore_from_symbol("6205") == 25.0


def test_lm48548_komplet_nie_ginie_przy_normalizacji():
    """LM48548/LM48510 (Timken, 34,925 x 65,0875 x 18,034) - zapis kompletu z ukośnikiem."""
    from lookup import lookup_by_symbol, normalize_symbol
    for zapis in ("LM48548/48510", "LM48548/LM48510", "LM 48548 / LM 48510"):
        assert normalize_symbol(zapis) == "LM48548", zapis
        assert classify_symbol(zapis) == TYP_STOZKOWE_CALOWE, zapis
        assert bore_from_symbol(zapis) is None      # numer calowy nie koduje otworu
    r = lookup_by_symbol("LM48548/48510")
    assert (r.d, r.D, r.B) == (34.925, 65.0875, 18.034)


def test_tuleja_slizgowa_skf_or_bvpb():
    """OR-BVPB366936A redukowało się do gołego "366936" (numer OE) i typu None."""
    from bearing_data import TYP_TULEJA_SLIZGOWA
    from lookup import lookup_by_symbol, normalize_symbol
    for zapis in ("OR-BVPB366936A", "OR-BVPB 366936 A", "SKF OR-BVPB366936A", "BVPB366936"):
        assert normalize_symbol(zapis) == "BVPB366936", zapis
        assert classify_symbol(zapis) == TYP_TULEJA_SLIZGOWA, zapis
        assert bore_from_symbol(zapis) is None      # numer OE nie koduje otworu
    r = lookup_by_symbol("OR-BVPB366936A")
    assert (r.d, r.D, r.B, r.typ) == (35, 52, 16.5, TYP_TULEJA_SLIZGOWA)
