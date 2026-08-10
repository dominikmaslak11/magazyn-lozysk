# TODO / Roadmapa

Lista pomysłów zebrana 2026-08-10. Nieoznaczone = do zrobienia, `[x]` = zrobione, `[~]` = częściowo/wymaga decyzji.

## Otwarte źródło / Google Play

- [ ] Dodać plik `LICENSE` (do ustalenia która licencja — patrz pytanie do użytkownika)
- [x] Repo publiczne na GitHubie (`dominikmaslak11/magazyn-lozysk`)
- [ ] Rozbudować `README.md` (root) o pełną instrukcję instalacji/uruchomienia dla kogoś z zewnątrz (nie tylko dla siebie), z opisem architektury (serwer Flask + PWA, klient Android offline+sync, legacy desktop)
- [ ] Karta sklepu Google Play (opis, grafiki, polityka prywatności) — dopiero gdy appka będzie gotowa do publikacji
- [ ] Konto dewelopera Google Play (użytkownik zakłada sam — wymaga płatności/danych osobowych)
- [ ] Podpisany build AAB appki `android-offline` do uploadu
- [ ] Uwaga: appka zależna od własnego serwera domowego (Wi-Fi/Tailscale) — do przemyślenia, jak to wygląda dla kogoś, kto ściągnie appkę z Play bez posiadania takiego serwera (tryb czysto offline musi działać sensownie sam z siebie)

## Funkcje aplikacji

- [ ] **Skanowanie kodów kreskowych/QR** (CameraX + ML Kit) do szybkiego wyszukania łożyska po symbolu
  - [ ] Dodać generowanie QR/kodu kreskowego do etykiet PDF (`pdf_labels.py`), żeby było co skanować
  - [ ] Ekran skanera w `android-offline` (i ew. `android-klient`)
- [ ] **Mechanizm weryfikacji wersji / wymuszania aktualizacji**
  - [ ] Endpoint na serwerze zwracający minimalną/aktualną wymaganą wersję API
  - [ ] Appka Android porównuje przy starcie i blokuje/ostrzega, jeśli wersja za stara
  - [ ] Do ustalenia: czy to ma sens jako "twardy blokader" czy tylko ostrzeżenie (patrz uwaga o Play Store w rozmowie)
- [ ] **Konfigurowalna liczba regałów** (usunąć sztywne 9)
  - [ ] Endpoint `POST /api/shelves` (dodaj regał) i `DELETE /api/shelves/<id>` (usuń regał, z obsługą łożysk które na nim leżały)
  - [ ] UI webowe: przyciski "Dodaj regał" / "Usuń regał" w zakładce Regały
  - [ ] Sync do appek Android (model `Shelf` już jest generyczny, powinno zadziałać bez zmian w Room, do zweryfikowania)
  - [ ] **Do ustalenia z użytkownikiem**: czy chodzi tylko o dowolną liczbę regałów (płasko, jak teraz), czy o pełną hierarchię regał → szuflada → skrytka (wymaga zmiany modelu danych, patrz rozmowa)

## Uwagi / ryzyka do pilnowania

- Appka nie ma obecnie żadnej autoryzacji na endpointach API serwera — jeśli appka trafia do publicznego Play Store i ma się łączyć z serwerami różnych ludzi przez internet (nie tylko lokalne Wi-Fi), warto rozważyć czy potrzebne jest jakiekolwiek zabezpieczenie dostępu do serwera.
