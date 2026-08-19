# Wdrożenie produkcyjne

> Stan na 2026-08-19, po zakończeniu migracji.
>
> Uwaga: to repozytorium jest **publiczne**, więc nie ma tu adresów, nazw
> hostów ani niczego, co opisuje prywatną sieć. Szczegóły dostępu trzymane
> są poza repozytorium.

## Gdzie to chodzi

Aplikacja pracuje na **osobnej maszynie domowej**, która działa bez przerwy —
dzięki temu laptop można zamknąć, przenieść i zrestartować bez ubijania serwera.

Instancja na laptopie została **zatrzymana i wyłączona z autostartu**
(`systemctl --user disable magazyn-lozysk`). To nie jest kosmetyka: dopóki
chodziła, telefony synchronizowały się z nią, a nie z serwerem, i obie bazy
rozjeżdżały się w ciszy. Dwie żywe instancje tej samej aplikacji to najprostszy
sposób na zgubienie danych.

Maszyna jest dostępna wyłącznie przez prywatną sieć nakładkową
([Tailscale](https://tailscale.com)). Nie ma przekierowania portów na routerze
i nie jest wystawiona do internetu.

## Jak jest zbudowane

| | |
|---|---|
| System | Debian 13 (trixie), bez środowiska graficznego |
| Katalog aplikacji | `/opt/magazyn-lozysk` (klon repozytorium) |
| Katalog danych | `/var/lib/lozyska` (baza, kopie, `ai_keys.json`, `token.txt`) |
| Konto systemowe | `lozyska` — osobne, bez powłoki logowania |
| Zależności | własne `venv` w katalogu aplikacji |
| Port | `8420` |
| Usługa | `systemd`, jednostka `lozyska.service`, `Restart=always` |

Aplikacja **nie chodzi jako root**. Gdyby ktoś znalazł w niej dziurę,
ograniczone konto jest różnicą między kłopotem a katastrofą.

Usługa nie uruchamia `server.py` bezpośrednio — startuje przez
`/usr/local/bin/lozyska-start`, który czeka na adres sieci nakładkowej,
ustawia `LOZYSKA_DATA_DIR` i `LOZYSKA_PORT`, a dopiero potem oddaje sterowanie
Pythonowi. Powód praktyczny: wielolinijkowy `bash -c` wewnątrz pliku jednostki
psuje się na cytowaniu w sposób trudny do zauważenia, a osobny skrypt da się
uruchomić ręcznie i zobaczyć, co mówi.

## Podział ról: gdzie kod, gdzie dane

To jest sedno układu i warto go trzymać:

| | gdzie żyje | kto zmienia |
|---|---|---|
| **Kod** | laptop → git → GitHub → `git pull` na serwerze | rozwijany na laptopie |
| **Dane produkcyjne** | **wyłącznie serwer**, `/var/lib/lozyska` | telefony i przeglądarka przez API |
| **Dane testowe** | laptop, `~/.lozyska_data` | dowolnie, to piaskownica |

**Baza na laptopie nie jest już produkcyjna.** Została tam jako kopia z momentu
migracji i służy do prób: uruchamiania testów, `audyt.py`, eksperymentów ze
schematem. Można ją skasować i odtworzyć z serwera w każdej chwili.

Zmiany w **prawdziwych** danych (poprawki wymiarów, korekty stanów) robi się
przeciwko serwerowi — przez przeglądarkę, telefon albo skrypt uruchomiony
przez SSH na serwerze. Nigdy przez edycję lokalnej bazy z nadzieją, że
„się zsynchronizuje": ona się nie zsynchronizuje, bo to serwer jest źródłem prawdy.

## Codzienna praca

```bash
# --- rozwój, na laptopie ---
# testy chodzą na lokalnej bazie testowej, nie dotykają produkcji
python tests/test_bearing_types.py
python -m pytest tests/          # jeśli wolisz

git add -A && git commit && git push

# --- wdrożenie, na serwerze ---
ssh <serwer>
sudo -u lozyska git -C /opt/magazyn-lozysk pull --ff-only
sudo -u lozyska /opt/magazyn-lozysk/venv/bin/pip install -q -r /opt/magazyn-lozysk/requirements.txt
sudo systemctl restart lozyska

# --- co się dzieje ---
systemctl status lozyska
journalctl -u lozyska -f
```

Skrypty narzędziowe (`audyt.py`, `wysylka.py`) uruchamiane **na serwerze**
działają na prawdziwych danych:

```bash
ssh <serwer> "sudo -u lozyska /opt/magazyn-lozysk/venv/bin/python \
    /opt/magazyn-lozysk/audyt.py --oznaczone"
```

## Dane

Baza została przeniesiona z laptopa i **zweryfikowana przez porównanie liczby
rekordów oraz odcisku zawartości** (SHA-256 z posortowanych symboli, wymiarów,
ilości i lokalizacji) po obu stronach — nie przez sprawdzenie, że aplikacja
„się otwiera". Odciski były identyczne.

Kopie zapasowe robią się automatycznie przy starcie serwera i przed każdym
importem, do `/var/lib/lozyska/backups/`.

⚠ **Kopie leżą na tym samym dysku co baza.** Maszyna ma swoje lata i jej dysk
też. Warto wypychać kopie na inny nośnik albo na inną maszynę w sieci —
dysk psuje się razem z jednym i drugim.

## Token dostępu

Aplikacja ma własną autoryzację tokenem, zapisanym w `/var/lib/lozyska/token.txt`.

Przy migracji okazało się, że serwer miał **inny token niż telefony** — mimo że
dane przeniosły się poprawnie, urządzenia dostawały `401`. Token został
ujednolicony do tego, który znają telefony; poprzedni leży obok jako
`token.txt.przed-ujednoliceniem`.

Wniosek na przyszłość: przy przenoszeniu danych **token trzeba przenieść osobno
i sprawdzić osobno**. Nie wynika z bazy i nikt tego nie zauważy, dopóki
któreś urządzenie nie spróbuje się połączyć.

Zmiana tokenu: skasuj plik i zrestartuj usługę. Wtedy trzeba wpisać nowy
na wszystkich urządzeniach.

## Czego świadomie nie zrobiono

Aplikacja **nie jest wystawiona do internetu**, mimo że ma własny token. Token
byłby wtedy jedyną warstwą ochrony realnego stanu magazynowego. Sieć nakładkowa
jest drugą warstwą i kosztuje zero wysiłku.

## Lista kontrolna po migracji

- [x] baza przeniesiona i zweryfikowana odciskiem zawartości
- [x] token ujednolicony, API odpowiada urządzeniom `200`
- [x] instancja na laptopie zatrzymana i wyłączona z autostartu
- [x] jeden telefon przepięty na serwer i zsynchronizowany
- [ ] **drugi telefon przepięty** (wymaga podłączenia albo ręcznej zmiany adresu)
- [ ] kopie zapasowe wypychane poza maszynę serwera
