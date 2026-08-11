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
from bearing_types import classify_symbol


def test_zgodnosc_z_wbudowanym_katalogiem():
    """Najmocniejszy test: dla KAŻDEGO wpisu katalogu znamy typ na pewno,
    więc klasyfikator musi się z nim zgadzać co do jednego."""
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
