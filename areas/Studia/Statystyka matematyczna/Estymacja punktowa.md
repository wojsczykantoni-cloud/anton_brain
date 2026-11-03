---
type: notatka
tags: [studia, statystyka-matematyczna, estymacja-punktowa]
project: ["[[Statystyka matematyczna]]"]
people: []
created: 2026-11-03
---
# Estymacja punktowa
Część [[Statystyka matematyczna]]. Źródło: Wywiał, rozdz. 3 (estymacja punktowa). Poprzedni wykład: [[Statystyka z próby i rozkłady z wykładu]].
Zapis: xsr = średnia z próby, hat = ocena z próby (np. phat, S2hat), sigma2 = sigma do kwadratu.

## Oznaczenia (nazwy składników wzorów)
| Symbol | Nazwa |
|---|---|
| theta | szacowany parametr rozkładu |
| Theta | zbiór możliwych wartości parametru theta |
| Tn | estymator (statystyka z próby n-elementowej użyta do oceny theta) |
| U | błąd estymacji |
| b | obciążenie estymatora (błąd systematyczny) |
| E(.) | wartość oczekiwana (nadzieja matematyczna) |
| D2(.) | wariancja (miara precyzji) |
| D(.) | błąd średni szacunku (odchylenie standardowe estymatora) |
| V(.) | względny błąd średni szacunku, w % |
| n, N | liczebność próby, liczebność populacji |
| Xi | i-ta obserwacja z próby (zmienna losowa) |
| xi | wartość cechy i-tego elementu populacji |
| xsr | średnia z próby |
| m | średnia (wartość oczekiwana) w populacji |
| sigma2, sigma | wariancja, odchylenie standardowe w populacji |
| S2 | wariancja z próby z dzieleniem przez n (obciążona) |
| S2hat | wariancja z próby z dzieleniem przez n-1 (nieobciążona) |
| Shat | odchylenie standardowe z próby, pierwiastek z S2hat |
| Dhat | ocena błędu średniego obliczona z próby |
| d | postulowana precyzja (dopuszczalny błąd bezwzględny) |
| delta | postulowany względny błąd średni, w % |
| p | frakcja (odsetek) elementów z cechą w populacji |
| phat | frakcja z próby |
| K | liczba elementów z cechą w próbie |
| g, ghat | wartość globalna (suma cechy w populacji), jej estymator |
| eta4 | czwarty moment centralny E(X - E(X))^4 |
| rho | współczynnik korelacji w populacji |
| Rxy, rxy | współczynnik korelacji z próby (estymator, jego wartość) |
| Cxy | kowariancja z próby |
| Sx, Sy | odchylenia standardowe z próby dla X i Y |
| Me | mediana z próby |
| e | wskaźnik efektywności |
| [a] | część całkowita liczby a |

## 1. Podstawy
| Wzór | Nazwa i sens |
|---|---|
| U = Tn - theta | błąd estymacji |
| b = E(U) = E(Tn) - theta | obciążenie; b = 0 to brak obciążenia |
| E(U^2) = D2(Tn) + b^2 | błąd średniokwadratowy = wariancja + obciążenie do kwadratu |
| E(U^2) = suma po t z (t - theta)^2 * P(Tn = t) | błąd średniokwadratowy, estymator skokowy |
| E(U^2) = całka od -inf do +inf z (t - theta)^2 * f(t) dt | błąd średniokwadratowy, estymator ciągły (f(t) to gęstość estymatora) |
| D2(Tn) = E[Tn - E(Tn)]^2 | wariancja estymatora, wskaźnik precyzji |
| sqrt(E(U^2)) | błąd średni szacunku: o ile średnio estymator odchyla się od theta |

- **Def. 3.1 (lepszy):** T1n jest lepszy od T2n, gdy D2(T1n) <= D2(T2n) dla każdego theta i ostro dla co najmniej jednego theta.
- **Def. 3.2 (dopuszczalny):** Tn jest dopuszczalny w klasie K, gdy nie istnieje od niego lepszy estymator.

## 2. Własności estymatora
| Własność | Warunek | Sens |
|---|---|---|
| nieobciążony | E(Tn) = theta | brak błędu systematycznego |
| asymptotycznie nieobciążony | lim (n -> inf) E(Tn) = theta | obciążenie znika przy dużym n |
| zgodny | lim (n -> inf) P{abs(Tn - theta) < eps} = 1 dla każdego eps > 0 | im większe n, tym pewniej błąd jest mniejszy od eps; to słabe prawo wielkich liczb; opłaca się zwiększać n |
| efektywny | D2(T*) <= D2(Tn) dla każdego Tn z K, gdzie K to zbiór estymatorów nieobciążonych | najmniejsza wariancja wśród nieobciążonych |

- **Tw. 3.1 (wystarczy do zgodności):** asymptotycznie nieobciążony i lim (n -> inf) D2(Tn) = 0, to Tn jest zgodny.
- Wskaźnik efektywności: e(Tn) = D2(T*) / D2(Tn), przy czym 0 <= e <= 1.
- Względna efektywność: e(T1n, T2n) = D2(T2n) / D2(T1n) = e(T1n) / e(T2n).

## 3. Średnia
| Wzór | Nazwa |
|---|---|
| m = (1/N) * suma (i=1..N) xi | średnia w populacji (cel estymacji) |
| xsr = (1/n) * suma (i=1..n) Xi | estymator m; E(xsr) = m (nieobciążony) |
| sigma2 = (1/N) * suma (xi - m)^2 | wariancja w populacji |
| D2(xsr) = sigma2 / n | wariancja średniej (losowanie ze zwracaniem) |
| D(xsr) = sigma / sqrt(n) | błąd średni szacunku |
| V(xsr) = D(xsr) / m * 100% = sigma / (m * sqrt(n)) * 100% | względny błąd średni |
| S2hat = (1/(n-1)) * suma (Xi - xsr)^2 | nieobciążona ocena wariancji |
| Dhat(xsr) = Shat / sqrt(n), czyli D2hat(xsr) = S2hat / n | ocena błędu średniego z próby |

**Niezbędna liczebność próby:**
| Cel | Wzór |
|---|---|
| precyzja d | n >= [(sigma / d)^2] + 1, a z próby [(Shat / d)^2] + 1 (z nierówności D(xsr) <= d) |
| względny błąd delta (%) | n >= [10000 * S2hat / (xsr^2 * delta^2)] + 1 (z nierówności V(xsr) <= delta) |

**Losowanie bez zwracania z populacji N:** E(xsr) = m, ale D2(xsr) = (N - n)/N * sigma_gwiazdka2 / n, gdzie sigma_gwiazdka2 = N/(N-1) * sigma2. Czyli D2(xsr) = (N - n)/(N - 1) * sigma2 / n.

**Przykład 1:** n = 64, xsr = 80, S2hat = 1600, Dhat = 40/8 = 5. Chcemy d = 2: n >= [(40/2)^2] + 1 = 401, czyli dobrać jeszcze 337 osób.

### Mediana a średnia
- Mediana z próby: Me = X na pozycji [n/2] + 1 (po uporządkowaniu). Dla rozkładu symetrycznego E(X) = mediana (kwantyl rzędu 0,5).
- Rozkład normalny N(m, sigma2): D2(Me) = pi/2 * sigma2/n.
- e = D2(xsr) / D2(Me) = 2/pi < 1, więc **średnia jest lepsza od mediany**.
- Wg skryptu E(Me) = m + A/n (A to stała), czyli mediana jest granicznie nieobciążona.

### Przykład 3 (populacja skończona, próba 2 bez zwracania)
Populacja: y = 0, 1, 1, 2, 3 (N = 5). m = 1,4; sigma2 = 1,04; sigma_gwiazdka2 = 5/4 * 1,04 = 1,3. Liczba prób: 10.

| xsr | 0,5 | 1,0 | 1,5 | 2,0 | 2,5 |
|---|---|---|---|---|---|
| P | 0,2 | 0,2 | 0,3 | 0,2 | 0,1 |

E(xsr) = 1,4 = m; D2(xsr) = 0,39 (= 3/5 * 1,3/2); D(xsr) = 0,6245; V = 0,6245/1,4*100% = 44,6%.

## 4. Frakcja
| Wzór | Nazwa |
|---|---|
| phat = K/n = (1/n) * suma Xi | frakcja z próby; Xi zero-jedynkowe: P(Xi=1) = p, P(Xi=0) = 1 - p |
| E(phat) = p | nieobciążony |
| D2(phat) = p(1-p)/n | wariancja; <= 1/(4n), maksimum dla p = 0,5 |
| D(phat) <= 1/(2*sqrt(n)) | błąd średni; dla n = 1000 jest <= 0,0158 |
| D2hat(phat) = phat(1-phat)/n | ocena wariancji |
| Dhat(phat) = sqrt(phat(1-phat)/n) | ocena błędu średniego |
| V(phat) = D(phat)/p * 100% | względny błąd średni |

**Niezbędna liczebność próby:**
| Sytuacja | Wzór |
|---|---|
| p nieznane, błąd d | n >= [1/(4*d^2)] + 1 |
| phat znane, błąd d | n >= [phat(1-phat)/d^2] + 1 |
| phat znane, względny błąd delta (%) | n >= [10000 * (1-phat) / (delta^2 * phat)] + 1 |

**Przykład 5:** p około 0,5, d = 0,02: n >= [1/(4*0,0004)] + 1 = 626.

## 5. Wartość globalna
| Wzór | Nazwa |
|---|---|
| g = N * m = E(suma Yi po populacji) | wartość globalna |
| ghat = N * xsr = (N/n) * suma Yi | estymator; E(ghat) = N*m, nieobciążony i zgodny |
| D(ghat) = N * sigma / sqrt(n) = N * D(xsr) | błąd średni |
| V(ghat) = V(xsr) | względny błąd średni jest taki sam jak dla średniej |
| g = N*p, ghat = N * phat = N*K/n, D(ghat) = N * sqrt(p(1-p)/n) | gdy Y zero-jedynkowa (liczba elementów z cechą) |

**Przykład 6:** N = 5000, n = 81, xsr = 93, S2hat = 2500 (Shat = 50): ghat = 5000*93 = 465 000; Dhat(ghat) = 5000*50/9 = 27 777,78.

## 6. Wariancja
| Wzór | Nazwa |
|---|---|
| S2 = (1/n) * suma (Xi - xsr)^2 | wariancja z próby, **obciążona**: E(S2) = (n-1)/n * sigma2 < sigma2 |
| S2hat = (1/(n-1)) * suma (Xi - xsr)^2 | **nieobciążona**: E(S2hat) = sigma2 |
| S2hat = n/(n-1) * S2 | związek obu |
| D2(S2) = (eta4 - sigma4)/n + O(n^-2), analogicznie D2(S2hat) | wariancja estymatorów; O(n^-2) to wielkość malejąca do zera jak c/n^2 |
| eta4 = E(X - E(X))^4 | czwarty moment centralny |

## 7. Korelacja
| Wzór | Nazwa |
|---|---|
| rho = Cov(X,Y) / (D(X) * D(Y)), rho w przedziale [-1; 1] | współczynnik korelacji w populacji |
| Cov(X,Y) = E[(X - E(X)) * (Y - E(Y))] | kowariancja; D2(X) = Cov(X,X) |
| skokowe: suma po i,j z (xi - E(X))(yj - E(Y)) * P(X=xi, Y=yj) | kowariancja, zmienne skokowe |
| ciągłe: całka podwójna z (x - E(X))(y - E(Y)) * f(x,y) dx dy | kowariancja, zmienne ciągłe |
| Rxy = Cxy / (Sx * Sy) | współczynnik korelacji z próby |
| Cxy = (1/n) * suma (xi - xsr)(yi - ysr) | kowariancja z próby |
| Sx = sqrt(Cxx), Sy = sqrt(Cyy) | odchylenia standardowe z próby |
| E(Rxy) = rho + O(1/n), D2(Rxy) = (1 - rho^2)^2 / n + O(n^(-3/2)) | dla rozkładu dwuwymiarowego normalnego; Rxy jest graniczne nieobciążony i zgodny (Cramer 1958) |
| Dhat(Rxy) = (1 - rxy^2) / sqrt(n) | ocena błędu średniego |
| Vhat(Rxy) = Dhat(Rxy) / abs(rxy) * 100% | względny błąd |

**Przykład 7:** n = 400, rxy = 0,3: Dhat = 0,91/20 = 0,0455; Vhat = 0,0455/0,3 * 100% = 15,2%.

## 8. Zadania ze skryptu: wyniki
1. Wykazać E(xsr) = m: z liniowości wartości oczekiwanej, E(xsr) = (1/n) * n * m = m.
2. Zgodność xsr: Tw. 3.1 (E(xsr) = m, D2(xsr) = sigma2/n dąży do 0) lub nierówność Czebyszewa.
3. 29 = 25 + b^2, więc b^2 = 4, **b = 2 lub -2**.
4. phat = 64/121, ghat = 4000 * 64/121 = **2116** studentów.
5. p = 0,12, d = 0,01: [0,12*0,88/0,0001] + 1 = **1057**.
6a. d = 50: [(1232/50)^2] + 1 = 607 + 1 = **608**.
6b. delta = 5%: [10000 * 1232^2 / (3898^2 * 25)] + 1 = 39 + 1 = **40**.
7. p nieznane, d = 0,02: **626**.
8. E(S2) = (n-1)/n * sigma2, które dąży do sigma2 przy n dążącym do nieskończoności.

## 9. Błędy w skrypcie (sprawdź z prowadzącym)
- **Przykład 2:** skrypt podaje n = 2000. Ze wzoru: [10000 * 1600 / (6400 * 100)] + 1 = 26. Podane tam 50% to s/xsr (współczynnik zmienności), a nie względny błąd średni dla n = 64 (ten wynosi 6,25%).
- **Przykład 1:** skrypt podaje 400 i "336 dobrać"; ze wzoru z +1 wychodzi 401 i 337.
- **Przykład 5 (względny błąd 2%):** skrypt podaje 1251; ze wzoru wychodzi [10000 * 0,5 / (4 * 0,5)] + 1 = 2501.
- **Przykład 6:** skrypt podaje V(ghat) = 53,8%, czyli s/xsr bez dzielenia przez sqrt(n). Z wzoru: 27 777,78 / 465 000 * 100% = 5,97%.
- **Korelacja:** rho należy do [-1; 1], a nie do [0; 1] jak w skrypcie.

## Na egzamin
- Rozpoznaj pojęcie: obciążenie, błąd średniokwadratowy, zgodność (Tw. 3.1), efektywność.
- Dobór n: wybierz wzór wg danych (średnia czy frakcja, błąd bezwzględny d czy względny delta, p znane czy nie). Zawsze zaokrąglaj w górę: część całkowita + 1.
- S2hat (z n-1) jest nieobciążona, S2 (z n) obciążona.
- Średnia jest lepsza od mediany dla rozkładu normalnego (e = 2/pi).
