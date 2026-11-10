---
type: notatka
tags: [statystyka, egzamin, estymacja-przedzialowa, zadania]
project: ["[[Statystyka matematyczna]]"]
people: []
created: 2026-11-10
---
# Estymacja przedziałowa 1 - zadania
#statystyka #egzamin

Plik źródłowy: `Estymacja_przedzia_owa_1.xlsx` (arkusze Zad.1 - Zad.9). **W pliku są tylko treści zadań, bez żadnych obliczeń** (puste komórki, na arkuszach Zad.8 i Zad.9 tylko obrazki ze wzorami). Zad.1, 2, 4, 6 mają rozwiązania w osobnym pliku: [[Estymacja przedziałowa 1 - rozwiązania]]. Zad.3, 5, 7, 8, 9 **policzyłem sam** według wzorów z [[Wzory - estymacja]] i oznaczam je jako "policzone przeze mnie" (sprawdź z prowadzącym).

| Zad. | Treść w skrócie | Typ | Rozwiązanie |
|---|---|---|---|
| 1 | dyskonto, sigma = 8 znane, n = 36, 95% | średnia, wzór 1 | [[Estymacja przedziałowa 1 - rozwiązania#Zad.1]] |
| 2 | stopa zwrotu, n = 15, Shat = 3,5, 92% | średnia, wzór 3 | [[Estymacja przedziałowa 1 - rozwiązania#Zad.2]] |
| 3 | baterie, n = 12, xsr = 34,2 h, Shat = 5,9, 90% | średnia, wzór 3 | niżej (policzone przeze mnie) |
| 4 | odszkodowania, n = 165, 95% i 99% | średnia, wzór 2 | [[Estymacja przedziałowa 1 - rozwiązania#Zad.4]] |
| 5 | domy, n = 200, xsr = 647 000, Shat = 140 000, 80% | średnia, wzór 2 | niżej (policzone przeze mnie) |
| 6 | 34 z 100, 95% | frakcja | [[Estymacja przedziałowa 1 - rozwiązania#Zad.6]] |
| 7 | 53 z 250 par, 90% | frakcja | niżej (policzone przeze mnie) |
| 8 | wydatki kuracjuszy, delta0 = 120, sigma = 400 znane, 95% | min. n, średnia | niżej (policzone przeze mnie) |
| 9 | frakcja ok. 0,25, delta0 = 0,10, 99% | min. n, frakcja | niżej (policzone przeze mnie) |

Wszystkie zadania kończą się poleceniem: "Wyznacz wskaźnik precyzji estymacji oraz względny wskaźnik precyzji estymacji" (zad.8, 9 pytają o liczebność).

## Rozwiązanie krok po kroku (tylko zadania bez rozwiązania w pliku)

### Zad.3
*policzone przeze mnie: baterie*
1. n = 12 < 30, rozkład normalny, sigma nieznane -> **wzór 3**.
2. gamma = 0,90: t_gamma = T.INV(0,95; 11) = **1,7959**.
3. S = pierwiastek(11/12) * 5,9 = **5,6488**.
4. Błąd = 1,7959 * 5,6488 / pierwiastek(11) = **3,0587** h.
5. Przedział: 34,2 -+ 3,0587 = **(31,14; 37,26)** godz.
6. delta = **3,0587**; wdelta = 3,0587 / 34,2 = **0,0894** (8,94%).

### Zad.5
*policzone przeze mnie: domy w Ventura County*
1. n = 200 >= 30, sigma nieznane -> **wzór 2**.
2. gamma = 0,80: u = kwantyl rzędu 0,90 = **1,2816**.
3. S = pierwiastek(199/200) * 140 000 = **139 649,56**.
4. Błąd = 1,2816 * 139 649,56 / pierwiastek(200) = **12 654,96** $.
5. Przedział: 647 000 -+ 12 654,96 = **(634 345,04; 659 654,96)** $.
6. delta = **12 654,96**; wdelta = 12 654,96 / 647 000 = **0,0196** (1,96%).
(Wariant z Shat/pierwiastek(n): błąd 12 686,71, różnica symboliczna.)

### Zad.7
*policzone przeze mnie: trudności z podziałem majątku*
1. phat = 53 / 250 = **0,212**.
2. gamma = 0,90: u = **1,6449**.
3. Błąd = 1,6449 * pierwiastek(0,212 * 0,788 / 250) = 1,6449 * 0,02585 = **0,04252**.
4. Przedział: **(0,1695; 0,2545)**.
5. delta = **0,0425**; wdelta = 0,0425 / 0,212 = **0,2006** (20,1%).

### Zad.8
*policzone przeze mnie: wydatki na rozrywki, sigma znane*
1. Wskaźnik precyzji delta = u * sigma / pierwiastek(n) <= delta0 = 120; sigma = 400 znane (w arkuszu opisy "sigma znane" / "sigma nieznane": wybieramy wariant "znane").
2. u = **1,9600**.
3. n >= sigma^2 * u^2 / delta0^2 = 400^2 * 1,96^2 / 120^2 = 160 000 * 3,8415 / 14 400 = **42,68**.
4. Zaokrąglamy w górę: **n = 43**.

### Zad.9
*policzone przeze mnie: frakcja zainteresowanych*
1. phat ok. 0,25 (dane firmy), delta0 = 0,10, gamma = 0,99: u = **2,5758**.
2. n >= phat(1-phat) * u^2 / delta0^2 = 0,25 * 0,75 * 6,6349 / 0,01 = **124,40**.
3. Zaokrąglamy w górę: **n = 125**.

## Wzory
Ogólne i legenda: [[Wzory - estymacja#Przedział dla średniej]], [[Wzory - estymacja#Przedział dla frakcji]], [[Wzory - estymacja#Niezbędna liczebność próby]].

**Zad.3** (wzór 3)
- ogólny: `xsr +- t_gamma * S / pierwiastek(n-1)`
- z liczbami: `34,2 +- 1,7959 * 5,6488 / pierwiastek(11)`
- Excel PL: `=34,2-ROZKŁ.T.ODWR(0,95;11)*PIERWIASTEK(11/12)*5,9/PIERWIASTEK(11)` (i `+`)

**Zad.5** (wzór 2)
- ogólny: `xsr +- u_gamma * S / pierwiastek(n)`
- z liczbami: `647000 +- 1,2816 * 139649,56 / pierwiastek(200)`
- Excel PL: `=647000-ROZKŁ.NORMALNY.S.ODWR(0,9)*PIERWIASTEK(199/200)*140000/PIERWIASTEK(200)` (i `+`)

**Zad.7** (frakcja)
- ogólny: `phat +- u_gamma * pierwiastek(phat(1-phat)/n)`
- z liczbami: `0,212 +- 1,6449 * pierwiastek(0,212*0,788/250)`
- Excel PL: `=53/250-ROZKŁ.NORMALNY.S.ODWR(0,95)*PIERWIASTEK((53/250)*(1-53/250)/250)` (i `+`)

**Zad.8** (sigma znane)
- ogólny: `n >= sigma^2 * u_gamma^2 / delta0^2` (z nierówności `u*sigma/pierwiastek(n) <= delta0`)
- z liczbami: `400^2 * 1,96^2 / 120^2 = 42,68 -> 43`
- Excel PL: `=ZAOKR.W.GÓRĘ(400^2*ROZKŁ.NORMALNY.S.ODWR(0,975)^2/120^2;0)`
- wariant sigma nieznane: `n >= Shat^2 * t_gamma^2 / delta0^2` (zob. [[Estymacja przedziałowa 2 - rozwiązania#Zad. 1]])

**Zad.9** (frakcja)
- ogólny: `n >= phat(1-phat) * u_gamma^2 / delta0^2`
- z liczbami: `0,25*0,75*2,5758^2/0,10^2 = 124,40 -> 125`
- Excel PL: `=ZAOKR.W.GÓRĘ(0,25*0,75*ROZKŁ.NORMALNY.S.ODWR(0,995)^2/0,1^2;0)`

## Dlaczego tak
- **Zad.3:** mała próba (12), rozkład normalny, sigma nieznane -> t-Studenta. Słowa-klucze: "S^ = ...", "rozkład normalny", n = 12.
- **Zad.5:** n = 200 jest duże, więc t ~ u; sigma nieznane (S^), stąd wzór 2. Słowo-klucz: "odchylenie standardowe z próby".
- **Zad.7:** to frakcja (53 z 250). Słowa-klucze: "frakcja", "ile ma trudności".
- **Zad.8:** polecenie "wskaźnik precyzji nie większy niż" + "minimalna wymagana liczebność" = nierówność delta <= delta0 rozwiązana względem n. Słowo-klucz: "odchylenie standardowe w populacji wynosi 400" -> sigma znane, kwantyl u.
- **Zad.9:** frakcja p około 0,25 znana z bieżących danych, więc podstawiamy ją zamiast najgorszego p = 0,5 (mniejsza próba).

## Interpretacja
- **Zad.3:** "Z ufnością 90% przeciętna długość życia bateryjki mieści się w przedziale 31,1 - 37,3 h; precyzja to 3,06 h (8,9%)."
- **Zad.5:** "Z ufnością 80% przeciętna wartość domu w Ventura County to 634 345 - 659 655 $; błąd maksymalny 12 655 $, czyli 1,96% średniej: bardzo precyzyjne oszacowanie."
- **Zad.7:** "Z ufnością 90% od 17,0% do 25,5% rozwiedzionych par ma duże trudności w podziale majątku."
- **Zad.8, 9:** "Aby wskaźnik precyzji nie przekroczył zadanej wartości przy podanej ufności, trzeba zbadać co najmniej 43 kuracjuszy (zad.8) / 125 osób (zad.9)."

## Pułapki
- **Zad.1 - 6 w tym pliku nie mają obliczeń** (tylko treść); rozwiązania są w [[Estymacja przedziałowa 1 - rozwiązania]].
- **Zad.8:** nie mylić wariantów (sigma znane: u i sigma^2; sigma nieznane: t i Shat^2 + n-1 stopni z próby pilotażowej). W treści jest "odchylenie standardowe w populacji", więc **u**.
- **Zad.9:** nie podstawiać 0,5, skoro znamy przybliżone p = 0,25 (z 0,5 wyszłoby 0,25 * 6,6349 / 0,01 = 166 -> 166); treść wprost mówi o "ok. 0,25".
- **Zad.5:** dane liczbowe w jednostkach dolarów, nie tysiącach; "647 000$" to xsr (nie średnia populacji).
- **Zawsze zaokrąglaj n w górę.**
- **Kwantyl dla gamma = 0,80:** (1+0,8)/2 = 0,9, dla 0,90: 0,95, dla 0,99: 0,995.
