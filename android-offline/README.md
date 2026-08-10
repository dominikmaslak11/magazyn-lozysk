# Łożyska Offline (Android)

Appka Kotlin/Jetpack Compose z własną bazą (Room/SQLite) na telefonie.
Działa w pełni offline, a gdy jest połączenie z serwerem (`../server.py`),
synchronizuje się z nim automatycznie.

## Budowanie

```bash
cd android-offline
./gradlew assembleDebug
```

Plik APK: `app/build/outputs/apk/debug/app-debug.apk`. Zainstaluj przez
`adb install -r <plik>` albo skopiuj na telefon i zainstaluj ręcznie
(Ustawienia → Bezpieczeństwo → zezwól na instalację z nieznanych źródeł).

## Konfiguracja synchronizacji

1. Uruchom serwer (`python ../server.py`) na komputerze. Przy starcie wypisze
   w konsoli **token dostępu** - będzie potrzebny w kroku 2.
2. W appce, w zakładce **Dane**, wpisz:
   - **adres serwera** (np. `192.168.1.23:8420` w tej samej sieci Wi-Fi, albo
     adres Tailscale w formie `100.x.x.x:8420` dla dostępu spoza domu - patrz
     `../README.md`),
   - **token dostępu** (ten z konsoli serwera; leży też w
     `~/.lozyska_data/token.txt`),

   i kliknij „Zapisz i synchronizuj teraz”. Jeśli token jest zły, appka
   napisze wprost „Serwer odrzucił połączenie - sprawdź token dostępu”
   zamiast pokazywać surowy błąd HTTP.
3. Od tej pory appka synchronizuje się automatycznie: przy każdym otwarciu
   oraz co ok. godzinę w tle (gdy jest połączenie z siecią), plus zawsze
   ręcznie przez ten sam przycisk.

Powtórz konfigurację (krok 2) na każdym telefonie - wszystkie synchronizują
się z tym samym serwerem, więc będą mieć te same dane.

## Jak działa synchronizacja

Serwer jest jedynym źródłem prawdy ("hub") - telefony nigdy nie
synchronizują się bezpośrednio między sobą, tylko przez serwer:

1. Telefon wysyła (push) rekordy, które **sam** zmienił lokalnie od swojej
   ostatniej udanej synchronizacji.
2. Serwer zapisuje te zmiany i odsyła pełny, aktualny stan.
3. Telefon podmienia swoją lokalną kopię na to, co dostał z serwera.

Rekordy mają identyfikatory UUID (nie liczby), więc kilka telefonów może
tworzyć nowe łożyska offline jednocześnie bez ryzyka kolizji. Kasowanie jest
"miękkie" (nagrobek), żeby poprawnie propagowało się na inne urządzenia.

**Konflikty** (dwa telefony offline edytują *tę samą* pozycję w tym samym
czasie) rozstrzyga reguła "kto ostatni zsynchronizuje się z serwerem,
wygrywa" - bez UI do ręcznego scalania. To świadomy kompromis: prostota
kosztem rzadkiego ryzyka cichego nadpisania przy jednoczesnej edycji offline
dokładnie tej samej pozycji przez dwie osoby. Dla magazynu łożysk (dane
głównie addytywne) to uzasadniony wybór.

Appka działa też w pełni bez serwera - lokalna baza jest zawsze dostępna,
synchronizacja jest tylko wzbogaceniem/backupem na wypadek awarii komputera.

## Skanowanie kodów QR / kreskowych

W zakładce **Łożyska** obok przycisku „+” jest przycisk z ikoną skanera.
Po zeskanowaniu kodu QR albo kreskowego (z etykiety, opakowania, pudełka)
appka od razu otwiera okno dodawania łożyska z **wpisanym symbolem** i
automatycznie dociąga do niego wymiary — dokładnie tą samą ścieżką, co
ręczne kliknięcie „Pobierz wymiary” (najpierw wbudowany katalog offline,
potem ewentualnie internet). Wystarczy uzupełnić ilość sztuk i zapisać.

Rozpoznawanie kodów działa **w pełni offline** (ML Kit on-device) — obraz z
aparatu nigdy nie opuszcza telefonu i nie jest nigdzie wysyłany. Kosztem
tego wyboru jest rozmiar APK (model rozpoznawania jest wbudowany w appkę,
~40 MB zamiast ~5 MB) — świadomy kompromis, spójny z offline-first
charakterem appki.

Uprawnienie do aparatu jest proszone dopiero przy pierwszym użyciu skanera i
jest w pełni opcjonalne — bez niego appka działa normalnie, symbol po prostu
wpisujesz ręcznie.

### Kody kreskowe z opakowań (EAN) — appka uczy się sama

Kod EAN-13 na pudełku łożyska to **numer handlowy producenta, a nie oznaczenie
łożyska** — nie da się z niego odczytać ani symbolu, ani wymiarów. Dlatego appka
rozróżnia dwa przypadki:

- **Nasza naklejka QR** (albo kod producenta zawierający oznaczenie) → symbol
  jest wprost w kodzie, więc appka od razu otwiera łożysko z wymiarami.
- **Kod handlowy EAN/UPC** → appka sprawdza zapamiętane skojarzenia. Jeśli kodu
  jeszcze nie zna, **pyta raz**: „co to za łożysko?”. Odpowiedź zostaje
  zapisana i zsynchronizowana przez serwer, więc każdy kolejny skan tego samego
  pudełka — także na innym telefonie — rozpoznaje je natychmiast, bez pytania.

Świadomie **nie** korzystamy z zewnętrznych baz GTIN: dla łożysk są płatne i
niekompletne, a takie samouczące się skojarzenia pokrywają dokładnie ten
asortyment, który faktycznie masz w magazynie.

Zapamiętane skojarzenia zobaczysz (i skasujesz, jeśli któreś jest błędne) w
wersji webowej, w zakładce **Dane → „Zapamiętane kody z opakowań”**. Po
usunięciu skojarzenia appka zapyta o ten kod ponownie przy następnym skanie.

## Wersjonowanie / wymuszanie aktualizacji

Każda synchronizacja z serwerem przenosi też informację o wersji (patrz
`VERSION` i `MIN_CLIENT_VERSION` w `../server.py`):

- Jeśli appka jest **starsza niż `min_client_version`** zgłoszone przez
  serwer, synchronizacja zatrzymuje się *przed* nadpisaniem lokalnej bazy
  (lokalne zmiany zdążyły już wcześniej wysłać się na serwer, więc nic nie
  ginie) i na górze ekranu pojawia się czerwony baner z przyciskiem
  „Aktualizuj”, prowadzącym do strony wydań na GitHubie. Appka offline
  działa dalej normalnie - blokowana jest tylko synchronizacja.
- Jeśli appka jest starsza niż bieżąca `server_version`, ale wciąż
  kompatybilna, pokazuje się tylko łagodna, informacyjna belka (bez
  blokowania niczego).

Dla kogoś, kto uruchamia własny serwer: `MIN_CLIENT_VERSION` w `server.py`
podnoś ręcznie **tylko** wtedy, gdy zmieniasz format/API synchronizacji w
sposób łamiący starsze appki - w przeciwnym razie zostaw ją bez zmian, żeby
nie zmuszać ludzi do aktualizacji bez potrzeby.

## Dostęp spoza domowej sieci

Rekomendowane rozwiązanie: [Tailscale](https://tailscale.com/) - prywatna
sieć VPN między serwerem a telefonami, bez przekierowywania portów na
routerze i bez certyfikatów TLS. Zainstaluj appkę Tailscale na komputerze z
serwerem i na każdym telefonie, zaloguj się tym samym kontem - serwer
dostanie stały adres (100.x.x.x), osiągalny z telefonu z dowolnego miejsca
z internetem. Wpisz ten adres w appce zamiast lokalnego IP.
