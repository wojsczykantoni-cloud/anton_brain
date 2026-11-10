---
type: notatka
tags: [statystyka, egzamin, estymacja-przedzialowa, zadania]
project: ["[[Statystyka matematyczna]]"]
people: []
created: 2026-11-10
---
# Estymacja przedziałowa 1 - rozwiązania
#statystyka #egzamin

Plik źródłowy: `Estymacja_przedzia_owa_1_-_rozw.xlsx` (arkusze Zad.1, Zad.2, Zad. 4, Zad. 6). Pełny zestaw bez rozwiązań: [[Estymacja przedziałowa 1 - zadania]]. Wzory: [[Wzory - estymacja]]. Skrót: [[00 Ściąga - Statystyka]].

**Co to za zadania:** przedział ufności dla **średniej** (zad.1, 2, 4) i dla **frakcji** (zad.6), a do tego wskaźnik precyzji delta (połowa długości przedziału) i względny wskaźnik precyzji wdelta = delta / estymator.

| Zad. | Dane | Wzór |
|---|---|---|
| 1 | dyskonto: xsr = 20%, sigma = 8% (znane), n = 36, gamma = 0,95, rozkład normalny | wzór 1 |
| 2 | stopa zwrotu: n = 15, xsr = 10,37%, Shat = 3,5%, gamma = 0,92, rozkład normalny | wzór 3 (t) |
| 4 | odszkodowania: n = 165, xsr = 16 530, Shat = 5542, gamma = 0,95 i 0,99 | wzór 2 |
| 6 | 34 z 100 kupuje produkt zagraniczny, gamma = 0,95 | przedział dla frakcji |

## Rozwiązanie krok po kroku

### Zad.1
1. Który wzór: n = 36 >= 30, sigma znane -> **wzór 1** (można też z n < 30 przy rozkładzie normalnym).
2. u_gamma = kwantyl N(0,1) rzędu 0,975 = **1,9600**.
3. Błąd = u * sigma / pierwiastek(n) = 1,96 * 8 / 6 = **2,6133**.
4. Przedział: 20 - 2,6133 = **17,3867** i 20 + 2,6133 = **22,6133** (%).
5. delta = (22,6133 - 17,3867) / 2 = **2,6133** p.p.
6. wdelta = 2,6133 / 20 = **0,1307** (13,07%).

### Zad.2
1. n = 15 < 30, rozkład normalny, sigma nieznane -> **wzór 3** (t-Studenta, 14 stopni swobody).
2. S (dzielnik n) = pierwiastek(14/15) * 3,5 = **3,3813**.
3. gamma = 0,92, więc dwustronne alfa = 0,08; t_gamma = **1,8875**.
4. Błąd = t * S / pierwiastek(n-1) = 1,8875 * 3,3813 / pierwiastek(14) = **1,7057**.
5. Przedział: 10,37 - 1,7057 = **8,6643**, 10,37 + 1,7057 = **12,0757** (%).
6. delta = **1,7057**; wdelta = 1,7057 / 10,37 = **0,1645** (16,45%).

### Zad.4
a) gamma = 0,95
1. n = 165 >= 30, sigma nieznane -> **wzór 2** (u z N(0,1)).
2. S = pierwiastek(164/165) * 5542 = **5525,18**.
3. u = **1,9600**; błąd = 1,96 * 5525,18 / pierwiastek(165) = **843,05**.
4. Przedział: **(15 686,95; 17 373,05)**.
5. delta = **843,05**; wdelta = 843,05 / 16 530 = **0,0510** (5,10%).

b) gamma = 0,99
1. u = kwantyl rzędu 0,995 = **2,5758**.
2. Błąd = 2,5758 * 5525,18 / pierwiastek(165) = **1107,95**.
3. Przedział: **(15 422,05; 17 637,95)**.
4. delta = **1107,95**; wdelta = **0,0670** (6,70%).

### Zad.6
1. phat = 34 / 100 = **0,34**.
2. u = **1,9600**.
3. Błąd = u * pierwiastek(phat(1-phat)/n) = 1,96 * pierwiastek(0,34*0,66/100) = 1,96 * 0,04737 = **0,09285**.
4. Przedział: **(0,2472; 0,4328)**.
5. delta = **0,0928**; wdelta = 0,0928 / 0,34 = **0,2731** (27,3%).

## Wzory
Pełna legenda: [[Wzory - estymacja#Przedział dla średniej]], [[Wzory - estymacja#Przedział dla frakcji]], [[Wzory - estymacja#Wskaźnik precyzji]].

**Przedział dla średniej, sigma znane (Zad.1)**
- ogólny: `xsr +- u_gamma * sigma / pierwiastek(n)`
- z liczbami: `20 +- 1,9600 * 8 / pierwiastek(36) = 20 +- 2,6133`
- Excel PL: `=20-B10*8/6` oraz `=20+B10*8/6`, gdzie `B10 = ROZKŁ.NORMALNY.S.ODWR(0,975)` (w pliku `NORM.S.INV(0,975)`)

**Przedział dla średniej, wzór 3 (Zad.2)**
- ogólny: `xsr +- t_gamma * S / pierwiastek(n-1)`, `S = pierwiastek((n-1)/n) * Shat`
- z liczbami: `10,37 +- 1,8875 * 3,3813 / pierwiastek(14) = 10,37 +- 1,7057`
- Excel PL: `S: =PIERWIASTEK(14/15)*3,5`; `t: =ROZKŁ.T.ODWR.DS(0,08;14)` (w pliku `TINV(0,08;14)`); `=10,37-B8*B7/PIERWIASTEK(14)`, `=10,37+B8*B7/PIERWIASTEK(14)`

**Przedział dla średniej, wzór 2 (Zad.4)**
- ogólny: `xsr +- u_gamma * S / pierwiastek(n)`
- z liczbami: `16530 +- 1,9600 * 5525,18 / pierwiastek(165) = 16530 +- 843,05`
- Excel PL: `=PIERWIASTEK(164/165)*5542`, `=16530-B8*B7/PIERWIASTEK(165)`, `=16530+B8*B7/PIERWIASTEK(165)`; dla 99%: `ROZKŁ.NORMALNY.S.ODWR(0,995)`

**Przedział dla frakcji (Zad.6)**
- ogólny: `phat +- u_gamma * pierwiastek(phat(1-phat)/n)`
- z liczbami: `0,34 +- 1,96 * pierwiastek(0,34*0,66/100) = 0,34 +- 0,0928`
- Excel PL: `=34/100`, `=B5-B6*PIERWIASTEK(B5*(1-B5)/100)`, `=B5+B6*PIERWIASTEK(B5*(1-B5)/100)`

**Wskaźniki precyzji (wszystkie zad.)**
- ogólny: `delta = (T2 - T1)/2`, `wdelta = delta / estymator`
- z liczbami (Zad.6): `(0,4328 - 0,2472)/2 = 0,0928`, `0,0928/0,34 = 0,2731`
- Excel PL: `=(C7-B7)/2`, `=B8/B5`

## Dlaczego tak
- **Wzór 1 (sigma znane):** gdy znamy sigma, standaryzowana średnia ma rozkład N(0,1), więc używamy kwantyla u. Słowa-klucze: "wiemy, że sigma = ...".
- **Wzór 3 (sigma nieznane, mała próba):** gdy sigma wstawiamy z próby, a n jest małe, rozkład ma "grubsze ogony" (t-Studenta, n-1 stopni swobody), więc kwantyl t jest większy niż u. Słowa-klucze: "S^ = ...", "rozkład normalny", małe n.
- **Wzór 2 (sigma nieznane, duża próba):** dla n >= 30 rozkład t jest praktycznie równy N(0,1), więc zamiast t bierzemy u. Słowa-klucze: "S^ = ...", n >= 30.
- **Przedział dla frakcji:** przy dużym n frakcja z próby ma w przybliżeniu rozkład normalny. Słowa-klucze: "udział", "ile osób z ... kupuje".
- **delta i wdelta:** delta to maksymalny błąd oszacowania w jednostkach danych, wdelta mówi, jaki to ułamek estymatora (porównywalny między zadaniami). Słowa-klucze: "wskaźnik precyzji estymacji".
- **Wyższy poziom ufności (zad.4b):** większe gamma -> większy kwantyl -> szerszy przedział i mniejsza precyzja.

## Interpretacja
- **Zad.1:** "Z ufnością 95% przedział (17,39%; 22,61%) pokrywa nieznaną średnią wartość dyskonta w populacji funduszy. Wskaźnik precyzji wynosi 2,61 p.p., czyli 13,07% średniej oszacowania."
- **Zad.2:** "Z ufnością 92% przeciętna stopa zwrotu z akcji zawiera się w przedziale (8,66%; 12,08%). Precyzja oszacowania to 1,71 p.p. (16,45%)."
- **Zad.4:** "Z ufnością 95% przeciętne żądane odszkodowanie mieści się w przedziale (15 687; 17 373), a z ufnością 99% w szerszym (15 422; 17 638); wyższa ufność = mniejsza precyzja (5,1% vs 6,7%)."
- **Zad.6:** "Z ufnością 95% udział produktów zagranicznych w rynku wynosi od 24,7% do 43,3%; przedział jest szeroki (wdelta = 27,3%), bo próba to tylko 100 osób."
- Standardowa fraza: "przedział ufności pokrywa nieznaną wartość parametru z prawdopodobieństwem gamma" (nie: "parametr leży w przedziale z prawdopodobieństwem gamma").

## Pułapki
- **Dobór wzoru:** zacznij od schematu ([[Wzory - estymacja#Który wzór]]): n >= 30?, sigma znane?, rozkład normalny?
- **n kontra n-1 w S:** w wzorze 3 jest S/pierwiastek(n-1) z S o dzielniku n; w treści zadań "S^" to zwykle Shat (dzielnik n-1). Dlatego w arkuszu najpierw przeliczono `S = pierwiastek((n-1)/n) * Shat`. Równoważnie: `t * Shat / pierwiastek(n)`.
- **Zad.2 vs Zad.4:** Zad.2 dzieli przez pierwiastek(n-1) (wzór 3), Zad.4 przez pierwiastek(n) (wzór 2 ze slajdu). To nie błąd, to dwa różne wzory. Gdyby w Zad.4 użyć Shat/pierwiastek(n), wyjdzie błąd 845,61 zamiast 843,05, czyli przedział (15 684,39; 17 375,61): przy n = 165 różnica jest nieistotna, ale na egzaminie trzymaj się wzoru z wykładu.
- **TINV kontra T.INV:** `TINV(0,08;14)` bierze dwustronne alfa (1-gamma), a `T.INV(0,975;14)` lewostronne (1-alfa/2). Pomylenie argumentu daje zły kwantyl.
- **Kwantyl dla gamma:** zawsze (1+gamma)/2: dla 95% -> 0,975, dla 99% -> 0,995, dla 92% -> 0,96.
- **wdelta:** dzielimy przez estymator (xsr lub phat), nie przez delta.
- **Procenty:** w zad.1 i 2 wyniki są w %, więc delta w p.p.
