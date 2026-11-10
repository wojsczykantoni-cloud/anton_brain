---
type: notatka
tags: [statystyka, egzamin, estymacja-przedzialowa, zadania]
project: ["[[Statystyka matematyczna]]"]
people: []
created: 2026-11-10
---
# Estymacja przedziałowa 3 - rozwiązania
#statystyka #egzamin

Plik źródłowy: `Estymacja_przedzia_owa_3___rozw.xlsx` (arkusze Zad. 1, Zad. 2). Wersja bez rozwiązania Zad.2, ale z porównaniem "bez korekty": [[Estymacja przedziałowa 3 - zadania]]. Wzory: [[Wzory - estymacja]]. Skrót: [[00 Ściąga - Statystyka]].

**Co to za zadania:** frakcja przy **losowaniu bezzwrotnym** z populacji skończonej (N znane): przedział ufności (zad.1) i minimalna liczebność próby (zad.2) z **poprawką na skończoność populacji**.

| Zad. | Dane | Szukamy |
|---|---|---|
| 1 | N = 500, n = 100 bezzwrotnie, k = 40 zadowolonych, gamma = 0,95 | przedział dla frakcji, delta, wdelta |
| 2 | N = 1000, delta0 = 0,05, gamma = 0,99, phat = 0,25, bezzwrotnie | min. n |

## Rozwiązanie krok po kroku

### Zad. 1
1. phat = k / n = 40 / 100 = **0,4**.
2. z_gamma = kwantyl N(0,1) rzędu 0,975 = **1,9600**.
3. Poprawka: (N - n) / ((N - 1) * n) = 400 / (499 * 100) = **0,008016**.
4. Pod pierwiastkiem: 0,008016 * 0,4 * 0,6 = 0,001924; pierwiastek = **0,04386**.
5. Błąd = 1,96 * 0,04386 = **0,08597**.
6. Przedział: P1n = 0,4 - 0,08597 = **0,3140**, P2n = 0,4 + 0,08597 = **0,4860**.
7. delta = (0,4860 - 0,3140) / 2 = **0,0860**.
8. wdelta = 0,0860 / 0,4 = **0,2149** (21,5%).

### Zad. 2
1. z_gamma = kwantyl rzędu 0,995 = **2,5758**; z^2 = 6,6349.
2. 1/N = 1/1000 = 0,001.
3. delta0^2 * (N - 1) / (N * z^2 * phat(1-phat)) = 0,0025 * 999 / (1000 * 6,6349 * 0,1875) = 2,4975 / 1244,04 = **0,0020076**.
4. Suma = 0,001 + 0,0020076 = 0,0030076.
5. n >= 1 / 0,0030076 = **332,49** -> zaokrąglamy w górę: **n = 333**.

## Wzory
Legenda: [[Wzory - estymacja#Przedział dla frakcji]], [[Wzory - estymacja#Niezbędna liczebność próby]], [[Wzory - estymacja#Wskaźnik precyzji]].

**Przedział dla frakcji, bez zwracania (Zad.1)**
- ogólny: `phat +- z_gamma * pierwiastek( (N-n)/((N-1)*n) * phat(1-phat) )`
- z liczbami: `0,4 +- 1,96 * pierwiastek( 400/(499*100) * 0,4*0,6 ) = 0,4 +- 0,0860`
- Excel PL: `p^: =B7/B6`, `z: =ROZKŁ.NORMALNY.S.ODWR(0,975)` (w pliku `NORM.S.INV(0,975)`), `P1n: =B8-B10*PIERWIASTEK((B5-B6)/((B5-1)*B6)*B8*(1-B8))`, `P2n: =B8+B10*PIERWIASTEK(...)`

**Wskaźniki precyzji (Zad.1)**
- ogólny: `delta = (P2n - P1n)/2`, `wdelta = delta/phat`
- z liczbami: `(0,4860 - 0,3140)/2 = 0,0860`, `0,0860/0,4 = 0,2149`
- Excel PL: `=(B12-B11)/2`, `=B15/B8`

**Min. liczebność bez zwracania (Zad.2)**
- ogólny: `n >= ( 1/N + delta0^2 * (N-1) / (N * z_gamma^2 * phat(1-phat)) )^(-1)`
- z liczbami: `( 0,001 + 0,0025*999/(1000*6,6349*0,1875) )^(-1) = 332,49 -> 333`
- Excel PL: `=(1/B9+B11^2*(B9-1)/(B9*B13^2*B12*(1-B12)))^(-1)` i `=ZAOKR.W.GÓRĘ(B14;0)`; z = `ROZKŁ.NORMALNY.S.ODWR(0,995)`

## Dlaczego tak
- **Poprawka (N-n)/(N-1):** gdy losujemy bez zwracania z małej populacji, próba niesie więcej informacji niż przy losowaniu ze zwracaniem, więc wariancja estymatora jest mniejsza, a przedział węższy. Słowa-klucze: "bezzwrotnie", "bez zwracania", "N = 500", "ma N elementów".
- **Zad.1:** odsetek osób zadowolonych to frakcja, więc wzór dla frakcji (z poprawką). Słowa-klucze: "odsetek", "udział".
- **Zad.2:** z warunku delta <= delta0 wyznaczamy n; w wersji bezzwrotnej wychodzi wzór "odwrócony" z 1/N. Słowa-klucze: "minimalna liczebność próby", "przy losowaniu bezzwrotnym", "wskaźnik precyzji nie przekraczał".
- **phat z wcześniejszych badań (Zad.2):** w treści "wstępne badania sugerują p = 0,25", więc używamy tej wartości, a nie 0,5.

## Interpretacja
- **Zad.1:** "Z ufnością 95% odsetek zadowolonych ze systemu premiowego wśród wszystkich 500 pracowników mieści się w (31,4%; 48,6%). Precyzja to 8,6 p.p., czyli 21,5% oszacowania."
- **Zad.2:** "Aby wskaźnik precyzji nie przekroczył 5 p.p. przy ufności 99%, trzeba zbadać co najmniej 333 gospodarstwa z 1000."

## Pułapki
- **Zaokrąglenie n w górę:** 332,49 -> 333 (nie 332).
- **Zad.1: nie pomijać poprawki.** Bez niej delta = 0,0960 (przedział 0,304; 0,496), czyli o 12% szerszy (patrz [[Estymacja przedziałowa 3 - zadania]]). Poprawka ma znaczenie, gdy n/N jest duże (tu 20%); przy n/N < 5% można ją pominąć.
- **N-1 w mianowniku**, nie N: `(N-n)/((N-1)*n)`, nie `(N-n)/(N*n)`.
- **Zad.2 daje mniejsze n niż wersja bez korekty:** bez poprawki n >= 0,1875 * 6,6349 / 0,0025 = 497,6 -> 498; z poprawką 333. Sprawdź, czy w treści jest "bezzwrotnie".
- **Wzór na n w Zad.2 jest "do potęgi -1"** (cała suma w nawiasie), w Excelu `^(-1)`.
- **P(|Z| < z_gamma) = gamma:** z_gamma to kwantyl rzędu (1+gamma)/2 (0,975 dla 95%, 0,995 dla 99%).
