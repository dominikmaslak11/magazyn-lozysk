# Lista zakupów: 6 nowych półek w Regale 2

Data: 2026-08-19 · sklep: Leroy Merlin

## Co i po co

Dolna półka Regału 2 ma **142 cm prześwitu** — to dziś zmarnowana przestrzeń.
Podział na 7 poziomów (czyli **6 nowych półek**) daje ok. **219 dm² powierzchni**,
więcej niż całe dzisiejsze Regały 1 + 2 razem wzięte (294 → 513 dm²).

Regał jest **drewniany, zrobiony ze starej szafy, ścianka ok. 2 cm** — to determinuje
długość wkrętów (patrz niżej).

## Wymiary półek

| | |
|---|---|
| wymiar płyty | **860 × 500 mm** (6 sztuk) |
| prześwit po zamontowaniu | ok. **18,4 cm** na poziom |
| najwyższy stos, jaki wejdzie | 13,4 cm (2 szt. uc209 albo 5 szt. 6020) |

Prześwit wychodzi z rachunku: 142 cm minus 6 × grubość płyty, podzielone na 7 poziomów.

---

## 1. Płyta — dwa warianty

**Wybór zależy od wilgotności warsztatu, nie od ceny.**

| wariant | arkuszy | koszt (szac.) | uwaga |
|---|---|---|---|
| płyta wiórowa surowa 18 mm, 280 × 207 cm | **1** (wychodzi 12 półek) | ~230 zł | **tylko do suchego, ogrzewanego pomieszczenia** |
| **OSB-3 18 mm, 250 × 125 cm** | **2** (po 5 półek) | ~330 zł | odporna na wilgoć — **wybór domyślny dla warsztatu** |
| OSB-3 22 mm, 250 × 125 cm | 2 | ~400 zł ([cena potwierdzona: 199 zł/arkusz](https://www.leroymerlin.pl/konstrukcje-drewniane-i-metalowe/deski-plyty-wykonczeniowe-listwy/plyty-osb/plyta-osb-3-22mm-2500x1250-3-125m2,p178697,l1899.html)) | niepotrzebna, jeśli będą listwy |

Surowa płyta wiórowa w wilgoci puchnie i rozwarstwia się — tego się nie odwraca.
Przy warsztacie nieogrzewanym bierz OSB-3.

**Poproś o docięcie na miejscu.** Arkusz 280 × 207 cm nie wejdzie do auta.
Kartka dla obsługi: **6 sztuk 860 × 500 mm**.

## 2. Listwy — to jest ważniejsze niż grubość płyty

Rozpiętość 86 cm bez podparcia jest duża. Ugięcie przy 60 kg (tyle waży pełna półka
ciężkich łożysk), z uwzględnieniem pełzania — płyta pod stałym obciążeniem dogina się
latami:

| rozwiązanie | od razu | po latach |
|---|---|---|
| sama płyta 18 mm | 5,7 mm | 11,5 mm ❌ |
| sama płyta 22 mm | 3,1 mm | 6,3 mm |
| **18 mm + dwie listwy 20 × 40 pod krawędziami** | **0,9 mm** | **1,7 mm** ✅ |

Listwy za kilkadziesiąt złotych dają sztywność, której nie kupisz żadną rozsądną
grubością płyty. Listwa idzie **na sztorc** (bokiem 40 mm w pionie) pod przednią
i tylną krawędzią, wzdłuż 86 cm.

**Do kupienia:**

| pozycja | ilość | zastosowanie |
|---|---|---|
| listwa sosnowa 20 × 40 mm | **11 m** (np. 4 × 3 m) | usztywnienie: 2 × 86 cm na półkę |
| listwa sosnowa 20 × 40 mm | **6 m** (np. 2 × 3 m) | podpory boczne: 2 × 50 cm na półkę |

Razem ok. **17 m**, czyli **6 listew po 3 m** z małym zapasem.

## 3. Wkręty — długość wynika ze ścianki 2 cm

⚠️ **Ścianka regału ma 20 mm — wkręt 40 mm przebije ją na wylot.**

| wkręt | ilość | do czego |
|---|---|---|
| **4 × 35 mm** do drewna | 100 szt. | podpory boczne do ścianek regału (20 mm listwa + 15 mm w ściankę) |
| **3,5 × 30 mm** do drewna | 100 szt. | płyta do listew usztywniających (18 mm płyta + 12 mm w listwę) |

Po dwa opakowania setek starczy z zapasem (potrzeba ok. 50 + 25).

**Jeśli szafa jest z płyty wiórowej, a nie z litego drewna** (a stare szafy zwykle są):
- **nawiercaj otwory** wiertłem 2,5 mm — wiórowa pęka i pęcznieje przy wkręcaniu na siłę
- wkręcaj w **płaszczyznę** ścianki, nigdy w krawędź — w krawędzi wiórowa trzyma słabo

---

## Podsumowanie kosztów (szacunek)

| | |
|---|---|
| OSB-3 18 mm × 2 arkusze | ~330 zł |
| listwy 20 × 40, 6 × 3 m | ~60 zł |
| wkręty, 2 opakowania | ~40 zł |
| **razem** | **~430 zł** |

Wariant z płytą wiórową (suchy warsztat): **~330 zł**.

---

## Do sprawdzenia przed zakupem

- [ ] Zmierzyć **wewnętrzną** szerokość regału w kilku miejscach — stara szafa może być
      nierówna, a 860 mm to wymiar dopasowany na styk. Jak wyjdzie mniej, docinamy mniej
- [ ] Ustalić, czy warsztat jest ogrzewany (decyduje o wyborze płyty)
- [ ] Sprawdzić, czy ścianki są z litego drewna czy z płyty wiórowej (decyduje o nawiercaniu)

## Skąd te liczby

Wymiary regału pochodzą z bazy magazynu (tabela `shelves`, kolumny `szerokosc_mm`,
`glebokosc_mm`, `wysokosc_mm`). Obciążenie 60 kg to oszacowanie pełnej półki ciężkich
łożysk, policzone z geometrii pozycji w bazie. Ugięcie liczone jak dla belki swobodnie
podpartej z obciążeniem równomiernym, moduł sprężystości OSB przyjęty ostrożnie
(3500 MPa), pełzanie jako podwojenie ugięcia w czasie.

Ceny poza OSB-3 22 mm są **szacunkowe** — sprawdź na miejscu.
