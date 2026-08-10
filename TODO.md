# TODO / Roadmapa

Lista pomysłów zebrana 2026-08-10. Nieoznaczone = do zrobienia, `[x]` = zrobione, `[~]` = częściowo/wymaga decyzji.

## Decyzje (2026-08-10)

- Licencja: **GPL-3.0**
- Struktura magazynu: **pełna hierarchia regał → szuflada → skrytka** (duży projekt, wymaga przeprojektowania modelu danych/API/UI/obu appek — patrz sekcja niżej)
- Konto dewelopera Google Play: **jeszcze nie założone** przez użytkownika — publikacja w Play wstrzymana do tego czasu
- Kolejność prac: **1) wersjonowanie/aktualizacje (w toku)**, 2) reszta wg priorytetów niżej

## Otwarte źródło / Google Play

- [x] Dodać plik `LICENSE` (**GPL-3.0** — zrobione 2026-08-10, oficjalny tekst z gnu.org)
- [x] Repo publiczne na GitHubie (`dominikmaslak11/magazyn-lozysk`)
- [x] Rozbudować `README.md` (root) — zrobione 2026-08-10: spis treści, diagram architektury, szybki start od `git clone`, tabela struktury repo, sekcja bezpieczeństwa, link do GitHub Issues
- [ ] Karta sklepu Google Play (opis, grafiki, polityka prywatności) — dopiero gdy appka będzie gotowa do publikacji
- [ ] Konto dewelopera Google Play (użytkownik zakłada sam — wymaga płatności/danych osobowych)
- [ ] Podpisany build AAB appki `android-offline` do uploadu
- [ ] Uwaga: appka zależna od własnego serwera domowego (Wi-Fi/Tailscale) — do przemyślenia, jak to wygląda dla kogoś, kto ściągnie appkę z Play bez posiadania takiego serwera (tryb czysto offline musi działać sensownie sam z siebie)

## Funkcje aplikacji

- [~] **Skanowanie kodów kreskowych/QR** (CameraX + ML Kit) do szybkiego wyszukania łożyska po symbolu
  - [x] Ekran skanera w `android-offline` (`BarcodeScanner.kt`) — CameraX + ML Kit, rozpoznawanie w pełni
    on-device (obraz nie opuszcza telefonu), uprawnienie do aparatu proszone dopiero przy pierwszym użyciu
  - [x] Po zeskanowaniu otwiera się arkusz dodawania łożyska z wpisanym symbolem i automatycznie
    dociągniętymi wymiarami — reużywa istniejącego `lookupBySymbol` (ta sama ścieżka co „Pobierz wymiary”)
  - [x] Zbudowane i zweryfikowane (`assembleDebug`, uprawnienie CAMERA scalone w manifeście)
  - [ ] **Nie przetestowane na fizycznym telefonie** — do zrobienia przy najbliższej okazji (czy odczyt
    z realnych etykiet działa, czy autofocus daje radę z małym drukiem)
  - [x] Generowanie naklejek QR do PDF (`pdf_labels.py` + `/api/export/bearing-qr-labels-pdf`) — arkusz A4,
    3x8 naklejek, każda z QR (koduje symbol), wymiarami i regałem. Zweryfikowane dekoderami (pyzbar+OpenCV):
    moduł 0,96 mm, sam kod 20,2 mm — ~3x powyżej progu czytelności dla aparatu telefonu
  - [ ] Rozważyć: skanowanie z poziomu wyszukiwarki (skanuj → od razu filtruj listę, zamiast dodawać nowe)
  - [ ] **Naklejki tylko dla wybranych łożysk** — teraz arkusz generuje ZAWSZE wszystkie pozycje, więc po
    dodaniu 3 nowych łożysk trzeba wygenerować cały arkusz i wyciąć z niego 3 sztuki (reszta papieru się
    marnuje). Przydałby się wybór pozycji albo filtr „dodane po dacie”
  - [ ] Opcjonalnie: dopasowanie siatki do arkuszy samoprzylepnych z wykrojnikiem (Avery L7159 itp.).
    Świadomie odłożone — obecny arkusz jest pod nożyczki + papier pełnopowierzchniowy (bez wykrojnika)
  - Uwaga: rozmiar APK urósł z ~5 MB do ~40 MB (wbudowany model ML Kit). Alternatywa to wersja
    „unbundled” przez Google Play Services (mniejsze APK, ale wymaga Play Services i pierwszego pobrania
    modelu online) — świadomie wybrano wersję offline-first
  - Nie dotyczy `android-klient` (appka wygaszona)
- [x] **Tablica skojarzeń kod kreskowy → symbol** (zrobione 2026-08-10)
  - [x] Serwer: tabela `barcode_aliases` + migracja v2→v3 (dokłada pustą tabelę, nie rusza danych),
    CRUD, endpointy `/api/barcode-aliases` (GET/POST/DELETE) i `/api/barcode-lookup/<kod>`
  - [x] Włączone do synchronizacji (`sync_state` / `apply_sync_push`), z obsługą kolizji: ten sam kod
    skojarzony niezależnie na dwóch telefonach offline → ostatni wygrywa, starszy zostaje nagrobkiem
    (bez wywalenia się na unikalnym indeksie)
  - [x] Android: encja Room + DAO + **prawdziwa migracja v2→v3** (NIE destrukcyjna — inaczej zginęłyby
    zmiany zrobione offline i jeszcze niewypchnięte na serwer)
  - [x] Appka rozróżnia format kodu: EAN_13/EAN_8/UPC_A/UPC_E = kod handlowy (pytaj), reszta = symbol wprost
  - [x] Dialog „Nieznany kod z opakowania” — pyta raz, zapamiętuje, synchronizuje
  - [x] UI webowe (Dane → „Zapamiętane kody z opakowań”) do podglądu i kasowania błędnych skojarzeń —
    bez tego literówka w symbolu byłaby nie do naprawienia z poziomu telefonu
  - [x] Zgodność wstecz zweryfikowana: stary klient (bez pola `barcode_aliases`) nie wywala serwera
    i nie kasuje aliasów; nowy klient wobec starego serwera zostawia lokalne skojarzenia w spokoju
  - [ ] **Nie przetestowane na fizycznym telefonie** (jak cała funkcja skanowania)
  - Celowo BEZ zewnętrznych baz GTIN — dla łożysk są płatne i niekompletne; system uczy się sam
- [x] **Mechanizm weryfikacji wersji / wymuszania aktualizacji** (zrobione 2026-08-10)
  - [x] Plik `VERSION` (root) + stałe `APP_VERSION`/`MIN_CLIENT_VERSION` i endpoint `GET /api/version` w `server.py`,
    `server_version`/`min_client_version` dołączone też do `/api/sync/state` i `/api/sync/push`
  - [x] `android-offline`: `sync/VersionCheck.kt` (porównanie semver), `SyncEngine` blokuje nadpisanie lokalnej
    bazy i zwraca `SyncResult.UpdateRequired` gdy appka starsza niż `min_client_version` (lokalne zmiany i tak
    zdążyły się wcześniej wypchnąć na serwer — nic nie ginie)
  - [x] Baner w UI (`MainActivity.kt`) — czerwony/blokujący gdy `updateRequired`, łagodny gdy tylko
    `updateAvailable` — z przyciskiem do strony wydań na GitHubie (`RELEASES_URL`)
  - [x] Zasada: **blokuje tylko synchronizację, nigdy działanie appki offline**
  - Świadomie NIE dotyczy wersji webowej/PWA — ta zawsze serwuje się świeża prosto z `server.py`, więc
    "stara wersja" tam nie występuje
  - Nie dotyczy `android-klient` (appka wygaszona/zastąpiona przez `android-offline`)
  - Pozostaje do zrobienia przy publikacji w Play: appka **z automatu ma się aktualizować przez sam Play
    Store** — ten mechanizm to dodatkowe zabezpieczenie przed niekompatybilnością starego klienta z nowszym
    API serwera, nie zamiennik mechanizmu Play
- [ ] **Konfigurowalna hierarchia lokalizacji** (zaktualizowana decyzja z 2026-08-10, patrz rozmowa)
  - Zamiast sztywnych 3 tabel (regał/szuflada/skrytka): **jedna samo-referencyjna tabela `locations`**
    (`id`, `parent_id` nullable, `nazwa`, `poziom_etykieta` np. "regał"/"półka"/"szuflada"/"skrytka",
    `d_min`/`d_max` tylko na poziomie liściastym używanym do auto-przydziału).
  - Użytkownik sam wybiera **głębokość zagnieżdżenia** (0 = płasko jak dziś, 1 = regał+półka,
    2 = regał+szuflada+skrytka, itd.) — bez zmiany schematu przy każdej kombinacji.
  - `bearings.regal_id` → `bearings.location_id`, wskazuje na dowolny węzeł drzewa (nie musi być liściem).
  - Migracja v2 → v3: istniejące `shelves` stają się węzłami `locations` bez rodzica (poziom 0) — dla
    obecnych użytkowników (w tym Dominika) nic się nie zmienia funkcjonalnie, bo "wystarcza jak do tej pory".
  - API: CRUD na `locations` (dodaj/usuń/przenieś węzeł na dowolnym poziomie).
  - UI webowe: drzewo/breadcrumb zamiast płaskiej listy, ale **tylko gdy użytkownik włączy głębsze poziomy**
    — domyślny widok ma zostać tak prosty jak teraz.
  - Android (`android-offline`): aktualizacja encji Room (jedna tabela `LocationEntity` zamiast `ShelfEntity`)
    + ekranu wyboru lokalizacji (drzewo) + silnika sync pod nową tabelę.
  - `pdf_labels.py`: etykiety per najniższy skonfigurowany poziom.
  - To osobny, wieloetapowy projekt — rozbić na mniejsze PR-y, nie robić jednym skokiem. **Niski priorytet
    dla Dominika osobiście** (obecna płaska struktura mu wystarcza) — robione głównie z myślą o innych
    użytkownikach po publikacji open source.

## Uwagi / ryzyka do pilnowania

- Appka nie ma obecnie żadnej autoryzacji na endpointach API serwera — jeśli appka trafia do publicznego Play Store i ma się łączyć z serwerami różnych ludzi przez internet (nie tylko lokalne Wi-Fi), warto rozważyć czy potrzebne jest jakiekolwiek zabezpieczenie dostępu do serwera.
