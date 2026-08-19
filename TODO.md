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
- [ ] **`targetSdk = 34` prawdopodobnie za niski dla Play** — sklep wymaga świeższego API dla nowych
  aplikacji. Do zweryfikowania w Play Console PRZED pierwszym uploadem (progu nie da się sprawdzić z repo)
- [ ] **Rozmiar APK 40 MB** przez wbudowany model ML Kit. Dla Play sensowniejsza wersja „unbundled”
  (~5 MB) — Play Services są i tak na każdym telefonie ze sklepem. Dla prywatnego użytku Dominika lepsza
  jest obecna, w pełni offline. Może to być różnica między buildami (flavor), nie zamiana
- [ ] **Napięcie Play vs architektura**: appka jest dziś pomyślana wokół własnego serwera. Ktoś, kto pobierze
  ją ze sklepu, nie ma żadnego serwera, a pierwsze co zobaczy to zakładka o adresie serwera i tokenie.
  Żeby to miało sens w Play, tryb czysto offline musi być pełnoprawnym produktem, a synchronizacja —
  opcją dla zaawansowanych. To zmiana w podejściu/UI, nie w silniku

## Priorytety uzgodnione 2026-08-11

Kolejność wynika z analizy „co realnie boli”, nie z tego, co najciekawsze do napisania:

1. **Klasyfikator typu z oznaczenia** (w toku) — mały, samodzielny, wyraźny zysk
2. **Wyszukiwanie własnego magazynu po wymiarach** — największy realny brak (patrz niżej)
3. **Naprawa synchronizacji ilości** — cicha utrata danych, realna wada
4. **Rozbudowa katalogu offline** zamiast polegania na scrapingu

---

- [x] **Klasyfikator typu łożyska z oznaczenia (ISO 15 / ISO 355)** — ZROBIONE 2026-08-11
  - [x] `bearing_types.py` (serwer) + `BearingTypeClassifier.kt` (Android) — port 1:1, te same reguły
  - [x] Wpięte w `lookup.py` i `Repository.lookupBySymbol` — typ ustawia się także wtedy, gdy wymiary
    idą z internetu ALBO gdy w ogóle ich nie znaleziono
  - [x] `ALL_TYPES` / `TypLozyska` rozszerzone o: skośne, walcowe, oporowe, igiełkowe
  - [x] Testy po obu stronach (6/6 Python + 6/6 Kotlin), w tym **test zgodności ze wszystkimi 254 wpisami
    katalogu** — klasyfikator zgadza się z każdym znanym typem co do jednego
  - [x] Zwraca `None` zamiast zgadywać przy śmieciowym wejściu (min. 3 cyfry, jawna lista marek)
  - [x] **Przy okazji naprawiony realny błąd**: `normalize_symbol` obcinało `NU205` → `205`, przez co
    wyszukiwarka zwracała wymiary zupełnie innego łożyska (205×285×38 zamiast 25×52×15). Prefiksy
    literowe (NU/NJ/NA/HK/QJ...) są teraz zachowywane po obu stronach
  - [ ] **Nie przetestowane na fizycznym telefonie**
  - Poprzedni opis zadania (zostawiony dla kontekstu decyzji):
  - Problem: typ jest ustawiany automatycznie TYLKO gdy symbol trafi do wbudowanego katalogu (254 wpisy).
    Gdy go tam nie ma, `lookup.py` zwraca wymiary z internetu z `typ=None` i kategoria zostaje ta, która
    akurat była wybrana w formularzu.
  - Rozwiązanie: reguły na wzorcach oznaczeń — działa dla tysięcy symboli spoza katalogu, offline,
    deterministycznie (bez ML, bez internetu):
    `6xxx`/`16xxx` kulkowe · `7xxx` skośne · `32xx`/`33xx` (4 cyfry) skośne dwurzędowe ·
    `302xx`/`303xx`/`320xx`/`322xx` stożkowe · `12xx`/`13xx`/`22xx`/`23xx` (4 cyfry) wahliwe kulkowe ·
    `222xx`/`223xx`/`240xx` (5 cyfr) wahliwe baryłkowe · `NU`/`NJ`/`N`/`NUP`/`NN` walcowe ·
    `511xx`/`512xx` oporowe kulkowe · `HK`/`BK`/`NA`/`NKI` igiełkowe · `UC`/`UCP`/`UCF` wstawkowe
  - **PUŁAPKA do obsłużenia jawnie**: `3200` (4 cyfry) = skośne dwurzędowe, ale `30200` (5 cyfr) =
    stożkowe. Reguły muszą iść od najbardziej szczegółowej, inaczej `30204` zostanie źle zaklasyfikowane.
  - Katalog offline pozostaje nadrzędny — reguły działają dopiero, gdy symbolu w nim nie ma
  - Wymaga rozszerzenia `ALL_TYPES` o nowe kategorie (walcowe, skośne, oporowe, igiełkowe).
    `typ` to zwykły tekst w bazie, więc dodanie kategorii jest wstecznie zgodne
  - Ta sama logika musi trafić do appki Android (`Repository.lookupBySymbol`), nie tylko na serwer

- [ ] **Wymiary → kategoria: świadomie NIE robimy automatycznego wyboru**
  - Z samych trzech liczb NIE da się rzetelnie wyznaczyć typu — różne konstrukcje dzielą te same gabaryty.
    Automat dawałby pewnie brzmiące, czasem błędne odpowiedzi, a zła kategoria jest gorsza niż jej brak.
  - Co robimy zamiast: dopasowanie do katalogu + pokazanie typu **z widoczną niepewnością**
    („pasuje 6205 — kulkowe; pasuje też 5 innych”), jako propozycja, nie ciche ustawienie pola

- [x] **Wyszukiwanie własnego magazynu po wymiarach** — ZROBIONE 2026-08-11
  - [x] Jedno pole rozpoznaje intencję samo: `6205` → symbol, `25x52` → wymiary. Bez przełącznika w UI
  - [x] Składnia: `25x52`, `25x52x15`, `x52` (samo D), `25x` (samo d), `25 52 15`; tolerancja ±0,6 mm
  - [x] `SearchQuery.kt` (Android) + `search_query.py` (serwer) — port 1:1, 8 testów po każdej stronie
  - [x] Zweryfikowana **równoważność wyników** serwer vs telefon na tym samym zbiorze danych (0 rozbieżności)
  - [x] Przetestowane na fizycznym Samsungu (SM-M215F) — wpisanie `25x52` faktycznie zawęża listę,
    podpowiedź pokazuje rozpoznane wymiary
  - [x] Przy okazji: skrócona etykieta pola (zawijała się na dwie linie i zjadała miejsce na wyniki)
  - [x] Przy okazji: pusty wynik filtra mówi teraz „Nic nie pasuje do…” zamiast mylącego
    „Brak łożysk. Dodaj pierwsze przyciskiem +”

- [x] **Automatyczne przypisanie kategorii podczas WPISYWANIA symbolu** — ZROBIONE 2026-08-11
  - Klasyfikator istniał już od `fcde377`, ale uruchamiał się tylko przy „Pobierz wymiary” i przy skanie —
    samo wpisanie `NU205` w pole symbolu nie zmieniało kategorii
  - [x] Rozpoznawanie na bieżąco, przy każdym znaku (lokalne, bez sieci)
  - [x] Ręczny wybór typu z listy wyłącza automat (jak przy ręcznym przydziale regału)
  - [x] Przy edycji istniejącego łożyska zapisany typ inny niż wynikający z oznaczenia jest traktowany
        jak świadoma decyzja i nie zostaje nadpisany przy poprawce literówki
  - [x] Pole Symbol przeniesione NAD listę typów — czyta się naturalnie (najpierw przyczyna, potem skutek)
  - [x] Przetestowane na Samsungu: `NU205`→walcowe, `3204`→skośne, `30204`→stożkowe, `22205`→baryłkowe,
        `2205`→wahliwe kulkowe, `HK1010`→igiełkowe, `SKF 6205`→kulkowe, `nu 205 ecp`→walcowe

- [ ] **Naprawa synchronizacji ilości (realna, cicha utrata danych)**
  - Reguła „ostatni wygrywa” jest OK dla nazwy czy uwag, ale NIE dla licznika. Gdy jedna osoba weźmie
    offline 2 sztuki, a druga 1, po synchronizacji jedna ze zmian zniknie bez śladu — stan się nie zgodzi
    i nie da się dojść dlaczego.
  - Rozwiązanie: dla `ilosc` synchronizacja różnicowa (±2, ±1) zamiast nadpisania wartością
  - Przy okazji warto rozważyć historię zmian ilości („kto, kiedy, ile wziął”) i alert niskiego stanu

- [x] **Odsiewanie błędnych wymiarów z internetu** — ZROBIONE 2026-08-12
  - Problem realny, nie teoretyczny: w bazie Dominika łożysko `6204` miało zapisane 60×80×0 mm
    zamiast prawdziwych 20×47×14 — wynik scrapingu wyglądający w magazynie na prawdziwe dane
  - Rozwiązanie: oznaczenie samo koduje otwór (ISO 15) — dwie ostatnie cyfry to kod otworu,
    d = kod × 5 mm (wyjątki 00/01/02/03 = 10/12/15/17). `6204` → 20 mm, `NU205` → 25, `UC206` → 30
  - `bore_from_symbol()` + `dimensions_are_plausible()` po obu stronach (Python + Kotlin, port 1:1);
    wynik z sieci niezgodny z oznaczeniem jest ODRZUCANY, a użytkownik dostaje komunikat
    „otwór powinien mieć ok. X mm” zamiast cichego zapisania bzdury
  - Sprawdzana też podstawowa geometria: 0 < d < D oraz B > 0
  - Reguła zweryfikowana na **251 z 254 wpisów katalogu, 0 niezgodności**; pomijane są wyłącznie
    3 rzeczywiście niejednoznaczne (gołe 3-cyfrowe `126`/`127`/`129`, gdzie kod otworu nie obowiązuje)
  - Świadomie NIE stosujemy reguły do serii igiełkowych (HK/BK/NA) i calowych — lepiej nie sprawdzać
    niż sprawdzić źle
  - [x] Poprawiony rekord `6204` w bazie Dominika (20×47×14, regał przydzielony automatycznie),
        poprawka rozsynchronizowana na telefony

- [ ] **Rozbudowa katalogu offline zamiast scrapingu**
  - `OnlineLookup` opiera się na regexie po HTML DuckDuckGo — to się zepsuje przy zmianie layoutu,
    blokadzie albo CAPTCHA, a dla appki w Play jest dodatkowo ryzykowne regulaminowo
  - Tablice wymiarów ISO są skończone i publiczne — 254 wpisy można rozbudować do kilku tysięcy
  - Wolniej w przygotowaniu, ale odporne i naprawdę offline

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

- [x] **Zabezpieczenie API serwera tokenem** (zrobione 2026-08-10)
  - [x] Token generowany automatycznie przy pierwszym starcie, zapisany w `~/.lozyska_data/token.txt`
    (chmod 600, poza katalogiem z kodem) i wypisywany w konsoli przy każdym starcie
  - [x] Wszystkie `/api/*` wymagają tokenu (`X-Auth-Token` albo `Authorization: Bearer`), porównanie
    przez `secrets.compare_digest` (stały czas — brak wycieku przez pomiar czasu odpowiedzi)
  - [x] Wersja webowa: strona `/login` + sesja w ciasteczku, `/logout`; klucz sesji wyprowadzony z tokenu,
    więc restart serwera nie wylogowuje, ale zmiana tokenu unieważnia sesje
  - [x] Świadome wyjątki bez tokenu: `/api/version` (appka sprawdza zgodność wersji zanim się
    uwierzytelni), pliki statyczne, manifest, service worker, `/login`
  - [x] Android: pole „Token dostępu” w zakładce Dane, nagłówek przez interceptor OkHttp,
    czytelny komunikat przy 401 zamiast surowego błędu HTTP; `SyncWorker` nie ponawia w kółko przy 401
  - [x] Wyłącznik `LOZYSKA_AUTH_DISABLED=1` dla w pełni zaufanej sieci
  - [ ] **Nie przetestowane na fizycznym telefonie** — do sprawdzenia razem z resztą funkcji skanowania

## Uwagi / ryzyka do pilnowania

- Ruch idzie po HTTP, nie HTTPS. W lokalnym Wi-Fi albo przez Tailscale (który sam szyfruje) to w porządku,
  ale przy wystawianiu serwera do internetu trzeba postawić go za odwróconym proxy z TLS. Token chroni
  przed przypadkowym dostępem z tej samej sieci, nie przed podsłuchem nieszyfrowanego połączenia.
- Token jest współdzielony (jeden dla wszystkich urządzeń) — nie da się odebrać dostępu jednemu telefonowi
  bez zmiany tokenu na wszystkich. Świadomy kompromis; wystarczający dla prywatnego magazynu.

- [x] **BŁĄD: skasowane łożyska wracały na telefon** — naprawione 2026-08-15
  - Objaw: łożyska `6008` i `UC211` skasowane 8 sierpnia nadal widniały na liście w telefonie,
    mimo że na serwerze były prawidłowo oznaczone jako nagrobki (`deleted_at`)
  - Przyczyna: `SyncModels.kt` przy konwersji DTO → encja ustawiał `deletedAt` **zawsze na null**,
    więc nagrobek z serwera stawał się zwykłym, aktywnym rekordem i przechodził przez filtr
    w `Repository.replaceAllFromServer`
  - Dotyczyło wszystkich trzech typów rekordów: łożysk, regałów i aliasów kodów kreskowych
  - Test regresyjny `SyncModelsTest.kt` (4 przypadki) — bez niego łatwo to przywrócić
  - Potwierdzone na fizycznym Samsungu: po poprawce lista pokazuje wyłącznie `6204`
  - Uwaga na przyszłość: dane NIE ginęły — serwer przez cały czas trzymał poprawny stan,
    błąd był wyłącznie po stronie odczytu na telefonie

## Autostart serwera

- [x] **Usługa systemd użytkownika** — skonfigurowana 2026-08-14
  - `~/.config/systemd/user/magazyn-lozysk.service`, `enable --now`, `Restart=on-failure`
  - Włączony `loginctl enable-linger` — serwer startuje po restarcie laptopa BEZ logowania
    i przeżywa wylogowanie (bez tego usługi użytkownika giną po zamknięciu sesji)
  - Logi: `journalctl --user -u magazyn-lozysk -f`
  - Token przetrwał restart (leży w pliku), więc telefony nie wymagały przekonfigurowania

- [x] **Ruchy magazynowe zamiast nadpisywania ilości** — ZROBIONE 2026-08-15 (priorytet #3)
  - Problem: ilość to LICZNIK, a reguła „ostatni wygrywa” po cichu gubiła zmiany. Gdy jedna osoba
    wzięła offline 2 szt., a druga 1, jedna z tych zmian znikała bez śladu i stan się nie zgadzał.
  - Rozwiązanie: każda zmiana ilości to RUCH (delta) z własnym id; serwer je sumuje
  - [x] Serwer: tabela `stock_moves` + migracja v3→v4, stosowanie delt w `apply_sync_push`
  - [x] **Idempotencja**: serwer deduplikuje po id ruchu, więc ponowna wysyłka po zerwanym
        połączeniu nie policzy zmiany dwa razy (bez tego naprawa jednego błędu wprowadziłaby drugi)
  - [x] Android: `StockMoveEntity` + DAO + prawdziwa migracja Room 3→4; ruchy kasowane dopiero
        PO potwierdzeniu synchronizacji, więc zerwane połączenie nie gubi zmiany stanu
  - [x] Ruch dodany w trakcie synchronizacji jest ponownie nakładany na świeży stan
        (`reapplyPendingMoves`), żeby nie zniknął z ekranu do następnej rundy
  - [x] Edycja ilości w przeglądarce też idzie przez dziennik — reguła „ilość zmienia się
        WYŁĄCZNIE ruchami” nie ma wyjątków, więc historia jest kompletna
  - [x] Stan nie schodzi poniżej zera
  - [x] `MIN_CLIENT_VERSION` podniesiona do 1.2.0 — stara appka (1.1.0) wysyła ilość jako wartość
        bezwzględną, którą serwer teraz ignoruje, więc lepiej żeby ODMÓWIŁA synchronizacji
        (baner „zaktualizuj”) niż miała po cichu gubić zmiany
  - [x] Historia ruchów widoczna w wersji webowej (Dane → „Historia ruchów magazynowych”)
  - [x] Przetestowane na fizycznym Samsungu: +3 z telefonu i -1 z przeglądarki dały 3 (nie 4),
        telefon i serwer zbiegły do tej samej wartości

- [x] **Szybkie +/- na liście łożysk** — ZROBIONE 2026-08-15
  - Wydanie/przyjęcie sztuki to najczęstsza czynność w warsztacie — teraz jedno tapnięcie
    zamiast otwierania arkusza edycji, zmiany pól i zapisu
  - Przycisk „-” jest wyłączony przy stanie 0

## Asystent AI (2026-08-17)

- [x] **Podpowiedzi wymiarów od modeli AI** (`ai_assist.py`, `/api/ai/lookup`)
  - Cztery usługi równolegle: Claude (`claude-opus-5`), Gemini, DeepSeek, OpenAI
  - **Każda odpowiedź przechodzi tę samą walidację co scraping**: kod otworu ISO 15 +
    geometria (`dimensions_are_plausible`). Zweryfikowane testem z podstawionym „kłamcą":
    model podał 60×80×18 dla 6204 → ODRZUCONE, wynik końcowy pozostał poprawny
  - Uzgadnianie: liczy się zgodność kilku niezależnych modeli, nie deklarowana pewność
  - Sprawdzone na oznaczeniach spoza katalogu: `NU2210` 50×90×23 ✓, `7208B` 40×80×18 ✓
- [x] **Asystent-czat** (`/api/ai/chat`), domyślnie **najnowszy Claude** (`claude-opus-5`),
  przełączalny na pozostałych dostawców; zakładka „Asystent" w wersji webowej
  - Dostaje zwięzły spis magazynu, żeby odpowiadać konkretnie („czy mam coś 55 mm?")
- [x] **Bezpieczeństwo kluczy**: `~/.lozyska_data/ai_keys.json` (chmod 600, poza repo).
  `.gitignore` rozszerzony o wzorce kluczy. Telefon NIGDY nie widzi kluczy — pyta własny
  serwer. Świadoma odmowa „zaszycia kluczy w aplikacji": repo jest publiczne, a APK da
  się rozpakować w minutę
- [x] Klasyfikator: dodana seria **202xx/203xx (baryłkowe)** — realny przypadek z magazynu
  (`20211` dostawało domyślne „kulkowe zwykłe")
- [ ] **Czat w appce Android** — na razie tylko wersja webowa i przycisk „Zapytaj AI"
      w arkuszu dodawania
- [ ] Prywatność: spis magazynu wychodzi do dostawcy AI. Jest przełącznik `bez_magazynu`
      w API, ale nie ma go jeszcze w UI

## Konfigurowalna hierarchia regał → półka → szuflada → skrytka (poprosił 2026-08-17)

- [ ] **DUŻY PROJEKT — nie zaczęty.** Wymaga: samo-referencyjnej tabeli `locations`
      (`parent_id`), migracji v4→v5 zachowującej obecne 9 regałów, CRUD w API, drzewa
      w UI webowym, encji Room + ekranu wyboru w appce, przeprojektowania sync-u
      i etykiet PDF. Szczegóły projektu w sekcji „Konfigurowalna hierarchia lokalizacji"
      wyżej — to jedyna pozycja, która nie zmieściła się w tej sesji

## Hierarchia lokalizacji — ZROBIONE 2026-08-17

- [x] **Konfigurowalna hierarchia regał → półka → szuflada → skrytka**
  - Kluczowa decyzja: NIE nowa tabela, tylko `parent_id` + `poziom_typ` w istniejącej
    `shelves`. Dzięki temu `bearings.regal_id` działa bez zmian dla DOWOLNEGO węzła,
    a synchronizacja i encja Room wymagały dwóch pól zamiast przeprojektowania.
  - **Hierarchia jest niesymetryczna i opcjonalna**: regał może mieć pełne cztery
    poziomy, samą skrytkę wprost pod sobą, albo nic (zweryfikowane testem)
  - Migracja serwera v4→v5 i Room v4→v5 — dotychczasowe 9 regałów zostało korzeniami,
    zero utraty danych
  - Skasowanie węzła kasuje potomków, ale **NIE kasuje łożysk** — tracą tylko
    przypisanie (zweryfikowane: 6208 przetrwało z ilością 2)
  - Usunięty unikalny indeks na `poziom` — w drzewie numery powtarzają się między
    gałęziami i blokowałby dodawanie dzieci
  - Starszy klient nie spłaszczy hierarchii: `parent_id` aktualizowane tylko wtedy,
    gdy klient je przysłał
  - UI webowe: drzewo z wcięciami, „+ półka/szuflada/skrytka" na każdym poziomie
  - Android: wybór lokalizacji pokazuje pełną ścieżkę „Regał 3 › Półka 2 › Skrytka A"
- [ ] Etykiety PDF nadal drukują samą nazwę węzła, nie pełną ścieżkę
- [ ] Brak przenoszenia węzła między rodzicami (trzeba skasować i utworzyć na nowo)

## Dobór lokalizacji po typie + widok drzewa (2026-08-17)

- [x] **Typ ma pierwszeństwo przed średnicą** przy automatycznym doborze lokalizacji
  - Nowe pole `typy` w lokalizacji: przypisujesz np. „wstawkowe (UC)" i wszystkie UC/ES
    trafiają tam **niezależnie od średnicy** (sprawdzone: UC206 D=62, ES205 D=52,
    UCP211 D=100 → ta sama półka, a 6205 dalej sortuje się po średnicy)
  - Kolejność: typ+średnica → sam typ (najgłębsza lokalizacja) → ogólna wg średnicy →
    skrajna ogólna. Puste `typy` = lokalizacja ogólna, zachowanie jak dotąd
  - Klasyfikator poznaje serię **ES/ESP** (wstawkowe) — wcześniej zwracał „nie wiem"
  - Migracje v5→v6 po obu stronach
- [x] **Widok drzewa per regał**: wybór regału z listy, zwijanie gałęzi, stan zapamiętany
      w przeglądarce
- [x] **Sumy zbiorcze**: regał pokazuje ile leży w CAŁEJ gałęzi, nie tylko wprost na nim
      (bez tego regał ze wszystkim w skrytkach pokazywał 0 szt.)
- [x] Zakładka Dane rozbita na 7 składanych sekcji — świadoma alternatywa dla hamburgera
      (przy 4 zakładkach hamburger chowałby nawigację za dodatkowym tapnięciem)
- [ ] Brak UI do przypisywania typów w appce Android (jest w wersji webowej)

## Podpowiedzi przełożenia łożysk (2026-08-17)

- [x] **Deterministyczny rdzeń** (`sugestie_przeniesien`, `/api/suggestions`)
  - Porównuje obecną lokalizację z wyliczoną tymi samymi regułami co przy dodawaniu
    (typ + średnica). ZERO udziału AI — dzięki temu podpowiedź jest zawsze spójna,
    natychmiastowa i działa bez internetu
  - Sortowanie po liczbie sztuk: przeniesienie 10 szt. porządkuje magazyn bardziej niż jednej
  - Pozycje ustawione ręcznie NIE są pomijane (użytkownik kładzie „gdzie było miejsce"
    i właśnie o tym chce wiedzieć), ale są oznaczone flagą `reczny`
- [x] **Żółte podświetlenie + adnotacja** na karcie łożyska w wersji webowej, z powodem
      („średnica 47 mm mieści się w zakresie 42-55 mm") i przyciskiem „Przenieś"
- [x] **Asystent AI dostaje gotową listę** i opowiada o niej w rozmowie. Model NIE decyduje,
      co leży źle — tylko formułuje; inaczej przy tym samym magazynie dawałby różne odpowiedzi
- [ ] Brak podświetlenia i dymka w appce Android (na razie tylko wersja webowa)
- [ ] Brak „odrzuć tę sugestię na stałe" — pozycja świadomie zostawiona gdzie indziej
      będzie się podświetlać w kółko

## Scalanie zdublowanych i rozproszonych pozycji (2026-08-17)

- [x] **Wykrywanie dwóch RÓŻNYCH problemów** (`sugestie_scalenia`, `/api/consolidation`):
  - `duplikat` — ten sam symbol kilka razy w TEJ SAMEJ lokalizacji (błąd ewidencji)
  - `rozproszone` — ten sam symbol w RÓŻNYCH miejscach (błąd układu; patrząc na jedną
    półkę widzisz zaniżony stan i zamawiasz niepotrzebnie)
- [x] **Scalanie przez dziennik ruchów** (`scal_lozyska`) — sztuki nie są nadpisywane,
      tylko przenoszone ruchami, więc historia pozostaje kompletna i suma się zgadza
- [x] Czerwony baner nad listą + przycisk „Scal w jeden wpis"
- [x] **Naprawiony własny błąd**: pierwsza wersja przenosiła zduplikowany wpis do
      lokalizacji sugerowanej regułami, rozjeżdżając bazę z rzeczywistością (łożyska
      fizycznie leżały gdzie indziej). Duplikat zostaje TAM, GDZIE LEŻY
- [x] Na prawdziwych danych: 6203 (1+10 → 11 szt.) i 6208 (2+2 → 4 szt.), suma 15=15
- [ ] Brak wykrywania/scalania w appce Android (na razie wersja webowa)

## Wykrywanie niezgodności stanu (2026-08-17)

- [x] **Ustanowiony niezmiennik**: ilość łożyska == suma jego ruchów magazynowych.
      Wcześniej były DWIE ścieżki tworzenia — dodanie z telefonu zapisywało ruch,
      a z przeglądarki ustawiało liczbę wprost — więc suma nigdy się nie zgadzała
      i alert byłby bezużyteczny. `add_bearing` zapisuje teraz „bilans otwarcia"
- [x] `niezgodnosci_stanu()` + `/api/inconsistencies`: pozycje, których stan nie ma
      pokrycia w dzienniku (starsza appka, przerwana synchronizacja, ręczna zmiana w bazie)
- [x] Komunikat wprost: „Przelicz ponownie 6005 w Regał 9: baza mówi 7 szt., a z historii
      ruchów wychodzi 10 szt. (różnica -3)"
- [x] Zatwierdzenie przeliczenia dopisuje ruch „inwentaryzacja" — korekta jest widoczna
      w historii, nie nadpisuje się po cichu
- [x] **Program NIE zgaduje, która liczba jest prawdziwa** — wymaga fizycznego przeliczenia.
      Automatyczne „naprawienie" bazy zamaskowałoby problem zamiast go pokazać
- [x] Naprawiony własny błąd: korekta liczona względem sumy ruchów była nakładana na
      (błędną) ilość w rekordzie — a te wartości różnią się dokładnie wtedy, gdy ta
      funkcja się uruchamia. Zatwierdzenie 7 szt. dawało 4
- [ ] Brak w appce Android (wersja webowa + kontekst asystenta AI)

## Progi magazynowe i wyszukiwanie po uwagach (2026-08-17)

- [x] **Progi na łożysku**: `stan_min`, `stan_opt`, `zapotrzebowanie` (roczne zużycie).
      Wystarczy podać samo roczne zużycie — progi wyliczą się same (opt = zużycie,
      min = połowa) — albo ustawić je ręcznie
- [x] **Trzy poziomy alertu** zamiast jednego, bo znaczą co innego:
      `brak` (0 szt., czerwony) · `pilne` (poniżej minimum, żółty) ·
      `nadmiar` (ponad optymalny, szary — to nie awaria, tylko zamrożone pieniądze)
- [x] Komunikat wprost: „Konieczne uzupełnienie jak najszybciej: 6205 (wał corncrackera)
      — zostało 1 szt. przy minimum 5. Domów 9 szt. do stanu optymalnego (10)."
- [x] Pilnowane są TYLKO pozycje z ustawionymi progami — inaczej cały magazyn
      krzyczałby od pierwszego dnia
- [x] **Wyszukiwanie obejmuje teraz uwagi** — wpisanie „corncracker" znajduje 6205.
      Pole uwag istniało od dawna, ale wyszukiwarka go nie przeszukiwała
- [x] Progi zapisywane osobnym wywołaniem (`/api/bearings/<id>/progi`) — to decyzja
      zaopatrzeniowa, oddzielona od danych technicznych łożyska
- [ ] Progi i alerty nie są jeszcze w appce Android ani w synchronizacji

## Progi i podpowiedzi w appce Android (2026-08-18, wersja 1.3.0)

Wariant B: reguły liczy WYŁĄCZNIE serwer, telefon wyświetla gotowy wynik.
Powód: dwa silniki reguł (Python + Kotlin) prędzej czy później zaczęłyby mówić
co innego o tym samym łożysku, a tego się potem nie odkręca. Cena: offline widać
stan wiedzy z ostatniej synchronizacji - dlatego wiek danych jest pokazany wprost.

- [x] Schemat v7 na telefonie: `stanMin`, `stanOpt`, `zapotrzebowanie` + migracja 6→7
      (prawdziwa migracja, nie czyszczenie bazy - dane offline zostają)
- [x] Progi jadą w OBIE strony; serwer zapisuje je tylko wtedy, gdy klient je przysłał,
      więc starsza appka nie wyzeruje progów ustawionych w przeglądarce
- [x] Wspólny, płaski format podpowiedzi (`powiadomienia()` w database.py) - jedna lista
      zamiast czterech osobnych; nowa reguła na serwerze nie wymaga aktualizacji appki
- [x] Pasek podpowiedzi nad listą, zwijany, z wiekiem danych ("dane z serwera, 6 min temu")
- [x] Żółte podświetlenie pozycji + adnotacja wprost na karcie, żeby kolor nie był zagadką
- [x] Pola progów w arkuszu edycji (wystarczy roczne zużycie)
- [x] Sprawdzone na Samsungu SM-M215F: migracja v6→v7 bez utraty danych, 11 podpowiedzi
      z serwera, próg wpisany na telefonie dotarł na serwer i wygenerował alert
- [ ] Limit podpowiedzi przeniesienia to sztywne 10 - przy pełnym magazynie może być za mało
- [ ] Brak "nie pokazuj więcej tej podpowiedzi"
- [ ] Czat AI na telefonie (punkt 4 planu)
- [ ] Scalanie duplikatów i potwierdzanie stanu z telefonu (punkt 3 planu)

## Plan porządkowania magazynu - PO wprowadzeniu wszystkich danych

Zamówione 2026-08-18: gdy wszystkie symbole, wymiary i ilości będą wpisane,
przygotować KOMPLETNY plan rozłożenia magazynu - co gdzie ma trafić i w jakiej
kolejności robić ruchy - a nie pojedyncze podpowiedzi pozycja po pozycji.

- [ ] Plan liczony na całości naraz: obłożenie regałów, a nie tylko dopasowanie
      pojedynczego łożyska do zakresu średnic (dziś regał może się teoretycznie przepełnić)
- [ ] Kolejność ruchów: najpierw zwolnić miejsce, potem je zająć
- [ ] Grupowanie po typie i symbolu (UC…, ES… razem; ten sam symbol nigdy w dwóch miejscach)
- [ ] Wydruk / lista do ręki na czas przekładania, z odhaczaniem

## Prawdziwe wymiary regałów i rachunek pojemności (2026-08-19, wersja 1.4.0)

Magazyn przestał być opisany wymyślonymi zakresami średnic ("regał 8 to 30-42 mm"),
a zaczął rzeczywistymi wymiarami półek zmierzonymi miarą.

- [x] Schemat v8: `szerokosc_mm`, `glebokosc_mm`, `wysokosc_mm` na lokalizacji
      (`wysokosc` = PRZEŚWIT do następnej półki, nie grubość deski)
- [x] Struktura zgodna z rzeczywistością: Regał 1 (7 półek, 88 cm szer.),
      Regał 2 (2 półki, 86×50; dolna ma 142 cm prześwitu), Regał 3 (4 półki 89×40×40,
      wysokość regulowana) - zamiast dziewięciu wymyślonych "regałów"
- [x] Wszystkie 22 pozycje przeniesione z "Regał 9" na faktyczne miejsce:
      **Regał 2 › Półka 2 (góra)**
- [x] `pojemnosc.py` - rachunek zapełnienia. Model: łożyska leżą płasko (kwadrat o boku D),
      sztuki tego samego symbolu w stosie, stos nie wyższy niż szeroki (stabilność),
      odstęp 3 cm na rękę między pozycjami, 5 cm zapasu nad stosem, 15% straty na krawędziach
- [x] Nowe podpowiedzi: "półka przepełniona" i "nie mieści się na tej półce"
- [x] Wyłączone podpowiedzi oparte na zakresach średnic - bez zadeklarowanego zakresu
      lokalizacja nie pasuje do niczego, zamiast łapać wszystko
- [x] Wymiary widoczne i edytowalne w wersji webowej (w cm), na telefonie do odczytu
- [x] **Naprawiony błąd spłaszczający hierarchię**: zapis regału z telefonu budował rekord
      od zera, więc kasował `parentId`, typ poziomu, dedykowane typy i wymiary - i taki
      rekord jechał na serwer. Test regresyjny: `ShelfEditTest`
- [x] Regał 3 oznaczony jako bufor tymczasowy (przenosiny nieposortowanej zawartości Regału 1)

### Do zrobienia

- [ ] Podział dolnej półki Regału 2 (142 cm prześwitu) - rachunek mówi: 7 poziomów co 20 cm,
      zysk 219 dm² (więcej niż połowa dzisiejszego magazynu)
- [ ] Plan rozłożenia całości: uwzględnić, że Regał 3 jest buforem i nie jest miejscem docelowym
- [ ] Model nie zna ciężaru - ciężkie łożyska powinny lądować nisko, na razie decyduje o tym człowiek
- [ ] Głębokie półki (58 cm) - do tylnego rzędu trudno sięgnąć, rachunek tego nie odróżnia

## Bufory na czas inwentury (2026-08-19, wersja 1.5.0)

- [x] Schemat v9: flaga `bufor` na lokalizacji (ptaszek w wersji webowej, znacznik na telefonie)
- [x] Flaga dziedziczy się z regału na jego półki - nie trzeba odhaczać każdej z osobna
- [x] Bufor NIE zgłasza przepełnienia ani "nie mieści się" - jest z założenia zapchany
      i alarmowanie o tym zagłuszałoby realne problemy
- [x] Zamiast tego jedno spokojne przypomnienie: ile pozycji czeka na rozłożenie
- [x] Pełna ścieżka lokalizacji ("📍 Regał 2 › Półka 2") na liście łożysk zamiast
      samej nazwy półki - nazwy powtarzają się między regałami
- [x] Granica smukłości stosu podniesiona z 1× na 2× średnicy - łożyska to precyzyjne
      pierścienie i układają się współosiowo; poprzednia wartość marnowała półki
- [ ] Model nie zna skrzynek - jeśli łożyska trafią w pojemniki, skrzynka powinna być
      kolejnym poziomem hierarchii z własnymi wymiarami

## Rozdzielenie serii UC i ES (2026-08-19, wersja 1.6.0)

UC208 i ES208 mają ten sam otwór (40 mm) i tę samą średnicę zewnętrzną (80 mm),
ale to dwie różne konstrukcje - jedna nie zastąpi drugiej w maszynie.

- [x] Osobny typ `wstawkowe (ES)` obok `wstawkowe (UC)`, po obu stronach (Python + Kotlin)
- [x] **Naprawiony błąd podmieniający część**: "ES208" redukowało się przy szukaniu
      wymiarów do "208", czyli do zwykłego łożyska kulkowego 40×80×18. Ta sama pułapka,
      co kiedyś przy NU205 → 205. Brakowało ES/ESP na liście przedrostków do zachowania
- [x] Przy okazji dopisane brakujące UCPH, UCX, CSA - były w regułach typów, ale nie
      w normalizacji symbolu
- [x] Testy regresyjne po obu stronach (`test_bearing_types.py`, `WstawkoweTest.kt`)
- [x] `wstawkowe (ES)` dodane do listy typów w interfejsie

### Otwarte

- [ ] **Wymiarów serii ES nie ma skąd wziąć**: katalog offline jej nie zna, a modele AI
      nie są zgodne (1 na 4, i wzajemnie sprzeczne między symbolami). Trzeba zmierzyć suwmiarką
- [ ] Łożyska wstawkowe mają WYSTAJĄCY pierścień wewnętrzny: leżąc płasko zajmują na
      wysokość szerokość pierścienia wewnętrznego (UC209: 49,2 mm), a nie zewnętrznego
      (19 mm). Rachunek pojemności bierze pole B, więc dla tej serii zaniża wysokość stosu

## Seria ES rozpoznana - dane od producenta (2026-08-19, wersja 1.7.0)

Ustalone w katalogu NTN-SNR (eshop.ntn-snr.com), nie zgadnięte:

- ES to łożyska WSTAWKOWE do opraw, z kulistą powierzchnią zewnętrzną - czyli
  samonastawne w oprawie, tak samo jak UC. Nie jest to inna rodzina.
- Różnica jest w MOCOWANIU NA WALE: ES ma mimośrodowy pierścień zaciskowy,
  UC dwa wkręty dociskowe. Stąd inna szerokość pierścienia wewnętrznego.
- ES208 = 40×80, ES209 = 45×85, ES210 = 50×90; pierścień wewnętrzny z zaciskowym
  ma 43,7 mm w całej serii; pierścień zewnętrzny kolejno 18 / 19 / 20 mm.
  Dla porównania UC208/UC209 mają pierścień wewnętrzny 49,2 mm.
- [x] Wpisy ES208/209/210 w katalogu offline (serwer + telefon)
- [x] Opis typu przy wyborze kategorii - czym UC różni się od ES

### Do rozstrzygnięcia

- [ ] **Którą szerokość wpisujemy dla wstawkowych?** Katalog trzyma pierścień
      WEWNĘTRZNY (UC209: 49,2 mm), a wpis użytkownika `uc209` ma 19 mm, czyli
      pierścień ZEWNĘTRZNY. Trzeba wybrać jedną konwencję - wewnętrzna jest właściwa
      dla układania na półce (ten pierścień wystaje i to on wyznacza wysokość stosu)
- [ ] Poprawić wpis `uc209` po ustaleniu konwencji

## Nazwa appki, 37431A, ptaszek weryfikacji i narzędzie audytu (2026-08-19, wersja 1.8.0)

- [x] Appka na telefonie nazywa się teraz **Magazyn Łożysk** (jak serwer, wersja webowa
      i wydruki naklejek). "Offline" to szczegół implementacyjny, nie nazwa produktu.
      Stary klient przemianowany na "Magazyn Łożysk (stary klient)", żeby nie mylił
- [x] **37431A rozpoznane**: to pierścień wewnętrzny (cone) calowego łożyska stożkowego
      Timken 37431A/37625 - otwór 109,538 mm, śr. stożka 132,745 mm, szer. 21,438 mm.
      Sam stożek jest bezużyteczny bez pierścienia zewnętrznego 37625 (śr. 158,75 mm).
      Źródło: cad.timken.com. Wpis w bazie poprawiony (było 110 × 110 × 22)
- [x] **Naprawiony błąd odwracający kontrolę sensowności**: reguła ISO "dwie ostatnie
      cyfry to kod otworu" była stosowana także do oznaczeń calowych. Dla 37431A dawała
      otwór 155 mm, więc program ODRZUCAŁ prawdziwe wymiary jako niepasujące
      i przyjmował fałszywe. Teraz: nie rozpoznajemy typu → nie twierdzimy nic o otworze
- [x] Nowy typ "stożkowe calowe (Timken)" - różni je nie konstrukcja, tylko system oznaczeń
- [x] Ptaszek **"do sprawdzenia"** na łożysku (schemat v10) + zbiorcze powiadomienie
- [x] **`audyt.py`** - narzędzie przeglądające całą bazę

### audyt.py - co robi

    python audyt.py              # raport
    python audyt.py --ai         # + zapytanie modeli, najpierw o pozycje z ptaszkiem
    python audyt.py --zastosuj   # zapisz poprawki PEWNE (wyłącznie z katalogu)

Sprawdza: wymiary wewnętrznie sprzeczne, zgodność z katalogiem, kod otworu wg ISO,
oznaczenia nie do rozpoznania regułami, brak średnicy zewnętrznej.
Propozycji AI NIE zapisuje nigdy - błędny wymiar w magazynie wygląda potem
dokładnie tak samo jak prawdziwy.

### Znalezione w bazie, do decyzji użytkownika

- [ ] **62205 ma otwór 52 mm i średnicę zewnętrzną 52 mm** - z oznaczenia wynika otwór
      25 mm. Albo symbol, albo wymiar jest błędny; trzeba zmierzyć
- [ ] **uc209 ma szerokość 19 mm, katalog podaje 49,2 mm** - to ta sama sprawa co
      konwencja szerokości przy wstawkowych (pierścień zewnętrzny kontra wewnętrzny)
- [ ] **"205"** - oznaczenie niepełne; modele zgodnie (4/4) podają 25 × 52 × 15 mm,
      czyli wymiary 6205. Do potwierdzenia suwmiarką

## Seria RAE (INA/Schaeffler) - trzecia konwencja oznaczeń (2026-08-19, wersja 1.9.0)

RAE35 to wstawkowe łożysko kulkowe INA, 35 × 72 × 39 mm, mocowane mimośrodowym
pierścieniem zaciskowym, z poszerzonym pierścieniem wewnętrznym z jednej strony.

**Najważniejsze dla programu:** liczba w oznaczeniu to WPROST otwór w milimetrach
(RAE35 = 35 mm), a nie kod otworu jak w ISO. Reguła ISO dałaby 35 × 5 = 175 mm,
czyli wynik pięciokrotnie zawyżony - i program odrzucałby prawdziwe wymiary jako
"niepasujące do oznaczenia". Ten sam mechanizm, który zepsuł 37431A.

W magazynie są więc już TRZY konwencje oznaczeń:
  * ISO metryczna   6205    -> kod "05" -> otwór 25 mm
  * calowa Timken   37431A  -> brak reguły, otwór trzeba znać z katalogu
  * INA             RAE35   -> otwór 35 mm wprost

- [x] Typ "wstawkowe (RAE/INA)" + reguły po obu stronach (Python i Kotlin)
- [x] RAE35 w katalogu offline
- [x] Testy: reguła otworu, kontrola sensowności, brak kolizji z igiełkowymi RNA/NA
- [x] Opis typu ostrzega o różnicy RAE (walcowy) kontra GRAE (kulisty)

### Do sprawdzenia przy regale

- [ ] **Czy to RAE czy GRAE?** Wg Schaefflera RAE ma pierścień zewnętrzny WALCOWY,
      a GRAE KULISTY - i tylko GRAE kompensuje niewspółosiowość wału, czyli jest
      samonastawne w oprawie. Sprzedawcy nagminnie opisują oba jako "spherical",
      więc trzeba obejrzeć: kulisty jest wybrzuszony beczkowato, walcowy prosty
- [ ] Pozostałe rozmiary serii RAE (30, 40, 45...) - w katalogu jest na razie tylko 35

## EX.208.G2 - kropki w oznaczeniu i seria EX (2026-08-19, wersja 1.10.0)

Zgłoszone przez użytkownika: appka na siłę podpowiadała "kulkowe zwykłe 208,
40×80×18", a w rzeczywistości EX 208 G2 SNR to wstawkowe samonastawne 40×80×56,3/21.

Dwie osobne przyczyny, obie naprawione:

- [x] **Kropka nie była separatorem.** SNR zapisuje oznaczenia jako "EX.208.G2", więc
      przedrostek się nie doklejał i całość redukowała się do gołego "208". Program
      podstawiał wymiary zwykłego łożyska kulkowego - a wyglądały wiarygodnie, bo otwór
      i średnica zewnętrzna faktycznie się zgadzają. Poprawione w czterech miejscach:
      `bearing_types.py`, `lookup.py`, `BearingTypeClassifier.kt`, `Repository.kt`
- [x] **Brak serii EX w regułach.** Nowy typ "wstawkowe (EX/SNR)" + wpis EX208 (40×80×56,3)
- [x] Przy okazji dołożone pozostałe rodziny wstawkowych, żeby nie powtórzyły tej samej
      pułapki: SNR US/UEL/USFE, SKF YEL/YET/YAR
- [x] Testy regresyjne po obu stronach, w tym test pilnujący, że UC208, ES208 i EX208
      mają trzy różne typy i trzy różne szerokości

Trzy wstawkowe o tych samych gabarytach 40 × 80 mm, ale to trzy różne części:

| symbol | szer. całkowita | mocowanie |
|--------|-----------------|-----------|
| UC208  | 49,2 mm         | dwa wkręty dociskowe |
| ES208  | 43,7 mm         | mimośrodowy pierścień |
| EX208  | 56,3 mm         | mimośrodowy pierścień |

## Rejestr serii i test spójności (2026-08-19, wersja 1.11.0)

Rozpoznawanie oznaczeń żyje w CZTERECH plikach (`bearing_types.py`, `lookup.py`,
`BearingTypeClassifier.kt`, `Repository.kt`). Trzy razy zdarzyło się, że seria trafiła
do jednego, a nie do drugiego - i program po cichu podstawiał wymiary innego łożyska.

- [x] **`serie_lozysk.py`** - rejestr serii: przedrostki, typ, sposób czytania otworu
      (kod ISO / wprost w mm / brak reguły) i **ŹRÓDŁO** dla każdej pozycji.
      Wpis bez źródła nie przechodzi testu - nie trzymamy tu wiedzy "z pamięci"
- [x] Lista przedrostków w `lookup.py` nie jest już pisana ręcznie, tylko brana z rejestru
- [x] **`tests/test_spojnosc_regul.py`** - pilnuje, że wszystkie cztery miejsca mówią
      to samo; plik Kotlina czytany jako tekst

### Co ten test znalazł od razu

Jedenaście serii z tą samą pułapką co ES/EX - gubiły przedrostek przy normalizacji:
**N, NP, NUB, NJP, NKX, NKS, NKIB, TA, AXK, AX, RA**. Najpoważniejsze jest `N208`:
zwykłe łożysko walcowe, które redukowało się do „208", czyli do kulkowego 40×80×18.

Oraz regresję, którą sam wprowadziłem przy tej poprawce: po dodaniu przedrostka „N"
normalizacja czytała **„NTN 6205" jako „N6205"** - końcowe N w nazwie marki wyglądało
jak seria. Ratuje granica słowa; osobny test tego pilnuje.

## Walidacja całej bazy (2026-08-19, wersja 1.12.0)

Sprawdzone wszystkie 27 pozycji: wymiary kontra oznaczenie, oznaczenie kontra typ,
zgodność z katalogiem.

### Znaleziony błąd W REGUŁACH (nie w danych)

- [x] **Seria 52xx była klasyfikowana jako OPOROWA, a jest SKOŚNA DWURZĘDOWA.**
      Łożysko 5202 użytkownika (15 × 35 × 15,9 mm, 11 szt.) dostało przez to złą
      kategorię. 52xx i 53xx to starsze oznaczenie serii 32xx/33xx - to samo łożysko
      (5202 = 3202). Oporowe kulkowe mają oznaczenia PIĘCIOCYFROWE: 51100, 51200, 52200.
      Pomyłka nie jest kosmetyczna: oporowe przenosi obciążenie osiowe, skośne
      promieniowo i osiowo. Poprawione po obu stronach + test + wpis w katalogu

### Wymiary zgodne z oznaczeniem (sprawdzone regułą kodu otworu i normą)

20211 (55×100×21), 21307 (35×80×21), 21310 (50×110×27), 2209 (45×85×23),
32010 (50×80×20), NJ211 (55×100×21), 62205 (25×52×18), 6922zz (110×150×20),
oraz wszystkie 6xxx zgodne z katalogiem co do dziesiątej milimetra.

### Do rozstrzygnięcia przy regale (oznaczone ptaszkiem)

- [ ] **62205 - otwór 52 mm przy średnicy zewnętrznej 52 mm.** Z oznaczenia wynika
      25 mm. Drugi wpis tego samego symbolu ma poprawne 25 × 52 × 18 - wygląda na
      literówkę przy wpisywaniu. Do zmierzenia i scalenia z tamtym wpisem
- [ ] **uc209 - szerokość 19 mm** (pierścień zewnętrzny) kontra 49,2 mm w katalogu
      i w Twoim nowszym wpisie UC208 (pierścień wewnętrzny). Jedna konwencja do wyboru
- [ ] **"205"** - to stare oznaczenie PN/GOST odpowiadające 6205; wymiary 25×52×15 się
      zgadzają. Rozważyć zapis jako 6205, żeby reguły je rozpoznawały
