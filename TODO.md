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
