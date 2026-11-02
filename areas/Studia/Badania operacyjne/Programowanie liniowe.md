---
type: notatka
tags: [studia, badania-operacyjne, programowanie-liniowe]
project: ["[[Badania operacyjne]]"]
people: []
created: 2026-10-07
---
# Badania operacyjne: programowanie liniowe

Notatka z wykładu z [[2026-10-07]]. Hub przedmiotu: [[Badania operacyjne]]. Źródło: wykład PL, Katedra Badań Operacyjnych (Wachowicz).

## Plan wykładu
1. Wprowadzenie
2. Modelowanie problemów decyzyjnych
3. Metoda graficzna
4. Postać bazowa
5. Simpleks
6. Szczególne przypadki simpleksu
7. Metoda dualna

## Podstawy
- Badania operacyjne = teoria decyzji -> **optymalizacja**: wyznaczanie najlepszego rozwiązania problemu decyzyjnego wg danego kryterium.
- Schemat: **Problem -> Model -> Algorytm -> Rozwiązanie**.
- Nazwa: II wś, grupa Blacketta ("Cyrk Blacketta"): lokalizacja radarów, walka z u-bootami, ocena nalotów dywanowych. "Operations rooms" -> badania operacyjne.

## Budowa modelu (4 kroki)
1. **Zmienne decyzyjne**: co decydujemy (np. ilość par produktu).
2. **Funkcja celu**: co max/min.
3. **Warunki ograniczające**: zasoby (nierówności).
4. **Warunki brzegowe**: nieujemność zmiennych.

Wszystko razem = **postać kanoniczna** zadania PL.

## Przykład: kierpce i papcie
Zasoby: Ł = 14, P = 8, S = 16.

| | Kierpce (x1) | Papcie (x2) | Zasób |
|---|---|---|---|
| Ł | 2 | 2 | 14 |
| P | 1 | 2 | 8 |
| S | 4 | 0 | 16 |
| Zysk | 2 zł | 3 zł | |

Model:
- f(x1, x2) = 2x1 + 3x2 -> max
- 2x1 + 2x2 <= 14
- x1 + 2x2 <= 8
- 4x1 <= 16
- x1 >= 0, x2 >= 0

## Metoda graficzna: algorytm
1. Dla każdego ograniczenia narysuj prostą (punkty przecięcia z osiami), zaznacz właściwą półpłaszczyznę.
2. Część wspólna wszystkich półpłaszczyzn = **zbiór rozwiązań dopuszczalnych**.
3. Narysuj **warstwice** funkcji celu (2x1 + 3x2 = c) i **gradient** (2, 3), który wskazuje kierunek wzrostu f.
4. Przesuwaj warstwicę zgodnie z gradientem (max) lub przeciwnie (min) do ostatniego punktu zbioru dopuszczalnego.

Proste z przykładu (przecięcia z osiami):
- 2x1 + 2x2 = 14 -> (7,0), (0,7)
- x1 + 2x2 = 8 -> (8,0), (0,4)
- 4x1 = 16 -> x1 = 4

Wierzchołki zbioru dopuszczalnego:

| Punkt | Współrzędne | f = 2x1 + 3x2 |
|---|---|---|
| O | (0,0) | 0 |
| C | (4,0) | 8 |
| B | (4,2) | **14** |
| A | (0,4) | 12 |

B = przecięcie x1 + 2x2 = 8 oraz 4x1 = 16 -> x1 = 4, x2 = 2.

**Rozwiązanie optymalne:** x1 = 4, x2 = 2, zysk f = 14 (4 pary kierpców, 2 pary papci).

## Kluczowe wnioski
- Gradient funkcji celu: (df/dx1, df/dx2) = (2, 3).
- **Rozwiązanie optymalne leży na brzegu (powłoce) zbioru dopuszczalnego**: w wierzchołku (lub na krawędzi), bez względu na postać funkcji celu.
- Dla max idziemy z gradientem, dla min przeciwnie do gradientu.
- Wystarczy sprawdzić wierzchołki.

## Do uzupełnienia (kolejne wykłady)
- [ ] Postać bazowa (zmienne dopełniające)
- [ ] Simpleks: tablica, kryterium optymalności, wybór zmiennej wchodzącej i wychodzącej
- [ ] Przypadki szczególne (sprzeczność, nieograniczoność, wiele rozwiązań, degeneracja)
- [ ] Dualność
