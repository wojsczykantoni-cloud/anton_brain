---
type: notatka
tags: [statystyka, egzamin, sciaga]
project: ["[[Statystyka matematyczna]]"]
people: []
created: 2026-11-10
---
# 00 Ściąga - Statystyka
#statystyka #egzamin

Zakres: estymacja punktowa i przedziałowa (zadania z Excela). Pełne wzory i legenda: [[Wzory - estymacja]]. Teoria z wykładu: [[Estymacja punktowa]]. Hub: [[Statystyka matematyczna]].

Zapis: `xsr` średnia z próby, `S2` wariancja z dzielnikiem n, `S2hat` z dzielnikiem n-1 (`Shat` = pierwiastek), `phat` frakcja, `u` kwantyl N(0,1) rzędu (1+gamma)/2, `t` kwantyl t-Studenta (n-1 stopni swobody), `delta` połowa długości przedziału, `delta0` dopuszczalna precyzja.

## Typy zadań

| Typ zadania | Po czym go poznać | Wzór | Funkcja Excela PL | Przykład |
|---|---|---|---|---|
| Ocena średniej | "oszacuj średnią", lista danych | xsr = suma(xi)/n | `ŚREDNIA` | [[Estymacja punktowa - zadania#Zad.1]] |
| Ocena wariancji / odch. std. | "oszacuj wariancję", "odchylenie standardowe" | S2hat = suma((xi-xsr)^2)/(n-1) | `WARIANCJA.PRÓBKI` (w pliku `WARIANCJA.A`), `ODCH.STANDARD.PRÓBKI` | [[Estymacja punktowa - zadania#Zad.2]] |
| Średni błąd szacunku średniej | "średni błąd szacunku dla estymatora średniej" | Dhat(xsr) = pierwiastek(S2hat/n) | `PIERWIASTEK` | [[Estymacja punktowa - zadania#Zad.1]] |
| Frakcja punktowo + błąd | "frakcja", "udział", warunek (np. > 100) | phat = K/n; Dhat = pierwiastek(phat(1-phat)/n) | `LICZ.JEŻELI` | [[Estymacja punktowa - zadania#Zad.3]] |
| E, D2, MSE średniej (populacja znana) | "wartość oczekiwana i wariancja średniej z próby", "błąd średniokwadratowy" | E(xsr) = m; D2 = sigma^2/n; MSE = D2 + b^2 | `PIERWIASTEK` | [[Estymacja punktowa - zadania#Zad.4]] |
| Względny błąd średniej | "względny średni błąd szacunku" | V = (sigma/pierwiastek(n))/m | `PIERWIASTEK` | [[Estymacja punktowa - zadania#Zad.10]] |
| Min. n, estymacja punktowa | "minimalna liczebność", "błąd co najwyżej" | n >= sigma^2/D^2 (lub S2hat/D^2); frakcja: p(1-p)/D^2 (p nieznane: 0,25/D^2) | `ZAOKR.W.GÓRĘ` | [[Estymacja punktowa - zadania#Zad.6]] |
| Przedział średniej, sigma znane | "wiemy, że sigma = ..." | xsr +- u*sigma/pierwiastek(n) | `ROZKŁ.NORMALNY.S.ODWR` | [[Estymacja przedziałowa 1 - rozwiązania#Zad.1]] |
| Przedział średniej, sigma nieznane, n >= 30 | "S^ = ...", duże n | xsr +- u*S/pierwiastek(n) | `ROZKŁ.NORMALNY.S.ODWR` | [[Estymacja przedziałowa 1 - rozwiązania#Zad.4]] |
| Przedział średniej, sigma nieznane, n < 30, rozkład normalny | "S^ = ...", małe n, "rozkład normalny" | xsr +- t*S/pierwiastek(n-1) | `ROZKŁ.T.ODWR.DS` / `ROZKŁ.T.ODWR` | [[Estymacja przedziałowa 1 - rozwiązania#Zad.2]] |
| Przedział frakcji | "udział", "frakcja", "ile z n ..." | phat +- u*pierwiastek(phat(1-phat)/n) | `ROZKŁ.NORMALNY.S.ODWR` | [[Estymacja przedziałowa 1 - rozwiązania#Zad.6]] |
| Przedział frakcji, bez zwracania | "bezzwrotnie", dane N | phat +- u*pierwiastek((N-n)/((N-1)n)*phat(1-phat)) | `ROZKŁ.NORMALNY.S.ODWR` | [[Estymacja przedziałowa 3 - rozwiązania#Zad. 1]] |
| Przedział wariancji | "przedział dla wariancji", rozkład normalny | (n-1)S2hat/c1 ; (n-1)S2hat/c2 | `ROZKŁ.CHI.ODWR` | [[Estymacja przedziałowa 2 - rozwiązania#Zad. 2]] |
| Przedział wariancji, duża próba | n bardzo duże (ok. 100+) | (n-1)S2hat/(n-1 +- z*pierwiastek(2(n-1))) | `ROZKŁ.NORMALNY.S.ODWR` | [[Estymacja przedziałowa 2 - rozwiązania#Zad. 3]] |
| Przedział korelacji, duża próba | "współczynnik korelacji", n >= ok. 100 | R +- z(1-R^2)/pierwiastek(n) | `WSP.KORELACJI` (R z danych) | [[Estymacja przedziałowa 2 - rozwiązania#Zad. 4]] |
| Przedział korelacji, mała próba | "współczynnik korelacji", małe n | Fisher: A = un +- v/pierwiastek(n-3), potem tanh | `LN`, `EXP`, `ROZKŁAD.FISHER.ODW` | [[Estymacja przedziałowa 2 - rozwiązania#Zad. 5]] |
| Wskaźnik precyzji (delta, wdelta) | "wskaźnik precyzji estymacji" | delta = (T2-T1)/2; wdelta = delta/estymator | - | [[Estymacja przedziałowa 1 - rozwiązania]] |
| Min. n dla przedziału średniej | "wskaźnik precyzji nie większy niż", "minimalna liczebność" | sigma znane: sigma^2 u^2/delta0^2; nieznane: Shat^2 t^2/delta0^2 | `ZAOKR.W.GÓRĘ` | [[Estymacja przedziałowa 2 - rozwiązania#Zad. 1]], [[Estymacja przedziałowa 1 - zadania#Zad.8]] |
| Min. n dla przedziału frakcji | to samo, ale frakcja | p(1-p) u^2/delta0^2 | `ZAOKR.W.GÓRĘ` | [[Estymacja przedziałowa 1 - zadania#Zad.9]] |
| Min. n dla frakcji, bez zwracania | "bezzwrotnie", N znane | (1/N + delta0^2(N-1)/(N z^2 phat(1-phat)))^(-1) | `ZAOKR.W.GÓRĘ` | [[Estymacja przedziałowa 3 - rozwiązania#Zad. 2]] |

## Wszystkie wzory według tematów
(skrót; objaśnienia w [[Wzory - estymacja]])

**Miary położenia**
- xsr = (1/n) suma(xi)

**Miary zmienności**
- S2 = (1/n) suma((xi-xsr)^2), S2hat = (1/(n-1)) suma((xi-xsr)^2) = n/(n-1) S2
- S = Shat * pierwiastek((n-1)/n)

**Własności estymatora**
- b = E(Tn) - theta; MSE = D2(Tn) + b^2; RMSE = pierwiastek(MSE)
- D2(xsr) = sigma^2/n; D(xsr) = sigma/pierwiastek(n); Dhat(xsr) = Shat/pierwiastek(n)
- phat = K/n; D2(phat) = p(1-p)/n; Dhat(phat) = pierwiastek(phat(1-phat)/n)
- V = D(xsr)/m

**Przedziały ufności**
- średnia: sigma znane `xsr +- u sigma/pierwiastek(n)`; n >= 30 `xsr +- u S/pierwiastek(n)`; n < 30, normalny `xsr +- t S/pierwiastek(n-1)`
- frakcja: `phat +- u pierwiastek(phat(1-phat)/n)`; bez zwracania z poprawką `(N-n)/((N-1)n)`
- wariancja: `(n-1)S2hat/c1`, `(n-1)S2hat/c2`; duża próba `(n-1)S2hat/(n-1 +- z pierwiastek(2(n-1)))`
- korelacja: duża próba `R +- z(1-R^2)/pierwiastek(n)`; mała próba Fisher `un = 1/2 ln((1+R)/(1-R))`, `A = un +- v/pierwiastek(n-3)`, `T = (e^(2A)-1)/(e^(2A)+1)`
- precyzja: `delta = (T2-T1)/2`, `wdelta = delta/estymator`

**Liczebność próby (zawsze w górę)**
- `n >= sigma^2/D^2` (punktowo), `n >= p(1-p)/D^2`
- `n >= sigma^2 u^2/delta0^2`, `n >= Shat^2 t^2/delta0^2`, `n >= p(1-p) u^2/delta0^2`
- bez zwracania: `n >= (1/N + delta0^2 (N-1)/(N z^2 p(1-p)))^(-1)`

**Regresja, testy** - w tych plikach xlsx nie występują (nie ma zadań), więc nie dopisuję. Regresja (`REGLINP`) i testy dojdą z kolejnych materiałów.

## Schemat decyzyjny: mam takie dane / polecenie, to stosuję to
1. **Co mam oszacować?**
   - średnia -> pkt 2; frakcja/udział -> pkt 3; wariancja -> pkt 4; korelacja -> pkt 5.
2. **Średnia, jedna liczba ("oszacuj", "średni błąd szacunku")** -> xsr, S2hat (n-1), Dhat(xsr) = Shat/pierwiastek(n).
   **Średnia, przedział ("przedział ufności", gamma):**
   - n >= 30, sigma znane -> wzór 1 (u, sigma)
   - n >= 30, sigma nieznane -> wzór 2 (u, S)
   - n < 30 i rozkład normalny, sigma znane -> wzór 1; sigma nieznane -> wzór 3 (t, n-1)
   - n < 30, brak rozkładu normalnego -> nie da się
3. **Frakcja:** phat = K/n, błąd pierwiastek(phat(1-phat)/n); w przedziale dodaj poprawkę (N-n)/((N-1)n), jeśli "bezzwrotnie" i dane N.
4. **Wariancja ("przedział dla wariancji"):** chi2 z n-1 stopniami; c1 większy kwantyl -> dolny koniec; n bardzo duże -> przybliżenie normalne.
5. **Korelacja:** n duże -> R +- z(1-R^2)/pierwiastek(n); n małe -> Fisher.
6. **"Minimalna liczebność":**
   - z estymacji punktowej ("błąd średni co najwyżej") -> n >= sigma^2/D^2 lub p(1-p)/D^2;
   - z przedziału ("wskaźnik precyzji nie większy niż delta0", gamma) -> dodaj kwantyl u/t;
   - sigma znane -> u; sigma nieznane -> Shat i t; p nieznane -> p = 0,5; "bezzwrotnie" -> wzór z N.
7. **"Wskaźnik precyzji"** -> delta = połowa długości przedziału; względny = delta / estymator.
8. **Zawsze na końcu:** zaokrąglij n w górę; sprawdź n kontra n-1; napisz interpretację zdaniem.

## Szablony interpretacji (egzamin)
- Przedział: "Z ufnością gamma przedział (a; b) pokrywa nieznaną [średnią/frakcję/wariancję/korelację] w populacji."
- delta: "Maksymalny błąd oszacowania wynosi delta (w jednostkach), czyli wdelta% oszacowania."
- Dhat: "Szacunek średnio odchyla się od prawdziwej wartości o Dhat."
- Liczebność: "Aby precyzja nie była gorsza niż delta0 przy ufności gamma, trzeba zbadać co najmniej n jednostek."

## Notatki z zadaniami
- [[Estymacja punktowa - zadania]] (`Estymacja_punktowa.xlsx`)
- [[Estymacja przedziałowa 1 - rozwiązania]] / [[Estymacja przedziałowa 1 - zadania]]
- [[Estymacja przedziałowa 2 - rozwiązania]]
- [[Estymacja przedziałowa 3 - rozwiązania]] / [[Estymacja przedziałowa 3 - zadania]]
