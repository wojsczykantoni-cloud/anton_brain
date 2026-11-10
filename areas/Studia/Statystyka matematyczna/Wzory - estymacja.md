---
type: notatka
tags: [statystyka, egzamin, estymacja, wzory]
project: ["[[Statystyka matematyczna]]"]
people: []
created: 2026-11-10
---
# Wzory - estymacja
#statystyka #egzamin

JEDNO miejsce na wzory z zadań z Excela. Notatki z zadań linkują tutaj (np. `[[Wzory - estymacja#Przedział dla średniej]]`). Skrót: [[00 Ściąga - Statystyka]]. Teoria: [[Estymacja punktowa]].

Zapis: `xsr` = średnia z próby, `m` = średnia w populacji, `sigma` = odch. std. w populacji, `S2` = wariancja z próby z dzielnikiem **n**, `S2hat` = wariancja z próby z dzielnikiem **n-1**, `Shat` = pierwiastek z S2hat, `phat` = frakcja z próby, `gamma` = poziom ufności, `delta` = wskaźnik precyzji, `delta0` = dopuszczalny wskaźnik precyzji.

## Średnia i wariancja z próby
- xsr = (1/n) * suma(xi)
- S2 = (1/n) * suma((xi - xsr)^2)   (dzielnik n, obciążona)
- S2hat = (1/(n-1)) * suma((xi - xsr)^2) = n/(n-1) * S2   (nieobciążona)
- S = pierwiastek(S2) = Shat * pierwiastek((n-1)/n)   (tak liczone w arkuszach: `=SQRT(164/165)*5542`)

## Estymacja punktowa
- Błąd estymacji: U = Tn - theta
- Obciążenie: b = E(Tn) - theta
- MSE (błąd średniokwadratowy): E(U^2) = D2(Tn) + b^2;  RMSE = pierwiastek(MSE)
- Wariancja średniej z próby: D2(xsr) = sigma^2 / n;  D(xsr) = sigma / pierwiastek(n)
- Ocena z próby (sigma nieznane): D2hat(xsr) = S2hat / n;  Dhat(xsr) = Shat / pierwiastek(n)
- Frakcja: phat = K / n;  D2(phat) = p(1-p)/n;  Dhat(phat) = pierwiastek(phat(1-phat)/n)
- Względny średni błąd szacunku: V = D(xsr) / m (razy 100% jeśli w %)

## Przedział dla średniej
Trzy wzory (slajd, schemat w [[#Który wzór]]):
1. sigma znane: xsr +- u_gamma * sigma / pierwiastek(n)
2. sigma nieznane, n >= 30: xsr +- u_gamma * S / pierwiastek(n)   (u z N(0,1))
3. sigma nieznane, n < 30, rozkład normalny: xsr +- t_gamma * S / pierwiastek(n-1)   (t z rozkładu t-Studenta, n-1 stopni swobody)

Uwaga: tu S ma dzielnik n. Równoważnie t_gamma * Shat / pierwiastek(n) (Shat z dzielnikiem n-1). Kwantyle: P(|U| < u_gamma) = gamma, czyli u_gamma = kwantyl rzędu (1+gamma)/2.

### Który wzór
- n >= 30, sigma znane -> wzór 1
- n >= 30, sigma nieznane -> wzór 2
- n < 30, rozkład normalny, sigma znane -> wzór 1
- n < 30, rozkład normalny, sigma nieznane -> wzór 3
- n < 30 i rozkład nie jest normalny -> nie da się

## Wskaźnik precyzji
- delta = (1/2) * (T2 - T1) = połowa długości przedziału
- Względny wskaźnik precyzji: wdelta = delta / estymator (np. delta / xsr, delta / phat)

## Przedział dla frakcji
- Duża próba: phat +- u_gamma * pierwiastek(phat(1-phat)/n)
- Losowanie bez zwracania z N: phat +- u_gamma * pierwiastek( (N-n)/((N-1)*n) * phat(1-phat) )   (poprawka na skończoność populacji)

## Przedział dla wariancji
Zakładamy rozkład normalny. U = n*S2/sigma^2 = (n-1)*S2hat/sigma^2 ma rozkład chi-kwadrat o n-1 stopniach swobody.
- T1 = (n-1)*S2hat / c1 = n*S2 / c1
- T2 = (n-1)*S2hat / c2 = n*S2 / c2
- c1 = kwantyl chi2(n-1) rzędu (1+gamma)/2 (większy), c2 = kwantyl rzędu (1-gamma)/2 (mniejszy). Większy kwantyl w mianowniku daje **dolny** koniec.
- Duża próba (przybliżenie normalne): T1* = (n-1)*S2hat / (n-1 + z_gamma*pierwiastek(2(n-1))),  T2* = (n-1)*S2hat / (n-1 - z_gamma*pierwiastek(2(n-1)))

## Przedział dla korelacji
- Duża próba: R +- z_gamma * (1 - R^2) / pierwiastek(n)
- Mała próba (transformacja Fishera): un = (1/2) * ln((1+R)/(1-R)); A1 = un - v_gamma/pierwiastek(n-3); A2 = un + v_gamma/pierwiastek(n-3); T = (e^(2A)-1)/(e^(2A)+1) (czyli tanh(A)), liczymy dla A1 i A2. P(|V| < v_gamma) = gamma.

## Niezbędna liczebność próby
Szukamy najmniejszego CAŁKOWITEGO n (zawsze zaokrąglamy w górę).
- Estymacja punktowa, D(xsr) <= d: n >= sigma^2 / d^2  (arkusz, zad.6). Skrypt z wykładu ma jeszcze "+1", patrz [[Estymacja punktowa - zadania#Pułapki]].
- Estymacja punktowa, frakcja znana: n >= p(1-p) / d^2;  frakcja nieznana: p = 0,5 (najgorszy przypadek) czyli n >= 0,25 / d^2
- Przedział dla średniej, sigma znane: n >= sigma^2 * z_gamma^2 / delta0^2
- Przedział dla średniej, sigma nieznane: n >= Shat^2 * t_gamma^2 / delta0^2 (t ma n-1 stopni swobody z próby pilotażowej)
- Przedział dla frakcji: n >= phat(1-phat) * u_gamma^2 / delta0^2
- Frakcja, bez zwracania z N: n >= ( 1/N + delta0^2 (N-1) / (N * z_gamma^2 * phat(1-phat)) )^(-1)

## Funkcje Excela po polsku
W arkuszach zapisane po angielsku (tak je trzyma plik). Nazwy PL wg [strony Microsoft](https://support.microsoft.com/pl-pl/Excel/statistical-functions-reference). **Do zweryfikowania w swoim Excelu** (Wstaw funkcję -> szukaj fragmentu nazwy). W polskim Excelu separator argumentów to `;`, a ułamki z przecinkiem.

| Co liczymy | Excel w pliku | Excel PL |
|---|---|---|
| średnia | AVERAGE | ŚREDNIA |
| suma | SUM | SUMA |
| wariancja z próby (n-1) | VARA (w zad.1) | WARIANCJA.A (dla liczb to samo co WARIANCJA.PRÓBKI) |
| wariancja z próby (n-1), zalecana | VAR.S | WARIANCJA.PRÓBKI |
| wariancja populacji (n) | VAR.P | WARIANCJA.POP |
| odch. std. z próby (n-1) | STDEV.S | ODCH.STANDARD.PRÓBKI |
| odch. std. populacji (n) | STDEV.P | ODCH.STAND.POPUL |
| pierwiastek | SQRT | PIERWIASTEK |
| zliczanie warunku | COUNTIF | LICZ.JEŻELI |
| zaokrąglenie w górę | ROUNDUP | ZAOKR.W.GÓRĘ |
| u_gamma = kwantyl N(0,1) | NORM.S.INV(p) | ROZKŁ.NORMALNY.S.ODWR(p) |
| t_gamma (jednostronnie, p = (1+gamma)/2) | T.INV(p; n-1) | ROZKŁ.T.ODWR(p; n-1) |
| t_gamma (dwustronnie, p = 1-gamma) | TINV(1-gamma; n-1) | ROZKŁ.T.ODWR.DS(1-gamma; n-1) |
| kwantyl chi-kwadrat | CHISQ.INV(p; n-1) | ROZKŁ.CHI.ODWR(p; n-1) |
| korelacja | CORREL | WSP.KORELACJI |
| transformacja Fishera odwrotna (tanh) | FISHERINV | ROZKŁAD.FISHER.ODW |
| logarytm naturalny / e^x | LN / EXP | LN / EXP |

Uwagi:
- `TINV` (stara funkcja) bierze prawdopodobieństwo **dwustronne** (0,08 dla 92%), `T.INV` bierze **lewostronne** (0,975 dla 95%). Wynik ten sam, argument inny. W arkuszach występują oba (zob. [[Estymacja przedziałowa 1 - rozwiązania]] i [[Estymacja przedziałowa 2 - rozwiązania]]).
- `CHISQ.INV` jest lewostronne: c1 = (0,975), c2 = (0,025).
- REGLINP w tych plikach nie występuje (to regresja, nie estymacja).
