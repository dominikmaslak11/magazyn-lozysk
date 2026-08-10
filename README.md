# Magazyn Łożysk

> Uwaga dla anglojęzycznych odwiedzających: interfejs i dokumentacja tego
> projektu są po polsku (to system do zarządzania domowym/warsztatowym
> magazynem łożysk tocznych). *This project's UI and docs are in Polish —
> it's a small warehouse-management app for organizing bearing (rolling
> element bearing) stock by shelf/size.*

System do klasyfikacji, katalogowania i śledzenia łożysk tocznych w
magazynie (regały, przydział wg wymiarów, ilości sztuk). Open source na
licencji **[GPL-3.0](LICENSE)**.

## Spis treści

- [Funkcje](#funkcje)
- [Architektura](#architektura)
- [Szybki start](#szybki-start)
- [Struktura repozytorium](#struktura-repozytorium)
- [Aplikacja webowa (PWA)](#aplikacja-webowa-pwa)
- [Appki Android](#appki-android)
- [Jak to działa](#jak-to-działa)
- [Synchronizacja i tryb offline](#synchronizacja-i-tryb-offline)
- [Wersjonowanie i aktualizacje](#wersjonowanie-i-aktualizacje)
- [Backup, eksport i import](#backup-eksport-i-import)
- [Bezpieczeństwo](#bezpieczeństwo)
- [Wersja archiwalna (desktop)](#wersja-archiwalna-desktop)
- [Zgłaszanie błędów i pomysłów](#zgłaszanie-błędów-i-pomysłów)
- [Licencja](#licencja)

## Funkcje

- Katalogowanie łożysk: symbol, typ, wymiary (d/D/B), ilość sztuk, uwagi.
- Wbudowana baza ok. 250 najpopularniejszych rozmiarów (kulkowe zwykłe,
  stożkowe, wahliwe kulkowe, wahliwe baryłkowe, wstawkowe UC) + doszukiwanie
  wymiarów w internecie, gdy symbolu nie ma w bazie offline.
- Wyszukiwanie odwrotne: podajesz wymiary, appka podpowiada symbol.
- Skanowanie kodów QR i kreskowych aparatem (appka Android) – po zeskanowaniu
  otwiera się okno dodawania łożyska z automatycznie wypełnionym symbolem i
  dociągniętymi wymiarami. Rozpoznawanie w pełni offline (ML Kit on-device).
- Automatyczny przydział łożyska do regału na podstawie średnicy zewnętrznej
  (z możliwością ręcznego nadpisania).
- Generowanie etykiet regałów do druku (PDF).
- Trzy sposoby korzystania z tych samych danych: przeglądarka (komputer/
  telefon jako PWA), natywna appka Android działająca w pełni offline
  z automatyczną synchronizacją, oraz zarchiwizowana wersja desktopowa.
- Backup automatyczny (przy starcie serwera i przed importem) oraz ręczny
  eksport/import do pliku JSON.
- Mechanizm wersjonowania appki Android (patrz [niżej](#wersjonowanie-i-aktualizacje)).

## Architektura

```
                       ┌─────────────────────────┐
                       │   server.py (Flask)     │
                       │   ~/.lozyska_data/*.db  │  ← jedyne źródło prawdy
                       │   SQLite, REST API      │
                       └───────────┬─────────────┘
                                   │  HTTP (Wi-Fi lokalne albo Tailscale)
              ┌────────────────────┼────────────────────┐
              │                    │                     │
      ┌───────▼────────┐  ┌────────▼─────────┐  ┌────────▼─────────┐
      │  Przeglądarka   │  │  android-offline │  │  android-klient  │
      │  (PWA, static/  │  │  Room/SQLite     │  │  (wygaszona,     │
      │  + templates/)  │  │  lokalnie na     │  │  bez własnej     │
      │  bez własnej    │  │  telefonie,      │  │  bazy - zawsze   │
      │  bazy - zawsze  │  │  działa offline, │  │  wymaga          │
      │  online         │  │  sync w tle      │  │  połączenia)     │
      └─────────────────┘  └──────────────────┘  └──────────────────┘
```

Serwer (`server.py` + `database.py`, SQLite) jest zawsze jedynym źródłem
prawdy. Appka `android-offline` trzyma pełną kopię danych lokalnie w Room i
synchronizuje się z serwerem, gdy jest połączenie - działa w pełni offline
między synchronizacjami. Wersja webowa nie ma własnej bazy, więc zawsze
wymaga połączenia z serwerem (na tym samym komputerze albo w tej samej
sieci). `android-klient` to starsza appka, zastąpiona przez
`android-offline` - zostawiona w repo jako punkt odniesienia.

## Szybki start

Wymagania: **Python 3.10+**. (Rozwijane i testowane na Pythonie 3.13.)

```bash
git clone https://github.com/dominikmaslak11/magazyn-lozysk.git
cd magazyn-lozysk
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

Serwer nasłuchuje na `0.0.0.0:8420` – w konsoli zobaczysz adres IP
komputera, pod którym appka jest dostępna z telefonu w tej samej sieci
Wi-Fi (np. `http://192.168.1.23:8420`). Otwórz ten adres w przeglądarce na
komputerze albo telefonie – to już cała instalacja.

## Struktura repozytorium

| Ścieżka | Co to jest |
|---|---|
| `server.py` | Serwer Flask - strony, REST API, synchronizacja |
| `database.py` | Warstwa dostępu do SQLite (schemat, migracje, sync) |
| `bearing_data.py` | Wbudowany katalog ok. 250 typowych rozmiarów łożysk |
| `lookup.py` | Doszukiwanie wymiarów w internecie, gdy symbolu nie ma w katalogu |
| `pdf_labels.py` | Generowanie etykiet regałów (PDF) |
| `templates/`, `static/` | Frontend PWA (HTML/CSS/JS, manifest, service worker) |
| `android-offline/` | Główna appka Android - offline-first + sync (Kotlin/Compose) |
| `android-klient/` | Starsza appka Android, wygaszona (bez własnej bazy) |
| `legacy_desktop_gui/` | Zarchiwizowana wersja desktopowa (CustomTkinter), nieutrzymywana |
| `VERSION` | Bieżąca wersja projektu (patrz [Wersjonowanie](#wersjonowanie-i-aktualizacje)) |
| `TODO.md` | Lista pomysłów i planowanych funkcji |

### Gdzie są dane

Baza danych (`lozyska.db`) leży w `~/.lozyska_data/` – **poza** katalogiem
z kodem, żeby aktualizacja/podmiana plików appki nigdy jej nie ruszyła.
Automatyczne kopie zapasowe (ostatnie 20) robią się przy każdym starcie
serwera oraz przed każdym importem, w `~/.lozyska_data/backups/`. Lokalizację
można nadpisać zmienną środowiskową `LOZYSKA_DATA_DIR`.

## Aplikacja webowa (PWA)

Po uruchomieniu `server.py` appka jest dostępna pod adresem serwera w
dowolnej przeglądarce. Na telefonie można dodać ją do ekranu głównego
(opcja „Dodaj do ekranu głównego”) – będzie działać jak natywna appka
(PWA, `static/manifest.json` + `static/service-worker.js`).

## Appki Android

Oba projekty Android są w tym repo (`android-klient/`, `android-offline/`)
i budują się przez Android Studio albo `./gradlew assembleDebug` z ich
własnych katalogów. Wymagania: JDK 17, Android SDK (compileSdk 34), Gradle
pobiera się automatycznie przez wrapper (`./gradlew`). Pliki APK nie są
trzymane w repo (patrz `.gitignore`) – zbuduj lokalnie:

```bash
cd android-offline        # albo android-klient
./gradlew assembleDebug
```

Plik wynikowy: `app/build/outputs/apk/debug/app-debug.apk`. Zainstaluj przez
`adb install -r <plik>` albo skopiuj na telefon i zainstaluj ręcznie
(wymaga zezwolenia na instalację z nieznanych źródeł, dopóki appka nie jest
w Google Play).

**android-offline** – główna appka mobilna: własna baza lokalna (działa w
pełni offline) + automatyczna synchronizacja z serwerem, gdy jest
połączenie (Wi-Fi albo przez Tailscale spoza domowej sieci). Pełne
szczegóły w [`android-offline/README.md`](android-offline/README.md).

**android-klient** – wygaszona, zastąpiona przez `android-offline`.
Wymaga stałego połączenia z serwerem (nie ma własnej bazy). Zostawiona w
repo jako punkt odniesienia.

## Jak to działa

Dotyczy wszystkich trzech wersji (web, obie appki Android) – korzystają z
tego samego modelu danych.

### Dodawanie łożyska

- **Znasz symbol** (np. `6008`, `UC206`, `30204`) → wpisz go i kliknij
  „Pobierz wymiary”. Program najpierw sprawdza wbudowaną bazę offline, a
  jeśli symbolu tam nie ma – próbuje doszukać wymiarów w internecie. Wyniki
  z internetu są wyraźnie oznaczone jako **orientacyjne** – warto je
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

## Synchronizacja i tryb offline

`android-offline` synchronizuje się z serwerem automatycznie przy otwarciu
i co ok. godzinę w tle, a lokalna baza na telefonie działa zawsze, także
bez internetu. Serwer jest jedynym źródłem prawdy – telefony nigdy nie
synchronizują się bezpośrednio między sobą. Pełny opis algorytmu,
rozstrzygania konfliktów i dostępu spoza domowej sieci (Tailscale) jest w
[`android-offline/README.md`](android-offline/README.md).

## Wersjonowanie i aktualizacje

Wersja projektu jest w pliku [`VERSION`](VERSION). Appka `android-offline`
sprawdza ją przy każdej synchronizacji z serwerem i – jeśli appka jest
zbyt stara względem `MIN_CLIENT_VERSION` w `server.py` – wstrzymuje dalszą
synchronizację (nie działanie offline) i pokazuje w appce baner z linkiem
do najnowszego wydania na GitHubie. Wersja webowa nie potrzebuje tego
mechanizmu, bo zawsze serwuje się świeża, prosto z `server.py`.

## Backup, eksport i import

- Automatyczne kopie zapasowe bazy: przy każdym starcie serwera i przed
  każdym importem (`~/.lozyska_data/backups/`, ostatnie 20).
- Ręczny eksport/import do pliku JSON (ten sam format we wszystkich trzech
  wersjach) – w zakładce „Dane”. Przydatne jako dodatkowa kopia zapasowa
  albo do przenoszenia danych między instalacjami.

## Bezpieczeństwo

Serwer **nie ma żadnej autoryzacji** – każdy, kto ma dostęp do sieci, w
której nasłuchuje (Wi-Fi domowe albo Twoja sieć Tailscale), może odczytać
i zmienić dane bez logowania. Dla domowego użytku w zaufanej sieci to
świadomy kompromis na rzecz prostoty. Jeśli wystawiasz serwer szerzej niż
własna sieć domowa/Tailscale, rozważ postawienie go za odwróconym proxy z
uwierzytelnianiem.

## Wersja archiwalna (desktop)

Stara wersja desktopowa (CustomTkinter) jest zarchiwizowana w
[`legacy_desktop_gui/`](legacy_desktop_gui/) – nieutrzymywana, zastąpiona
wersją webową, zostawiona jako punkt odniesienia. Może nie działać bez
poprawek (format bazy i moduł `lookup` zmieniły się od czasu, gdy była
aktywna).

## Zgłaszanie błędów i pomysłów

Błędy i propozycje funkcji zgłaszaj przez
[GitHub Issues](https://github.com/dominikmaslak11/magazyn-lozysk/issues)
tego repozytorium. Lista już zebranych pomysłów i planowanych zmian jest w
[`TODO.md`](TODO.md).

## Licencja

[GNU General Public License v3.0](LICENSE) – możesz swobodnie kopiować,
modyfikować i rozpowszechniać ten projekt, pod warunkiem że pochodne prace
zachowają tę samą licencję i pozostaną open source.
