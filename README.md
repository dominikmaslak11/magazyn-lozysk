# Magazyn Łożysk

System do klasyfikacji i śledzenia łożysk na 9 regałach. Trzy sposoby korzystania:

1. **Aplikacja webowa** (`server.py`) – główna wersja, używana z przeglądarki
   na komputerze i na telefonie (PWA – można „zainstalować” na ekranie
   głównym). Jedna wspólna baza danych na komputerze.
2. **Natywny klient Android** (`android-klient/`) – appka w Kotlinie/Compose
   łącząca się z tym samym serwerem przez sieć Wi-Fi. **Wygaszona** na rzecz
   appki niżej (patrz `android-offline/README.md`).
3. **Samodzielna appka Android** (`android-offline/`) – appka w
   Kotlinie/Compose z własną bazą (Room/SQLite) na telefonie, działa w pełni
   offline i automatycznie synchronizuje się z serwerem, gdy jest
   połączenie (patrz `android-offline/README.md`).

Stara wersja desktopowa (CustomTkinter) jest zarchiwizowana w
`legacy_desktop_gui/` – nieutrzymywana, zastąpiona wersją webową.

## Uruchomienie wersji webowej

```bash
cd lozyska_app
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

Serwer nasłuchuje na `0.0.0.0:8420` – w konsoli zobaczysz adres IP
komputera, pod którym appka jest dostępna z telefonu w tej samej sieci
Wi-Fi (np. `http://192.168.1.23:8420`). Na telefonie możesz dodać stronę
do ekranu głównego (opcja „Dodaj do ekranu głównego” w przeglądarce) –
będzie działać jak zwykła appka.

### Gdzie są dane

Baza danych (`lozyska.db`) leży w `~/.lozyska_data/` – **poza** katalogiem
z kodem, żeby aktualizacja/podmiana plików appki nigdy jej nie ruszyła.
Automatyczne kopie zapasowe (ostatnie 20) robią się przy każdym starcie
serwera oraz przed każdym importem, w `~/.lozyska_data/backups/`.

## Natywne appki Android

Oba projekty Android są w tym repo (`android-klient/`, `android-offline/`)
i budują się przez Android Studio albo `./gradlew assembleDebug` z ich
własnych katalogów. Pliki APK nie są trzymane w repo (patrz `.gitignore`) -
zbuduj lokalnie albo poproś o świeży build.

**android-klient** – wygaszona, zastąpiona przez `android-offline` (patrz
niżej). Zostawiona w repo jako punkt odniesienia.

**android-offline** – główna appka mobilna: własna baza lokalna (działa w
pełni offline) + automatyczna synchronizacja z serwerem, gdy jest
połączenie (Wi-Fi albo przez Tailscale spoza domowej sieci). Szczegóły w
`android-offline/README.md`.

## Jak to działa (dotyczy wszystkich trzech wersji)

### Dodawanie łożyska

- **Znasz symbol** (np. `6008`, `UC206`, `30204`) → wpisz go i kliknij
  „Pobierz wymiary”. Program najpierw sprawdza wbudowaną bazę offline
  (łożyska kulkowe zwykłe, stożkowe, wahliwe kulkowe, wahliwe baryłkowe,
  wstawkowe UC – w sumie ok. 250 najpopularniejszych rozmiarów), a jeśli
  symbolu tam nie ma – próbuje doszukać wymiarów w internecie. Wyniki z
  internetu są wyraźnie oznaczone jako **orientacyjne** – warto je
  zweryfikować suwmiarką.
- **Znasz wymiary, nie znasz symbolu** → wpisz d / D / B (lub tylko część)
  i kliknij „Znajdź symbol na podstawie wymiarów”.

Ilość sztuk zawsze wpisujesz ręcznie.

### Przydział do regału

Regał dobierany jest automatycznie na podstawie **średnicy zewnętrznej D**:
duże łożyska trafiają na regały o niższym poziomie (np. Regał 1 na dole),
małe – na regały o wyższym poziomie (np. Regał 9 na górze). Zakresy średnic
dla każdego regału edytujesz w zakładce **Regały**.

Jeśli chcesz ręcznie zdecydować, na którym regale ma leżeć konkretne
łożysko, wybierz konkretny regał z listy zamiast „Auto” – taki wpis
zostanie oznaczony jako „ręcznie” i nie zostanie ruszony przy późniejszym
przeliczaniu automatycznych przydziałów.

### Etykiety regałów (PDF)

W zakładce „Dane” wersji webowej: „Pobierz etykiety regałów (PDF)” –
generuje dokument z jedną stroną na regał, z listą przypisanych łożysk
(symbol, typ, d/D/B, ilość, uwagi). Do wydruku i przyklejenia na regale.

## Uwaga o wyszukiwaniu w internecie

Funkcja internetowa jest wspomagająca (best-effort) – korzysta z wyników
wyszukiwarki i prostego rozpoznawania wzorców typu „40x80x18”. Może się
czasem pomylić lub niczego nie znaleźć, dlatego dane z internetu są zawsze
oznaczone jako pochodzące ze źródła „internet”, w odróżnieniu od pewnych
danych z „bazy offline”. W razie wątpliwości zawsze można wpisać wymiary
ręcznie po zmierzeniu łożyska.
