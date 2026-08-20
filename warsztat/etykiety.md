# Etykiety na lokalizacje — co wpisać w drukarkę

Taśma 12 mm, tekst wpisywany ręcznie. **29 etykiet** (po przebudowie Regału 2).

---

## Zasada nazewnictwa

```
R2-P3-A
│  │  └─ komora: A = lewa, B = prawa (patrząc na regał)
│  └──── półka, licząc OD DOŁU
└─────── regał
```

**Dlaczego tak, a nie „Regał 2, półka 3, lewa":** na taśmie 12 mm długi tekst schodzi
do rozmiaru, którego nie odczytasz z dwóch metrów. `R2-P3-A` to siedem znaków — zmieści
się dużą czcionką i przeczytasz je stojąc przed regałem.

**Dlaczego A/B, a nie L/P:** „P" znaczyłoby raz półkę, raz prawą. Litery A/B nie kolidują
z niczym i zostawiają miejsce na C, gdyby kiedyś doszła trzecia komora.

**Numeracja półek od dołu**, bo dokładanie półki na górze nie przenumeruje wtedy
wszystkiego poniżej. Etykieta ma przetrwać przebudowę.

---

## Lista do wpisania

### Regał 1 — 7 półek (bez przegród)

```
R1-P1
R1-P2
R1-P3
R1-P4
R1-P5
R1-P6
R1-P7
```

### Regał 2 — 9 poziomów, wszystkie z przegrodami

Dolna przestrzeń (142 cm) dzielona na 7 poziomów po 18,7 cm:

```
R2-P1-A     R2-P1-B
R2-P2-A     R2-P2-B
R2-P3-A     R2-P3-B
R2-P4-A     R2-P4-B
R2-P5-A     R2-P5-B
R2-P6-A     R2-P6-B
R2-P7-A     R2-P7-B
```

Górna przestrzeń (46 cm) dzielona na 2 poziomy po 22,1 cm:

```
R2-P8-A     R2-P8-B
R2-P9-A     R2-P9-B
```

Numeracja biegnie **od dołu przez cały regał**, bez resetowania na granicy dawnych
przestrzeni — z punktu widzenia szukania łożyska to jeden regał, a nie dwa.

### Regał 3 — bufor tymczasowy

```
R3-P1
R3-P2
R3-P3
R3-P4
```

Warto dokleić drugą etykietę **`BUFOR`** na samym regale, żeby było widać z daleka,
że to miejsce odkładcze, a nie docelowe.

---

## Gdzie naklejać

Na **przednią krawędź półki, przy lewym końcu** — wtedy widać wszystkie etykiety
w jednej pionowej linii i czyta się je jak spis treści. Przy komorach A/B: etykieta
komory A po lewej stronie przegrody, komory B po prawej.

Krawędź OSB jest chropowata — **przetrzyj ją papierem ściernym i odtłuść** przed
naklejeniem, inaczej taśma odpadnie po kilku miesiącach. Na laminowanej desce z biurka
trzyma się bez przygotowania.

---

## Czego NIE pisać na etykietach lokalizacji

**Symboli łożysk.** Kusi, żeby napisać „6205" na półce, ale zawartość się zmienia,
a etykieta zostaje — i po pół roku wprowadza w błąd. Od tego, co gdzie leży, jest
aplikacja; etykieta ma mówić tylko, **gdzie jesteś**.

Jeśli chcesz opisać same łożyska, rób to na pudełkach albo pojemnikach, nie na regale.

---

## Osobno: etykiety na pojemniki (opcjonalnie)

Jeśli małe łożyska trafią do skrzynek, na każdą warto nakleić sam symbol:

```
6203
6005
UC209
```

Te mogą się zmieniać razem z zawartością — pudełko wędruje, półka nie.

---

## Co dalej po naklejeniu

Powiedz, kiedy skończysz, to wprowadzę te 26 lokalizacji do bazy razem z wymiarami
każdej komory (**428 × 495 × 187 mm** dla A/B w Regale 2). Wtedy aplikacja będzie
pokazywać przy każdym łożysku dokładnie ten kod, który masz na taśmie — i rachunek
pojemności policzy zapełnienie każdej komory osobno.
