---
type: notatka
tags: [studia, statystyka-matematyczna, rozklady, statystyka-z-proby]
project: ["[[Statystyka matematyczna]]"]
people: []
created: 2026-10-13
---
# Statystyka z próby i rozkłady z wykładu

Notatka z wykładu z [[2026-10-13]]. Hub przedmiotu: [[Statystyka matematyczna]].

**Sedno:** próba to n niezależnych zmiennych o tym samym rozkładzie, statystyka to funkcja próby, a cały wykład pokazuje, jak wyliczyć rozkład takiej statystyki.

Oznaczenia: D2 = wariancja, sigma2 = sigma do kwadratu, xsr = średnia z próby.

## 1. Pojęcia
- **Duże X** to zmienna losowa. **Małe x** to konkretna liczba (realizacja próby).
- **Prosta próba** to X1..Xn, niezależne i o tym samym rozkładzie. Przykład: n-krotne losowanie ze zwracaniem.
- **Statystyka** T(X) to funkcja próby, która **nie zależy od parametru** (theta, czyli np. mu i sigma).
  - Statystyki: xsr, S2, max, min, rozstęp.
  - Nie są statystykami: (xsr - mu)·sqrt(n) oraz (xsr - mu)/sigma. Pytanie "czy to statystyka?" to częsty test.

## 2. Rozkład statystyki z próby dyskretnej (przykład 4, najważniejsza metoda)
Rozkład wyjściowy: P(-2) = 0,25, P(0) = 0,25, P(3) = 0,5. Dla n = 2:
1. Wypisz wszystkie pary (x1, x2), będzie ich 9.
2. Prawdopodobieństwo pary to iloczyn, bo zmienne są niezależne.
3. Policz statystykę dla każdej pary.
4. **Zsumuj prawdopodobieństwa pasujące do tej samej wartości statystyki.**

Wynik dla xsr:

| xsr | -2 | -1 | 0 | 0,5 | 1,5 | 3 |
|---|---|---|---|---|---|---|
| P | 0,0625 | 0,125 | 0,0625 | 0,25 | 0,25 | 0,25 |

- Sprawdzian: suma = 1.
- E(xsr) = 1 = E(X). D2(xsr) = 4,5/2 = 2,25 = D2(X)/n.
- W skrypcie jest literówka: "z przykładu 2" powinno być "z przykładu 3".

## 3. Wzory do zapamiętania
- **Frakcja:** Phat = K/n, K ~ Bin(n, p). E(Phat) = p, D2(Phat) = p(1-p)/n.
- **Próba z N(mu, sigma2):**
  - suma ~ N(n·mu, n·sigma2)
  - xsr ~ N(mu, sigma2/n)
- Średnia ma tę samą wartość oczekiwaną, a wariancję n razy mniejszą. Dlatego w symulacji w R rozkład xsr dla n = 100 jest węższy niż dla n = 10.

## 4. Suma dwóch U(0,1) (przykład 6)
- Z = X1 + X2. Dystrybuanta to **pole części kwadratu 1x1 pod prostą x2 = -x1 + z**.
- F(z) = z^2/2 dla 0 <= z <= 1, oraz F(z) = 1 - (2-z)^2/2 dla 1 < z <= 2.
- Gęstość to pochodna: g(z) = z dla 0 <= z <= 1, oraz g(z) = 2 - z dla 1 < z <= 2. Wykres jest trójkątem.

## 5. Dostateczność (najtrudniejsza koncepcyjnie)
- T jest dostateczna, gdy rozkład próby **przy ustalonym T = t nie zależy od theta**.
- Znaczy to tyle, że T zawiera całą informację o parametrze, jaką niesie próba.
- Dla N(mu, sigma2) statystyką dostateczną dla mu jest xsr. Gęstość próby rozkłada się na g(xsr, mu) · h(z), a h nie zawiera mu. Długi dowód ze slajdów sprowadza się do tego jednego faktu.

## 6. Rozkłady z wykładu i o co w nich chodzi
1. **Zero-jedynkowy (Bernoulliego), przykład 1, urna.** P(X=1) = 0,8 = p, P(X=0) = 0,2. Parametr theta = p, theta należy do [0;1]. Losowanie ze zwracaniem daje próbę zer i jedynek.
2. **Jednostajny dyskretny, przykład 2, kostka czworościenna.** P(X=x) = 0,25 dla x = 1, 2, 3, 4. Służy tylko do pokazania, że próba to niezależne zmienne o takim samym rozkładzie.
3. **Rozkład wypłaty gracza, przykład 3** (na nim są obliczenia): x = -2, 0, 3 z prawdopodobieństwami 0,25; 0,25; 0,5. E(X) = -0,5 + 0 + 1,5 = 1. D2(X) = E(X^2) - 1 = 5,5 - 1 = 4,5.
4. **Rozkład xsr z próby dwuelementowej, przykład 4:** tabela w punkcie 2. E(xsr) = 1, D2(xsr) = 2,25. Metoda: 9 par, iloczyn prawdopodobieństw, sumowanie par o tej samej średniej.
5. **Dwumianowy Bin(n, p), przykład 5, liczba sukcesów.** K = suma Xi, P(K=k) = C(n,k) · p^k · (1-p)^(n-k). Frakcja Phat = K/n ma E(Phat) = p i D2(Phat) = p(1-p)/n.
6. **Jednostajny ciągły U(0;1), przykład 6.** Gęstość f(x) = 1 na [0;1]. Suma dwóch takich zmiennych ma rozkład **trójkątny** (punkt 4).
7. **Normalny N(mu; sigma2), przykłady 7 i 9.** Suma Xi ~ N(n·mu; n·sigma2), xsr ~ N(mu; sigma2/n). Używany też do dowodu dostateczności: xsr jest statystyką dostateczną dla mu.

## Na egzamin najpewniej
- policz rozkład statystyki dla n = 2 (metoda z punktu 2),
- rozstrzygnij, czy coś jest statystyką,
- zastosuj wzory z punktu 3.

## Do zrobienia
- [ ] Zadanie 1 ze skryptu: ten sam schemat co w punkcie 2, dla rozstępu, wariancji i maksimum (po jednej statystyce).
