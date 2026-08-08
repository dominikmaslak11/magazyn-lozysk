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

1. Uruchom serwer (`python ../server.py`) na komputerze.
2. W appce, w zakładce **Dane**, wpisz adres serwera (np. `192.168.1.23:8420`
   w tej samej sieci Wi-Fi, albo adres Tailscale w formie `100.x.x.x:8420` dla
   dostępu spoza domu - patrz `../README.md`) i kliknij „Zapisz i
   synchronizuj teraz”.
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

## Dostęp spoza domowej sieci

Rekomendowane rozwiązanie: [Tailscale](https://tailscale.com/) - prywatna
sieć VPN między serwerem a telefonami, bez przekierowywania portów na
routerze i bez certyfikatów TLS. Zainstaluj appkę Tailscale na komputerze z
serwerem i na każdym telefonie, zaloguj się tym samym kontem - serwer
dostanie stały adres (100.x.x.x), osiągalny z telefonu z dowolnego miejsca
z internetem. Wpisz ten adres w appce zamiast lokalnego IP.
