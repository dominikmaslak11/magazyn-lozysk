# Półki do dwóch szaf na ubrania

Data: 2026-08-21 · policzone przez [`stolarz.py`](../stolarz.py)

## Przestrzeń

**1200 × 760 × 470 mm** w każdej z dwóch szaf, ścianka **16 mm**.

## Ile półek

| półek | poziomów | prześwit | do czego |
|---|---|---|---|
| 2 | 3 | 388 mm | za wysoko — stosy ubrań się przewracają |
| **3** | **4** | **286 mm** | **swetry, bluzy, pościel — wybór domyślny** |
| 4 | 5 | 226 mm | koszulki i bielizna, na swetry za nisko |

**Trzy półki na szafę, czyli sześć razem.** 28,6 cm to wysokość, przy której złożony
sweter stoi stabilnie, a jeszcze sięgasz ręką do tyłu półki.

## Grubość — 18 mm, nie 16

Rozpiętość 76 cm. Ugięcie po latach (z pełzaniem), granica L/200 = 3,8 mm:

| obciążenie | 16 mm | 18 mm |
|---|---|---|
| 10 kg (koszulki) | 2,6 mm | 1,8 mm |
| 15 kg (swetry) | 3,8 mm | 2,7 mm |
| **20 kg** | **5,1 mm ❌** | **3,6 mm ✅** |
| 25 kg (pościel) | 6,4 mm ❌ | 4,5 mm ❌ |
| 30 kg (koce) | 7,7 mm ❌ | 5,4 mm ❌ |

**16 mm wystarcza tylko do ~15 kg**, mimo że ścianki szafy mają właśnie tyle.
Przy 18 mm masz zapas do ~20 kg.

⚠️ **Pościeli i koców nie kładź na te półki** — 25–30 kg wygnie każdą płytę na tej
rozpiętości. Jeśli mają tam trafić, potrzebna jest podpora pośrodku (wtedy ugięcie
spada do 0,3 mm), ale w szafie na ubrania przegroda przeszkadza przy układaniu.

## Formatka

**755 × 450 mm**, 6 sztuk.

- **755** = 760 minus 5 mm luzu, żeby półka weszła między ścianki
- **450** zamiast 470 — dwa centymetry zapasu z przodu na zawiasy i domykanie drzwi.
  Głębokość i tak podałeś jako negocjowalną, a płytsza formatka nic nie kosztuje.

## Zakup — dwa warianty

| | cały arkusz | **docinanie na wymiar** |
|---|---|---|
| co kupujesz | 280 × 207 cm (5,80 m²) | 6 formatek 755 × 450 |
| cena płyty | **220 zł** | **~78 zł** (2,04 m² × 37,99 zł/m²) |
| odpad | **3,76 m² (65%)** | 0 — zostaje w sklepie |
| co zostaje | 6 zapasowych formatek | nic |

[Płyta meblowa laminowana biała U511 18 mm, Swiss Krono — 37,99 zł/m²](https://www.leroymerlin.pl/produkty/plyta-meblowa-laminowana-biala-u511-18-mm-280x207-cm-swiss-krono-41349882.html)

**Bierz docinanie na wymiar.** Arkusz 280 × 207 cm to 5,8 m² na 2 m² potrzeby —
zapłaciłbyś 142 zł za sześć zapasowych półek, których nie masz gdzie użyć, a przy
okazji musiałbyś przewieźć płytę 2,8 metra i pociąć ją samemu. Usługa nazywa się
**„płyta meblowa na wymiar"**.

## Obrzeże — przy białej płycie to nie kosmetyka

Cięta krawędź płyty laminowanej to goła wiórowa: szara, chropowata i widoczna
w otwartej szafie. Laminat pokrywa tylko płaszczyzny.

- **przednia krawędź**: 4,5 m łącznie (6 × 755 mm) — **to trzeba okleić**
- boki i tył: kolejne 5,4 m — boki chowają się przy ściance, tył nie widać

Kup **obrzeże melaminowe białe z klejem termotopliwym**, ok. 5 m na rolce; wystarczy
jedna rolka na przód, dwie jeśli chcesz też boki. Przykleja się żelazkiem, nadmiar
ścina się nożem. Leroy dokleja obrzeże także jako usługę przy docinaniu — jeśli cena
jest rozsądna, to najczystsze wyjście.

## Podparcie półek

Sześć par listew nośnych **20 × 20 mm**, po 450 mm — razem **5,4 m**, czyli
2 listwy po 3 m.

Alternatywa bez listew: **podpórki do półek w kołek 5 mm** — nawiercasz cztery otwory
na półkę i wkładasz metalowe wsporniki. Wygląda czyściej w szafie na ubrania i pozwala
przestawić półkę później. Przy 6 półkach to 24 podpórki, ok. 15 zł.

⚠️ Ścianka szafy ma **16 mm** — nawiercając otwory pod kołki użyj **ogranicznika
głębokości ustawionego na 10 mm**. Bez niego wiertło wychodzi na drugą stronę.

## Lista zakupów

| pozycja | ilość | koszt |
|---|---|---|
| płyta laminowana biała 18 mm, docięta 755 × 450 | 6 formatek (2,04 m²) | ~78 zł |
| obrzeże melaminowe białe 18–19 mm, rolka 5 m | 1–2 | ~30 zł |
| podpórki do półek 5 mm (albo listwy 20 × 20) | 24 szt. | ~15 zł |
| | **razem** | **~125 zł** |

Plus opłata za docięcie — zapytaj przez telefon, bo zależy od sklepu.

## Skąd te liczby

Wszystko policzone przez `stolarz.py` z pomiarów przestrzeni. Ugięcie liczone jak dla
belki swobodnie podpartej z obciążeniem równomiernym, moduł sprężystości płyty
wiórowej przyjęty ostrożnie (2800 MPa), pełzanie jako podwojenie ugięcia w czasie.

Model 3D: `warsztat/szafa.FCStd` i `szafa.step`.
Cena płyty **potwierdzona** (37,99 zł/m²), ceny obrzeża i podpórek **szacunkowe**.
