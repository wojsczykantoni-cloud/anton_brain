---
type: notatka
tags: [statystyka, egzamin, estymacja-przedzialowa, zadania]
project: ["[[Statystyka matematyczna]]"]
people: []
created: 2026-11-10
---
# Estymacja przedziałowa 3 - zadania
#statystyka #egzamin

Plik źródłowy: `Estymacja_przedzia_owa_3.xlsx` (arkusze Zad. 1, Zad. 2). To wersja robocza tych samych zadań co w [[Estymacja przedziałowa 3 - rozwiązania]]. Różnice: w Zad.1 jest dodatkowa kolumna **"bezkorekt"** (przedział bez poprawki na skończoność populacji), a Zad.2 ma **tylko treść** (bez obliczeń; rozwiązanie jest w pliku z rozwiązaniami: $n=333$). Wzory: [[Wzory - estymacja]]. Skrót: [[00 Ściąga - Statystyka]].

> [!info] O co chodzi
> Zad.1: przedział dla frakcji, $N=500$, $n=100$ (bezzwrotnie), $k=40$, $\gamma=0{,}95$. Zad.2: minimalne $n$ dla $N=1000$, $\Delta_0=0{,}05$, $\gamma=0{,}99$, $\hat p=0{,}25$ (bezzwrotnie). Dane i opis jak w [[Estymacja przedziałowa 3 - rozwiązania]].

## Ze slajdów wklejonych w arkusze
Te same dwa wzory co w [[Estymacja przedziałowa 3 - rozwiązania#Ze slajdów wklejonych w arkusze]]: przedział dla frakcji z poprawką $\frac{N-n}{(N-1)n}$ (Zad.1, slajd) i wzór na minimalne $n$ z $\frac1N$ (Zad.2, slajd).

## Rozwiązanie krok po kroku

### Zad.1
*Porównanie przedziału z poprawką i bez poprawki.*

1. $\hat p=\dfrac{40}{100}=0{,}4$; $z_\gamma=1{,}9600$.
2. **Z poprawką** (bezzwrotnie): błąd graniczny $1{,}96\sqrt{\dfrac{400}{499\cdot100}\cdot0{,}24}=0{,}0860$, przedział $(0{,}3140;\ 0{,}4860)$.
3. **Bez poprawki** (kolumna "bezkorekt"): błąd graniczny $1{,}96\sqrt{\dfrac{0{,}4\cdot0{,}6}{100}}=1{,}96\cdot0{,}04899=0{,}0960$, przedział $(0{,}3040;\ 0{,}4960)$.
4. Porównanie długości: z poprawką $0{,}172$, bez $0{,}192$, więc poprawka skraca przedział, bo losujemy bez zwracania 20% populacji.
5. Względna precyzja: z poprawką $\delta=\dfrac{0{,}0860}{0{,}4}=0{,}2149$; bez poprawki $\delta=\dfrac{0{,}0960}{0{,}4}=0{,}2400$ (policzone przeze mnie, w arkuszu nie ma).

### Zad.2
Tylko treść w arkuszu. Wynik $n=333$ i obliczenia: [[Estymacja przedziałowa 3 - rozwiązania#Zad. 2]].

## Wzory
Legenda: [[Wzory - estymacja#Przedział dla frakcji]].

| Wariant | Ogólny wzór | Z liczbami | Excel |
|---|---|---|---|
| z poprawką | $\hat p\pm z_\gamma\sqrt{\frac{N-n}{(N-1)n}\hat p(1-\hat p)}$ | $0{,}4\pm1{,}96\sqrt{\frac{400}{499\cdot100}\cdot0{,}24}=0{,}4\pm0{,}0860$ | `=B9-E5*PIERWIASTEK((B8-B6)/((B8-1)*B6)*(B9*(1-B9)))` |
| bez poprawki | $\hat p\pm z_\gamma\sqrt{\frac{\hat p(1-\hat p)}{n}}$ | $0{,}4\pm1{,}96\sqrt{\frac{0{,}24}{100}}=0{,}4\pm0{,}0960$ | `=B9-E5*PIERWIASTEK(B9*(1-B9)/B6)` (kolumna G) |
| $\hat p$, $z_\gamma$ | $\hat p=\frac{k}{n}$ | $\frac{40}{100}=0{,}4$ | `=B7/B6`; `=ROZKŁ.NORMALNY.S.ODWR(0,975)` |

## Dlaczego tak
Kolumna "bezkorekt" pokazuje, ile daje poprawka na skończoność populacji: przy losowaniu bez zwracania i dużym udziale próby w populacji ($n/N=20\%$) przedział ma być węższy. Słowa-klucze w treści: "bezzwrotnie", "bez zwracania".

## Interpretacja
"Uwzględnienie, że próba to 20% populacji, skraca przedział ufności z (0,304; 0,496) do (0,314; 0,486), czyli zwiększa precyzję oszacowania udziału zadowolonych pracowników."

## Pułapki
- Literówka w arkuszu: "gammna" w A5. "bezkorekt" i "bezzwrotna" to tylko notatki autora.
- Nie mylić wariantów: z poprawką (bezzwrotnie z $N$) kontra bez poprawki (ze zwracaniem lub $N$ bardzo duże).
- Zad.2 nie ma obliczeń w tym pliku; wynik bierz z notatki z rozwiązaniami.
