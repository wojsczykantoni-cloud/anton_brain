---
type: notatka
tags: [statystyka, egzamin, estymacja-przedzialowa, zadania]
project: ["[[Statystyka matematyczna]]"]
people: []
created: 2026-11-10
---
# Estymacja przedziałowa 3 - rozwiązania
#statystyka #egzamin

Plik źródłowy: `Estymacja_przedzia_owa_3___rozw.xlsx` (arkusze Zad. 1, Zad. 2). Wersja robocza z porównaniem "bez korekty": [[Estymacja przedziałowa 3 - zadania]]. Wzory: [[Wzory - estymacja]]. Skrót: [[00 Ściąga - Statystyka]].

> [!info] O co chodzi w tych zadaniach
> Frakcja przy **losowaniu bezzwrotnym** z populacji skończonej ($N$ znane): przedział ufności (zad.1) i minimalna liczebność próby (zad.2), z **poprawką na skończoność populacji**.

| Zad. | Dane | Szukamy |
|---|---|---|
| 1 | $N=500$, $n=100$ (bezzwrotnie), $k=40$ zadowolonych, $\gamma=0{,}95$ | przedział dla frakcji, $\Delta$, $\delta$ |
| 2 | $N=1000$, $\Delta_0=0{,}05$, $\gamma=0{,}99$, $\hat p=0{,}25$, bezzwrotnie | minimalne $n$ |

## Ze slajdów wklejonych w arkusze
**Zad.1 - przedział ufności:** $P\{P_{1n}<p<P_{2n}\mid p\}=\gamma$, gdzie
$$P_{1n}=\hat P-z_\gamma\sqrt{\frac{N-n}{(N-1)\,n}\,\hat P(1-\hat P)}\qquad P_{2n}=\hat P+z_\gamma\sqrt{\frac{N-n}{(N-1)\,n}\,\hat P(1-\hat P)}$$
przy czym $P(|Z|<z_\gamma)=\gamma$, $Z\sim N(0;1)$.

**Zad.2 - minimalna liczebność:**
$$n\ge\left(\frac{1}{N}+\frac{\Delta_0^2\,(N-1)}{N\,z_\gamma^2\,\hat p(1-\hat p)}\right)^{-1}$$

## Rozwiązanie krok po kroku

### Zad. 1
*Dział kadr: N = 500 pracowników, bezzwrotnie próba n = 100, 40 zadowolonych z systemu premiowego. Przedział dla udziału zadowolonych, 95%.*

1. Frakcja: $\hat p=\dfrac{k}{n}=\dfrac{40}{100}=0{,}4$.
2. Kwantyl: $\gamma=0{,}95$, rząd $0{,}975$, $z_\gamma=1{,}9600$.
3. Poprawka: $\dfrac{N-n}{(N-1)\,n}=\dfrac{400}{499\cdot100}=0{,}008016$.
4. Pod pierwiastkiem: $0{,}008016\cdot0{,}4\cdot0{,}6=0{,}001924$, pierwiastek $=0{,}04386$.
5. Błąd graniczny: $1{,}9600\cdot0{,}04386=0{,}08597$.
6. Przedział: $P_{1n}=0{,}4-0{,}08597=0{,}3140$; $P_{2n}=0{,}4+0{,}08597=0{,}4860$, czyli $(0{,}3140;\ 0{,}4860)$.
7. Precyzja: $\Delta=\dfrac{0{,}4860-0{,}3140}{2}=0{,}0860$.
8. Względna: $\delta=\dfrac{0{,}0860}{0{,}4}=0{,}2149$ (21,5%).

### Zad. 2
*Deweloper: N = 1000 gospodarstw, wskaźnik precyzji co najwyżej 0,05, ufność 99%, wstępnie phat = 0,25, losowanie bezzwrotne. Minimalne n.*

1. Kwantyl: $\gamma=0{,}99$, rząd $0{,}995$, $z_\gamma=2{,}5758$, $z_\gamma^2=6{,}6349$.
2. $\dfrac{1}{N}=\dfrac{1}{1000}=0{,}001$.
3. $\dfrac{\Delta_0^2(N-1)}{N\,z_\gamma^2\,\hat p(1-\hat p)}=\dfrac{0{,}0025\cdot999}{1000\cdot6{,}6349\cdot0{,}1875}=\dfrac{2{,}4975}{1244{,}04}=0{,}0020076$.
4. Suma w nawiasie: $0{,}001+0{,}0020076=0{,}0030076$.
5. $n\ge\dfrac{1}{0{,}0030076}=332{,}49$.
6. Zaokrąglenie w górę: $n=333$.

## Wzory
Legenda: [[Wzory - estymacja#Przedział dla frakcji]], [[Wzory - estymacja#Niezbędna liczebność próby]], [[Wzory - estymacja#Wskaźnik precyzji]].

| Co | Ogólny wzór | Z liczbami | Excel |
|---|---|---|---|
| przedział (zad.1) | $\hat p\pm z_\gamma\sqrt{\frac{N-n}{(N-1)n}\hat p(1-\hat p)}$ | $0{,}4\pm1{,}96\sqrt{\frac{400}{499\cdot100}\cdot0{,}24}=0{,}4\pm0{,}0860$ | `=B7/B6`; `z: =ROZKŁ.NORMALNY.S.ODWR(0,975)`; `=B8-B10*PIERWIASTEK((B5-B6)/((B5-1)*B6)*B8*(1-B8))` i `+` |
| precyzja (zad.1) | $\Delta=\frac{P_{2n}-P_{1n}}{2}$, $\delta=\frac{\Delta}{\hat p}$ | $\frac{0{,}4860-0{,}3140}{2}=0{,}0860$; $\frac{0{,}0860}{0{,}4}=0{,}2149$ | `=(B12-B11)/2`; `=B15/B8` |
| min. $n$ (zad.2) | $n\ge\left(\frac1N+\frac{\Delta_0^2(N-1)}{Nz_\gamma^2\hat p(1-\hat p)}\right)^{-1}$ | $\left(0{,}001+\frac{0{,}0025\cdot999}{1000\cdot6{,}6349\cdot0{,}1875}\right)^{-1}=332{,}49\to333$ | `=(1/B9+B11^2*(B9-1)/(B9*B13^2*B12*(1-B12)))^(-1)`; `=ZAOKR.W.GÓRĘ(B14;0)`; `z: =ROZKŁ.NORMALNY.S.ODWR(0,995)` |

## Dlaczego tak
- **Poprawka $\frac{N-n}{N-1}$:** gdy losujemy bez zwracania z małej populacji, próba niesie więcej informacji niż przy losowaniu ze zwracaniem, więc wariancja estymatora jest mniejsza, a przedział węższy. Słowa-klucze: "bezzwrotnie", "bez zwracania", podane $N$.
- **Zad.1:** odsetek zadowolonych to frakcja, więc wzór dla frakcji (z poprawką). Słowa-klucze: "odsetek", "udział".
- **Zad.2:** z warunku $\Delta\le\Delta_0$ wyznaczamy $n$; w wersji bezzwrotnej wychodzi wzór z $\frac1N$. Słowa-klucze: "minimalna liczebność próby", "przy losowaniu bezzwrotnym", "wskaźnik precyzji nie przekraczał".
- **$\hat p=0{,}25$ w zad.2:** w treści "wstępne badania sugerują", więc używamy tej wartości, a nie $0{,}5$.

## Interpretacja
- **Zad.1:** "Z ufnością 95% odsetek zadowolonych ze systemu premiowego wśród wszystkich 500 pracowników mieści się w przedziale (31,4%; 48,6%). Precyzja to 8,6 p.p., czyli 21,5% oszacowania."
- **Zad.2:** "Aby wskaźnik precyzji nie przekroczył 5 p.p. przy ufności 99%, trzeba zbadać co najmniej 333 gospodarstwa z 1000."

## Pułapki
- **Zaokrąglenie:** 332,49 -> 333 (w górę, nie 332).
- **Zad.1: nie pomijaj poprawki.** Bez niej $\Delta=0{,}0960$ (przedział $0{,}304$ - $0{,}496$), czyli o ok. 12% szerszy. Zobacz [[Estymacja przedziałowa 3 - zadania]]. Poprawka ma znaczenie, gdy $n/N$ jest duże (tu 20%); przy $n/N<5\%$ można ją pominąć.
- **$N-1$ w mianowniku**, nie $N$: $\frac{N-n}{(N-1)n}$, a nie $\frac{N-n}{Nn}$.
- **Zad.2 daje mniejsze $n$ niż wersja bez poprawki:** bez niej $n\ge\frac{0{,}1875\cdot6{,}6349}{0{,}0025}=497{,}6\to498$; z poprawką 333. Sprawdź, czy w treści jest "bezzwrotnie".
- **Wzór w zad.2 jest "do potęgi $-1$"** (cała suma w nawiasie), w Excelu `^(-1)`.
- **Kwantyl:** $z_\gamma$ to rząd $\frac{1+\gamma}{2}$ (0,975 dla 95%, 0,995 dla 99%).
