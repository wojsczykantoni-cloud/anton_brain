---
type: notatka
tags: [statystyka, egzamin, estymacja-przedzialowa, zadania]
project: ["[[Statystyka matematyczna]]"]
people: []
created: 2026-11-10
---
# Estymacja przedziałowa 1 - rozwiązania
#statystyka #egzamin

Plik źródłowy: `Estymacja_przedzia_owa_1_-_rozw.xlsx` (arkusze Zad.1, Zad.2, Zad. 4, Zad. 6). Pełny zestaw 9 zadań (bez rozwiązań w pliku): [[Estymacja przedziałowa 1 - zadania]]. Wzory: [[Wzory - estymacja]]. Skrót: [[00 Ściąga - Statystyka]].

> [!info] O co chodzi w tych zadaniach
> Przedział ufności dla **średniej** (zad.1, 2, 4) i dla **frakcji** (zad.6), plus wskaźnik precyzji $\Delta$ (połowa długości przedziału) i względny wskaźnik precyzji $\delta=\Delta/\text{estymator}$. Polecenie w każdym zadaniu kończy się: "Wyznacz wskaźnik precyzji estymacji oraz względny wskaźnik precyzji estymacji".

| Zad. | Dane | Wzór |
|---|---|---|
| 1 | dyskonto: $\text{xsr}=20\%$, $\sigma=8\%$ (znane), $n=36$, $\gamma=0{,}95$, rozkład normalny | 1 |
| 2 | stopa zwrotu: $n=15$, $\text{xsr}=10{,}37\%$, $\hat S=3{,}5\%$, $\gamma=0{,}92$, rozkład normalny | 3 |
| 4 | odszkodowania: $n=165$, $\text{xsr}=16\,530$, $\hat S=5542$, $\gamma=0{,}95$ i $0{,}99$ | 2 |
| 6 | 34 z 100 konsumentów kupuje produkt zagraniczny, $\gamma=0{,}95$ | frakcja |

## Ze slajdów wklejonych w arkusze
- **Wskaźnik precyzji** estymacji przedziałowej to połowa rozpiętości przedziału ufności: $\Delta=\dfrac{1}{2}(T_2-T_1)$.
- **Trzy wzory na przedział dla $m=E(X)$** oraz schemat wyboru ($n\ge30$? $\sigma$ znane? $X\sim N$?) są opisane w [[Wzory - estymacja#Przedział dla średniej]] i [[Wzory - estymacja#Który wzór]]. Slajd definiuje też liczby: dla $U\sim N(0;1)$ jest $P(-u_\gamma<U<u_\gamma)=\gamma$, a dla $T\sim t_{n-1}$ jest $P(-t_\gamma<T<t_\gamma)=\gamma$.
- **Wariancje:** $S^2=\dfrac{1}{n}\sum(X_i-\text{Xsr})^2$ oraz $\hat S^2=\dfrac{1}{n-1}\sum(X_i-\text{Xsr})^2=\dfrac{n}{n-1}S^2$. Wzory 2 i 3 używają $S$ (dzielnik $n$), a w treści zadań podane "S^" to $\hat S$ (dzielnik $n-1$). Stąd przeliczenie $S=\hat S\sqrt{(n-1)/n}$.
- **Frakcja (zad.6):** $P\left\{\hat P-u_\gamma\sqrt{\dfrac{\hat P(1-\hat P)}{n}}\le p\le\hat P+u_\gamma\sqrt{\dfrac{\hat P(1-\hat P)}{n}}\right\}=\gamma$, gdzie $P(|U_n|\le u_\gamma)=\gamma$, $U_n\sim N(0;1)$.

## Rozwiązanie krok po kroku

### Zad.1
*Fundusze "small fry": średnie dyskonto 20%, sigma = 8%, n = 36. Przedział dla średniej wartości dyskonta.*

1. Wybór wzoru: $\sigma$ znane, $n=36\ge30$, więc **wzór 1**.
2. Kwantyl: $\gamma=0{,}95$, rząd $0{,}975$, więc $u_\gamma=1{,}9600$.
3. Błąd: $u_\gamma\dfrac{\sigma}{\sqrt n}=1{,}9600\cdot\dfrac{8}{6}=2{,}6133$.
4. Przedział: $20-2{,}6133=17{,}3867$ oraz $20+2{,}6133=22{,}6133$, czyli $(17{,}39\%;\ 22{,}61\%)$.
5. Precyzja: $\Delta=\dfrac{22{,}6133-17{,}3867}{2}=2{,}6133$ p.p.
6. Względna: $\delta=\dfrac{2{,}6133}{20}=0{,}1307$ (13,07%).

### Zad.2
*Stopa zwrotu akcji: n = 15, xsr = 10,37%, S^ = 3,5%, 92%.*

1. Wybór wzoru: $n=15<30$, rozkład normalny, $\sigma$ nieznane, więc **wzór 3** ($t$-Studenta, $n-1=14$ stopni swobody).
2. Odchylenie z dzielnikiem $n$: $S=\hat S\sqrt{\dfrac{14}{15}}=3{,}5\cdot0{,}9661=3{,}3813$.
3. Kwantyl: $\gamma=0{,}92$, więc dwustronne $1-\gamma=0{,}08$, $t_\gamma=1{,}8875$ (to samo co kwantyl rzędu 0,96).
4. Błąd: $t_\gamma\dfrac{S}{\sqrt{n-1}}=1{,}8875\cdot\dfrac{3{,}3813}{\sqrt{14}}=1{,}7057$.
5. Przedział: $10{,}37-1{,}7057=8{,}6643$ oraz $10{,}37+1{,}7057=12{,}0757$, czyli $(8{,}66\%;\ 12{,}08\%)$.
6. Precyzja: $\Delta=1{,}7057$ p.p.; względna $\delta=\dfrac{1{,}7057}{10{,}37}=0{,}1645$ (16,45%).

### Zad.4
*Odszkodowania: n = 165, xsr = 16 530, S^ = 5542. Przedziały dla 95% i 99%.*

Wspólne kroki: $n=165\ge30$, $\sigma$ nieznane, więc **wzór 2**. $S=\hat S\sqrt{\dfrac{164}{165}}=5525{,}18$.

**a) $\gamma=0{,}95$**
1. $u_\gamma=1{,}9600$ (rząd 0,975).
2. Błąd: $1{,}9600\cdot\dfrac{5525{,}18}{\sqrt{165}}=843{,}05$.
3. Przedział: $(15\,686{,}95;\ 17\,373{,}05)$.
4. $\Delta=843{,}05$; $\delta=\dfrac{843{,}05}{16\,530}=0{,}0510$ (5,10%).

**b) $\gamma=0{,}99$**
1. $u_\gamma=2{,}5758$ (rząd 0,995).
2. Błąd: $2{,}5758\cdot\dfrac{5525{,}18}{\sqrt{165}}=1107{,}95$.
3. Przedział: $(15\,422{,}05;\ 17\,637{,}95)$.
4. $\Delta=1107{,}95$; $\delta=0{,}0670$ (6,70%).

### Zad.6
*Udział produktu zagranicznego: 34 z 100, 95%.*

1. Frakcja: $\hat p=\dfrac{34}{100}=0{,}34$.
2. Kwantyl: $u_\gamma=1{,}9600$.
3. Błąd średni frakcji: $\sqrt{\dfrac{0{,}34\cdot0{,}66}{100}}=0{,}04737$; błąd graniczny: $1{,}9600\cdot0{,}04737=0{,}09285$.
4. Przedział: $0{,}34-0{,}0928=0{,}2472$ oraz $0{,}34+0{,}0928=0{,}4328$, czyli $(0{,}2472;\ 0{,}4328)$.
5. $\Delta=0{,}0928$; $\delta=\dfrac{0{,}0928}{0{,}34}=0{,}2731$ (27,3%).

## Wzory
Legenda: [[Wzory - estymacja#Przedział dla średniej]], [[Wzory - estymacja#Przedział dla frakcji]], [[Wzory - estymacja#Wskaźnik precyzji]].

| Zad. | Ogólny wzór | Z liczbami | Excel |
|---|---|---|---|
| 1 | $\text{xsr}\pm u_\gamma\frac{\sigma}{\sqrt n}$ | $20\pm1{,}96\cdot\frac{8}{6}=20\pm2{,}6133$ | `u: =ROZKŁ.NORMALNY.S.ODWR(0,975)`; `=20-B10*8/6` i `=20+B10*8/6` |
| 2 | $\text{xsr}\pm t_\gamma\frac{S}{\sqrt{n-1}}$ | $10{,}37\pm1{,}8875\cdot\frac{3{,}3813}{\sqrt{14}}$ | `S: =PIERWIASTEK(14/15)*3,5`; `t: =ROZKŁ.T.ODWR.DS(0,08;14)`; `=10,37-B8*B7/PIERWIASTEK(14)` i `+` |
| 4 | $\text{xsr}\pm u_\gamma\frac{S}{\sqrt n}$ | $16530\pm1{,}96\cdot\frac{5525{,}18}{\sqrt{165}}$ | `S: =PIERWIASTEK(164/165)*5542`; `=16530-B8*B7/PIERWIASTEK(165)` i `+`; dla 99%: `ROZKŁ.NORMALNY.S.ODWR(0,995)` |
| 6 | $\hat p\pm u_\gamma\sqrt{\frac{\hat p(1-\hat p)}{n}}$ | $0{,}34\pm1{,}96\sqrt{\frac{0{,}34\cdot0{,}66}{100}}$ | `=34/100`; `=B5-B6*PIERWIASTEK(B5*(1-B5)/100)` i `+` |
| precyzja | $\Delta=\frac{T_2-T_1}{2}$, $\delta=\frac{\Delta}{\text{estymator}}$ | zad.6: $\frac{0{,}4328-0{,}2472}{2}=0{,}0928$, $\frac{0{,}0928}{0{,}34}=0{,}2731$ | `=(C7-B7)/2`; `=B8/B5` |

## Dlaczego tak
- **Wzór 1 ($\sigma$ znane):** gdy znamy $\sigma$, standaryzowana średnia ma rozkład $N(0;1)$, więc bierzemy kwantyl $u$. Słowa-klucze: "wiemy, że sigma = ...".
- **Wzór 3 ($\sigma$ nieznane, mała próba):** gdy $\sigma$ zastępujemy wartością z próby, a $n$ jest małe, rozkład ma "grubsze ogony" ($t$-Studenta z $n-1$ stopniami swobody), więc $t_\gamma>u_\gamma$. Słowa-klucze: "S^ = ...", "rozkład normalny", małe $n$.
- **Wzór 2 ($\sigma$ nieznane, duża próba):** dla $n\ge30$ rozkład $t$ jest praktycznie równy $N(0;1)$, więc bierzemy $u$. Słowa-klucze: "S^ = ...", duże $n$.
- **Frakcja:** przy dużym $n$ frakcja z próby ma w przybliżeniu rozkład normalny. Słowa-klucze: "udział", "ile osób z ... kupuje".
- **$\Delta$ i $\delta$:** $\Delta$ to największy błąd oszacowania w jednostkach danych; $\delta$ pokazuje, jaką część estymatora on stanowi (porównywalne między zadaniami).
- **Zad.4b:** wyższe $\gamma$ daje większy kwantyl, więc szerszy przedział i mniejszą precyzję.

## Interpretacja
- **Zad.1:** "Z ufnością 95% przedział (17,39%; 22,61%) pokrywa nieznaną średnią wartość dyskonta w populacji funduszy. Wskaźnik precyzji to 2,61 p.p., czyli 13,07% oszacowania."
- **Zad.2:** "Z ufnością 92% przeciętna stopa zwrotu z akcji mieści się w przedziale (8,66%; 12,08%). Precyzja: 1,71 p.p. (16,45%)."
- **Zad.4:** "Z ufnością 95% przeciętne żądane odszkodowanie mieści się w (15 687; 17 373), a z ufnością 99% w szerszym (15 422; 17 638). Wyższa ufność oznacza mniejszą precyzję (5,1% kontra 6,7%)."
- **Zad.6:** "Z ufnością 95% udział produktu zagranicznego w rynku to od 24,7% do 43,3%. Przedział jest szeroki ($\delta=27{,}3\%$), bo próba liczy tylko 100 osób."
- Poprawna fraza: "przedział ufności pokrywa nieznaną wartość parametru z prawdopodobieństwem $\gamma$" (nie: "parametr leży w przedziale z prawdopodobieństwem $\gamma$").

## Pułapki
- **Dobór wzoru:** zacznij od schematu ([[Wzory - estymacja#Który wzór]]): $n\ge30$?, $\sigma$ znane?, rozkład normalny?
- **$n$ czy $n-1$ w $S$:** we wzorze 3 jest $S/\sqrt{n-1}$ z $S$ o dzielniku $n$, a w treści "S^" to $\hat S$ (dzielnik $n-1$). Stąd w arkuszu najpierw $S=\hat S\sqrt{(n-1)/n}$. Równoważnie: $t\cdot\hat S/\sqrt n$.
- **Zad.2 kontra Zad.4:** zad.2 dzieli przez $\sqrt{n-1}$ (wzór 3), zad.4 przez $\sqrt n$ (wzór 2 ze slajdu). To nie błąd, tylko dwa różne wzory. Gdyby w zad.4 użyć $\hat S/\sqrt n$, wyjdzie błąd 845,61 zamiast 843,05, przedział (15 684,39; 17 375,61). Przy $n=165$ różnica jest nieistotna, ale na egzaminie trzymaj się wzoru z wykładu.
- **Argument funkcji $t$:** funkcja z argumentem dwustronnym przyjmuje $1-\gamma$ (0,08), a z jednostronnym $\frac{1+\gamma}{2}$ (0,96). Pomylenie daje zły kwantyl.
- **Kwantyl dla $\gamma$:** zawsze rząd $\frac{1+\gamma}{2}$ (95% -> 0,975; 99% -> 0,995; 92% -> 0,96).
- **$\delta$:** dzielimy przez estymator ($\text{xsr}$ albo $\hat p$), nie przez $\Delta$.
- **Jednostki:** w zad.1 i 2 wyniki są w procentach, więc $\Delta$ w punktach procentowych.
