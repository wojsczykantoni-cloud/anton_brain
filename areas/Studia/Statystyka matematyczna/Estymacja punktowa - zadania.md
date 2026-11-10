---
type: notatka
tags: [statystyka, egzamin, estymacja-punktowa, zadania]
project: ["[[Statystyka matematyczna]]"]
people: []
created: 2026-11-10
---
# Estymacja punktowa - zadania
#statystyka #egzamin

Plik źródłowy: `Estymacja_punktowa.xlsx` (arkusze zad.1 - zad.10). Teoria: [[Estymacja punktowa]]. Wzory: [[Wzory - estymacja]]. Skrót: [[00 Ściąga - Statystyka]].

**Co to za zadania:** estymacja punktowa, czyli jedna liczba jako ocena parametru (średnia, wariancja, frakcja), jej średni błąd szacunku, błąd średniokwadratowy i minimalna liczebność próby dla zadanej precyzji.

| Zad. | Dane w arkuszu | Szukamy |
|---|---|---|
| 1 | 12 kwot na kontach (A6:A17), n = 12 | xsr, S2hat, Dhat(xsr) |
| 2 | 17 cen kawy (A7:A23), n = 17 | xsr, S2hat, odch. std., Dhat(xsr) |
| 3 | te same 12 kwot, próg 100 zł | phat, Dhat(phat) |
| 4 | m = 1065, sigma = 500, n = 100 | E(xsr), D2(xsr), b, MSE |
| 5 | m = 53, sigma = 10, n = 400 | E(xsr), D2(xsr), D(xsr) |
| 6 | sigma^2 = 1 000 000, D(xsr) <= 26 | min. n |
| 7 | S2hat = 185 (pilotaż), Dhat(xsr) <= 1,2 | min. n |
| 8 | p = 0,22, Dhat(phat) <= 0,015 | min. n |
| 9 | p nieznane, Dhat(phat) <= 0,015 | min. n |
| 10 | m = 1,4, sigma^2 = 1,04, n od 1 do 220 | D(xsr) i względny błąd V |

## Rozwiązanie krok po kroku

### Zad.1
*konta bankowe, n = 12*
1. Suma kwot: 87,5 + 123,1 + ... + 102,11 = **1175,07**.
2. xsr = 1175,07 / 12 = **97,9225** zł.
3. Odchylenia xi - xsr (kol. C) i ich kwadraty (kol. D), np. 87,5 - 97,9225 = -10,4225, kwadrat 108,6285.
4. Suma kwadratów odchyleń = **29 550,181**.
5. S2hat = 29 550,181 / (12 - 1) = **2686,380** (oszacowanie wariancji kwot).
6. Dhat(xsr) = pierwiastek(2686,380 / 12) = **14,962** zł.

### Zad.2
*ceny kawy, n = 17*
1. Suma cen = **74,25**; xsr = 74,25 / 17 = **4,3676**.
2. Suma kwadratów odchyleń (kol. C) = **1,94471**.
3. S2hat = 1,94471 / 16 = **0,12154** (wariancja).
4. Odchylenie standardowe Shat = pierwiastek(0,12154) = **0,3486**. (Arkusz tego nie liczy, patrz Pułapki.)
5. Dhat(xsr) = pierwiastek(0,12154 / 17) = **0,08456**.

### Zad.3
*frakcja kont > 100 zł*
1. Liczymy konta > 100: 123,1; 213; 155; 132; 102,11 -> K = **5** z n = 12 (99,99 nie jest > 100).
2. phat = 5 / 12 = **0,4167**.
3. Dhat(phat) = pierwiastek(0,4167 * 0,5833 / 12) = **0,1423**.

### Zad.4
*m = 1065, sigma = 500, n = 100*
1. E(xsr) = m = **1065**.
2. D2(xsr) = 500^2 / 100 = **2500**.
3. Obciążenie b = E(xsr) - m = 1065 - 1065 = **0**.
4. MSE = D2 + b^2 = 2500 + 0 = **2500**; RMSE = pierwiastek(2500) = **50**.

### Zad.5
*m = 53, sigma = 10, n = 400*
1. E(xsr) = **53**.
2. D2(xsr) = 10^2 / 400 = **0,25**.
3. D(xsr) = pierwiastek(0,25) = **0,5**.

### Zad.6
*sigma^2 = 1 000 000, D(xsr <= 26)*
1. D2(xsr) = sigma^2 / n <= 26^2 = 676.
2. n >= 1 000 000 / 676 = 1479,29.
3. Zaokrąglamy w górę: **n = 1480**.

### Zad.7
*S2hat = 185, Dhat(xsr <= 1,2)*
1. Dhat2(xsr) = S2hat / n <= 1,2^2 = 1,44.
2. n >= 185 / 1,44 = 128,47 -> **n = 129**.

### Zad.8
*p = 0,22, Dhat(phat <= 0,015)*
1. p(1-p) = 0,22 * 0,78 = 0,1716; 0,015^2 = 0,000225.
2. n >= 0,1716 / 0,000225 = 762,67 -> **n = 763**.

### Zad.9
*p nieznane, Dhat(phat <= 0,015)*
1. Brak informacji o p, więc bierzemy najgorszy przypadek p = 0,5: p(1-p) = 0,25.
2. n >= 0,25 / 0,000225 = 1111,11 -> **n = 1112**.

### Zad.10
*m = 1,4, sigma^2 = 1,04, sigma = 1,0198*
D(xsr) = sigma / pierwiastek(n), V = D(xsr) / m.

| n | D(xsr) | V |
|---|---|---|
| 1 | 1,0198 | 72,84% |
| 2 | 0,7211 | 51,51% |
| 3 | 0,5888 | 42,06% |
| 4 | 0,5099 | 36,42% |
| 5 | 0,4561 | 32,58% |
| 10 | 0,3225 | 23,04% |
| 20 | 0,2280 | 16,29% |
| 30 | 0,1862 | 13,30% |
| 50 | 0,1442 | 10,30% |
| 100 | 0,1020 | 7,28% |
| 220 | 0,0688 | 4,91% |

## Wzory
Ogólne wzory i legenda: [[Wzory - estymacja#Średnia i wariancja z próby]], [[Wzory - estymacja#Estymacja punktowa]], [[Wzory - estymacja#Niezbędna liczebność próby]]. Poniżej: ogólny wzór / z liczbami / Excel PL (nazwy PL do zweryfikowania, patrz [[Wzory - estymacja#Funkcje Excela po polsku]]).

**Średnia (zad.1, 2)**
- ogólny: `xsr = (1/n) * suma(xi)`
- z liczbami: `xsr = (1/12) * 1175,07 = 97,9225`
- Excel PL: `=ŚREDNIA(A6:A17)` (w pliku: `=AVERAGE(A6:A17)`); kontrolnie `=1/12*A18` w D22. W zad.2: `=1/17*A24` => 4,3676.

**Wariancja z próby (zad.1, 2)**
- ogólny: `S2hat = (1/(n-1)) * suma((xi - xsr)^2)`
- z liczbami: `S2hat = 29550,181 / 11 = 2686,380`
- Excel PL: `=WARIANCJA.A(A6:A17)` (w pliku `=VARA(A6:A17)`), kontrolnie `=(1/(B19-1))*D18`. Zalecane: `=WARIANCJA.PRÓBKI(A6:A17)`. Zad.2: `=(1/(17-1))*C24` => 0,12154.

**Średni błąd szacunku średniej (zad.1, 2)**
- ogólny: `Dhat(xsr) = pierwiastek(S2hat / n)`
- z liczbami: `pierwiastek(2686,380 / 12) = 14,962`; zad.2: `pierwiastek(0,12154 / 17) = 0,08456`
- Excel PL: `=PIERWIASTEK(D23/B19)`; zad.2: `=PIERWIASTEK(D27/17)`

**Frakcja (zad.3)**
- ogólny: `phat = K/n`, `Dhat(phat) = pierwiastek(phat(1-phat)/n)`
- z liczbami: `phat = 5/12 = 0,4167`, `Dhat = pierwiastek(0,4167*0,5833/12) = 0,1423`
- Excel PL: `=LICZ.JEŻELI(A7:A18;">100")` => 5, `=E19/C19`, `=PIERWIASTEK(C21*(1-C21)/C19)`

**Błąd średniokwadratowy (zad.4)**
- ogólny: `D2(xsr) = sigma^2/n`, `b = E(xsr) - m`, `MSE = D2 + b^2`, `RMSE = pierwiastek(MSE)`
- z liczbami: `D2 = 500^2/100 = 2500`, `b = 0`, `MSE = 2500`, `RMSE = 50`
- Excel PL: `=B8^2/B9`, `=B11-B7`, `=B12+B13^2`, `=PIERWIASTEK(B14)`

**Średnia z próby (zad.5)**
- ogólny: `D2(xsr) = sigma^2/n`, `D(xsr) = pierwiastek(D2)`
- z liczbami: `100/400 = 0,25`, `pierwiastek(0,25) = 0,5`
- Excel PL: `=E6^2/E4`, `=PIERWIASTEK(B7)`

**Min. liczebność (zad.6 - 9)**
- ogólny: `n >= sigma^2 / D^2` (zad.6), `n >= S2hat / D^2` (zad.7), `n >= p(1-p) / D^2` (zad.8, 9)
- z liczbami: `1000000/676 = 1479,29 -> 1480`; `185/1,44 = 128,47 -> 129`; `0,22*0,78/0,000225 = 762,67 -> 763`; `0,5*0,5/0,000225 = 1111,11 -> 1112`
- Excel PL: `=B4/B6` i `=ZAOKR.W.GÓRĘ(E4;0)`; `=B7/D9`, `=ZAOKR.W.GÓRĘ(B11;0)`; `=B7*(1-B7)/B9`, `=ZAOKR.W.GÓRĘ(B6;0)`; `=B8*(1-B8)/B10`, `=ZAOKR.W.GÓRĘ(B11;0)`

**Względny błąd (zad.10)**
- ogólny: `D(xsr) = sigma/pierwiastek(n)`, `V = D(xsr)/m`
- z liczbami (n = 100): `1,0198/10 = 0,1020`, `V = 0,1020/1,4 = 7,28%`
- Excel PL: `=$B$20/PIERWIASTEK(A6)` i `=B6/$B$18`, gdzie B20 = `=PIERWIASTEK(B19)` = sigma

## Dlaczego tak
- **Zad.1, 2 (S2hat, n-1):** nieznaną wariancję populacji szacujemy z próby; dzielimy przez n-1, bo wtedy estymator jest nieobciążony (E(S2hat) = sigma^2). Słowa-klucze: "oszacuj wariancję", "szacowany średni błąd".
- **Zad.1, 2 (Dhat(xsr)):** średnia z próby ma rozrzut sigma/pierwiastek(n); sigma nieznane, więc wstawiamy Shat. Słowo-klucz: "średni błąd szacunku dla estymatora średniej".
- **Zad.3:** frakcja to wartość oczekiwana zmiennej 0-1, więc phat = K/n, a wariancja wynika z rozkładu dwumianowego. Słowa-klucze: "frakcja", "udział", "odsetek kont powyżej".
- **Zad.4, 5:** parametry populacji są znane, więc liczymy teoretyczne E i D2 średniej z próby (bez szacowania). Słowa-klucze: "wartość oczekiwana i wariancja dla średniej z próby", "błąd średniokwadratowy".
- **MSE = D2 + b^2:** łączy rozrzut i obciążenie; dla estymatora nieobciążonego MSE = D2.
- **Zad.6, 7:** z warunku "błąd co najwyżej" robimy nierówność na D i rozwiązujemy względem n. Zad.7: sigma nieznane, więc używamy wariancji z pilotażu. Słowa-klucze: "minimalna liczebność", "co najwyżej".
- **Zad.8, 9:** to samo dla frakcji; gdy p nieznane, bierzemy p = 0,5, bo wtedy p(1-p) jest największe i próba wystarczy dla każdego p. Słowa-klucze: "absolutna pewność", "niezależnie od".
- **Zad.10:** pokazuje, jak błąd maleje z n (pierwiastek z n): żeby błąd spadł o połowę, trzeba 4 razy większej próby.

## Interpretacja
- **Zad.1:** "Średnia kwota na kontach firmy jest szacowana na 97,92 zł. Wariancja kwot wynosi ok. 2686,38. Szacunek średniej myli się średnio o ok. 14,96 zł (od rzeczywistej średniej)."
- **Zad.3:** "Szacujemy, że 41,67% kont ma kwotę powyżej 100 zł; średni błąd tego szacunku wynosi 14,2 punktu procentowego."
- **Zad.4:** "Estymator jest nieobciążony (b = 0), więc błąd średniokwadratowy równa się wariancji i wynosi 2500; średnio średnia z próby odchyla się od m o 50."
- **Zad.6 - 9:** "Aby średni błąd szacunku nie przekraczał zadanej wartości, trzeba wylosować co najmniej 1480 (129, 763, 1112) jednostek."
- **Zad.10:** "Przy n = 100 średnia z próby odchyla się od m średnio o 0,102, czyli 7,3% wartości oczekiwanej."

## Pułapki
- **n czy n-1:** S2hat dzieli przez n-1, S2 przez n. W tym pliku wszędzie n-1 (poza kontrolnym `1/12*A18`, które dotyczy średniej).
- **Wariancja kontra odchylenie:** zad.2 w arkuszu: D27 ma etykietę "szacowane odchylenie standardowe", ale to **wariancja** (0,12154); odchylenie to 0,3486. **Błąd w arkuszu, popraw w zeszycie.**
- **Zad.4 etykiety:** B7 "xsr" to naprawdę m (średnia populacji); B8 "sigma ^2" to naprawdę sigma = 500 (formuła B12 podnosi do kwadratu, więc liczby są OK). Formuła obciążenia `B13 = B11 - B7` jest zawsze 0, bo B11 = B7; sensowniej b = E(xsr) - m.
- **Zad.1:** używa `VARA` (WARIANCJA.A), a nie funkcji dla próby; dla zwykłych liczb wynik ten sam co WARIANCJA.PRÓBKI, ale lepiej używać tej drugiej.
- **Zad.6 i "+1":** arkusz bierze n >= sigma^2/D^2 bez "+1"; skrypt z wykładu ([[Estymacja punktowa]]) ma wzór z "+1" (np. dla d daje 1481). Zapytaj prowadzącego, którą wersję stosuje; arkusz = 1480.
- **Zad.8:** w arkuszu etykieta B8 to "D^(xsr)", a chodzi o błąd frakcji D(phat).
- **Zad.10:** kolumna "odchylenie" to odchylenie standardowe **średniej** (sigma/pierwiastek(n)), nie sigma.
- **Zawsze zaokrąglaj n w górę** (`ZAOKR.W.GÓRĘ`), nigdy zwykłym zaokrągleniem.
- **Nie mylić** błędu średniokwadratowego (MSE, wariancja) z RMSE (pierwiastek, w jednostkach danych).
