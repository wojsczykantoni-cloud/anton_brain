---
type: notatka
tags: [statystyka, egzamin, estymacja-przedzialowa, zadania]
project: ["[[Statystyka matematyczna]]"]
people: []
created: 2026-11-10
---
# Estymacja przedziałowa 1 - zadania
#statystyka #egzamin

Plik źródłowy: `Estymacja_przedzia_owa_1.xlsx` (arkusze Zad.1 - Zad.9). W pliku są **same treści zadań, bez żadnych obliczeń**; na arkuszach Zad.8 i Zad.9 są tylko zdjęcia ze wzorami. Zad.1, 2, 4, 6 mają rozwiązania w [[Estymacja przedziałowa 1 - rozwiązania]]. Zad.3, 5, 7, 8, 9 **policzyłem sam** według wzorów z [[Wzory - estymacja]] i oznaczam je jako "policzone przeze mnie". Wzory: [[Wzory - estymacja]]. Skrót: [[00 Ściąga - Statystyka]].

> [!info] O co chodzi
> Przedziały ufności dla średniej i frakcji oraz minimalna liczebność próby dla zadanego wskaźnika precyzji. Polecenie w zad.1 - 7: "Wyznacz wskaźnik precyzji estymacji oraz względny wskaźnik precyzji estymacji".

| Zad. | Treść w skrócie | Typ | Rozwiązanie |
|---|---|---|---|
| 1 | dyskonto, $\sigma=8$ znane, $n=36$, 95% | średnia, wzór 1 | [[Estymacja przedziałowa 1 - rozwiązania#Zad.1]] |
| 2 | stopa zwrotu, $n=15$, $\hat S=3{,}5$, 92% | średnia, wzór 3 | [[Estymacja przedziałowa 1 - rozwiązania#Zad.2]] |
| 3 | baterie, $n=12$, $\text{xsr}=34{,}2$ h, $\hat S=5{,}9$, 90% | średnia, wzór 3 | niżej (policzone przeze mnie) |
| 4 | odszkodowania, $n=165$, 95% i 99% | średnia, wzór 2 | [[Estymacja przedziałowa 1 - rozwiązania#Zad.4]] |
| 5 | domy, $n=200$, $\text{xsr}=647\,000$, $\hat S=140\,000$, 80% | średnia, wzór 2 | niżej (policzone przeze mnie) |
| 6 | 34 z 100, 95% | frakcja | [[Estymacja przedziałowa 1 - rozwiązania#Zad.6]] |
| 7 | 53 z 250 par, 90% | frakcja | niżej (policzone przeze mnie) |
| 8 | wydatki kuracjuszy, $\Delta_0=120$, $\sigma=400$, 95% | minimalne $n$, średnia | niżej (policzone przeze mnie) |
| 9 | frakcja ok. 0,25, $\Delta_0=0{,}10$, 99% | minimalne $n$, frakcja | niżej (policzone przeze mnie) |

## Ze slajdów wklejonych w arkusze
Zad.1 - 7 mają te same slajdy co [[Estymacja przedziałowa 1 - rozwiązania#Ze slajdów wklejonych w arkusze]] (trzy wzory na średnią, schemat wyboru wzoru, wariancje $S^2$ i $\hat S^2$, przedział dla frakcji). Dodatkowo:

**Zad.8 - niezbędna liczebność próby, $\sigma$ znane i nieznane** (z podpisami "sigma znane" / "sigma nieznane" w arkuszu):
- $\sigma$ znane: $\dfrac{\sigma}{\sqrt n}z_\gamma\le\Delta_0$, czyli $n\ge\dfrac{\sigma^2}{\Delta_0^2}z_\gamma^2$, gdzie $P(|Z|<z_\gamma)=\gamma$, $Z\sim N(0;1)$.
- $\sigma$ nieznane: $\dfrac{\hat S}{\sqrt n}t_\gamma\le\Delta_0$, czyli $n\ge\dfrac{\hat S^2}{\Delta_0^2}t_\gamma^2$, gdzie $P(|T_{n-1}|<t_\gamma)=\gamma$.

**Zad.9 - niezbędna liczebność próby dla frakcji:**
$$\Delta=\sqrt{\frac{\hat p(1-\hat p)}{n}}\,u_\gamma\le\Delta_0\qquad\Rightarrow\qquad n\ge\frac{\hat p(1-\hat p)}{\Delta_0^2}\,u_\gamma^2,\quad P(|U_n|\le u_\gamma)=\gamma,\ U_n\sim N(0;1)$$

## Rozwiązanie krok po kroku (zadania bez rozwiązania w pliku)

### Zad.3
*policzone przeze mnie: baterie, n = 12, xsr = 34,2 h, S^ = 5,9 h, 90%, rozkład normalny.*

1. Wybór wzoru: $n=12<30$, rozkład normalny, $\sigma$ nieznane, więc **wzór 3**.
2. Kwantyl: $\gamma=0{,}90$, rząd $0{,}95$, $n-1=11$ stopni swobody, $t_\gamma=1{,}7959$.
3. Odchylenie z dzielnikiem $n$: $S=5{,}9\sqrt{\dfrac{11}{12}}=5{,}6488$.
4. Błąd: $1{,}7959\cdot\dfrac{5{,}6488}{\sqrt{11}}=3{,}0587$.
5. Przedział: $34{,}2\mp3{,}0587$, czyli $(31{,}14;\ 37{,}26)$ godz.
6. $\Delta=3{,}0587$; $\delta=\dfrac{3{,}0587}{34{,}2}=0{,}0894$ (8,94%).

### Zad.5
*policzone przeze mnie: domy w Ventura County, n = 200, xsr = 647 000 USD, S^ = 140 000 USD, 80%.*

1. Wybór wzoru: $n=200\ge30$, $\sigma$ nieznane, więc **wzór 2**.
2. Kwantyl: $\gamma=0{,}80$, rząd $0{,}90$, $u_\gamma=1{,}2816$.
3. $S=140\,000\sqrt{\dfrac{199}{200}}=139\,649{,}56$.
4. Błąd: $1{,}2816\cdot\dfrac{139\,649{,}56}{\sqrt{200}}=12\,654{,}96$.
5. Przedział: $(634\,345{,}04;\ 659\,654{,}96)$ USD.
6. $\Delta=12\,654{,}96$; $\delta=\dfrac{12\,654{,}96}{647\,000}=0{,}0196$ (1,96%).

(Wariant $\hat S/\sqrt n$ dałby błąd 12 686,71, różnica symboliczna.)

### Zad.7
*policzone przeze mnie: 53 z 250 rozwiedzionych par ma trudności z podziałem majątku, 90%.*

1. Frakcja: $\hat p=\dfrac{53}{250}=0{,}212$.
2. Kwantyl: $\gamma=0{,}90$, rząd $0{,}95$, $u_\gamma=1{,}6449$.
3. Błąd średni: $\sqrt{\dfrac{0{,}212\cdot0{,}788}{250}}=0{,}02585$; błąd graniczny: $1{,}6449\cdot0{,}02585=0{,}04252$.
4. Przedział: $(0{,}1695;\ 0{,}2545)$.
5. $\Delta=0{,}0425$; $\delta=\dfrac{0{,}0425}{0{,}212}=0{,}2006$ (20,1%).

### Zad.8
*policzone przeze mnie: wydatki na rozrywki, Delta0 = 120 USD, sigma = 400 USD (znane), 95%.*

1. Wariant: odchylenie standardowe w populacji podane, więc $\sigma$ **znane** ($z_\gamma$, nie $t$).
2. Kwantyl: $z_\gamma=1{,}9600$.
3. Warunek: $\dfrac{\sigma}{\sqrt n}z_\gamma\le\Delta_0$, czyli $n\ge\dfrac{400^2\cdot1{,}96^2}{120^2}=\dfrac{160\,000\cdot3{,}8415}{14\,400}=42{,}68$.
4. Zaokrąglenie w górę: $n=43$.

### Zad.9
*policzone przeze mnie: frakcja zainteresowanych zakupem, phat około 0,25, Delta0 = 0,10, 99%.*

1. Kwantyl: $\gamma=0{,}99$, rząd $0{,}995$, $u_\gamma=2{,}5758$, $u_\gamma^2=6{,}6349$.
2. $n\ge\dfrac{\hat p(1-\hat p)}{\Delta_0^2}u_\gamma^2=\dfrac{0{,}25\cdot0{,}75}{0{,}10^2}\cdot6{,}6349=\dfrac{0{,}1875}{0{,}01}\cdot6{,}6349=124{,}40$.
3. Zaokrąglenie w górę: $n=125$.

## Wzory
Legenda: [[Wzory - estymacja#Przedział dla średniej]], [[Wzory - estymacja#Przedział dla frakcji]], [[Wzory - estymacja#Niezbędna liczebność próby]].

| Zad. | Ogólny wzór | Z liczbami | Excel |
|---|---|---|---|
| 3 | $\text{xsr}\pm t_\gamma\frac{S}{\sqrt{n-1}}$ | $34{,}2\pm1{,}7959\cdot\frac{5{,}6488}{\sqrt{11}}$ | `=34,2-ROZKŁ.T.ODWR(0,95;11)*PIERWIASTEK(11/12)*5,9/PIERWIASTEK(11)` i `+` |
| 5 | $\text{xsr}\pm u_\gamma\frac{S}{\sqrt n}$ | $647000\pm1{,}2816\cdot\frac{139649{,}56}{\sqrt{200}}$ | `=647000-ROZKŁ.NORMALNY.S.ODWR(0,9)*PIERWIASTEK(199/200)*140000/PIERWIASTEK(200)` i `+` |
| 7 | $\hat p\pm u_\gamma\sqrt{\frac{\hat p(1-\hat p)}{n}}$ | $0{,}212\pm1{,}6449\sqrt{\frac{0{,}212\cdot0{,}788}{250}}$ | `=53/250-ROZKŁ.NORMALNY.S.ODWR(0,95)*PIERWIASTEK((53/250)*(1-53/250)/250)` i `+` |
| 8 | $n\ge\frac{\sigma^2}{\Delta_0^2}z_\gamma^2$ | $\frac{400^2\cdot1{,}96^2}{120^2}=42{,}68\to43$ | `=ZAOKR.W.GÓRĘ(400^2*ROZKŁ.NORMALNY.S.ODWR(0,975)^2/120^2;0)` |
| 9 | $n\ge\frac{\hat p(1-\hat p)}{\Delta_0^2}u_\gamma^2$ | $\frac{0{,}25\cdot0{,}75}{0{,}01}\cdot2{,}5758^2=124{,}40\to125$ | `=ZAOKR.W.GÓRĘ(0,25*0,75*ROZKŁ.NORMALNY.S.ODWR(0,995)^2/0,1^2;0)` |

Wariant z $\sigma$ nieznanym w zad.8: $n\ge\hat S^2t_\gamma^2/\Delta_0^2$, przykład w [[Estymacja przedziałowa 2 - rozwiązania#Zad. 1]].

## Dlaczego tak
- **Zad.3:** mała próba (12), rozkład normalny, $\sigma$ nieznane, więc $t$-Studenta. Słowa-klucze: "S^ = ...", "rozkład normalny", $n=12$.
- **Zad.5:** $n=200$ jest duże, więc $t\approx u$; $\sigma$ nieznane ("odchylenie standardowe z próby"), stąd wzór 2.
- **Zad.7:** to frakcja (53 z 250). Słowa-klucze: "frakcja wszystkich rozwiedzionych par", "ile ma trudności".
- **Zad.8:** "wskaźnik precyzji nie większy niż" plus "minimalna wymagana liczebność" to nierówność $\Delta\le\Delta_0$ rozwiązana względem $n$. "Odchylenie standardowe w populacji wynosi 400" oznacza $\sigma$ znane, więc kwantyl $z$.
- **Zad.9:** firma ma bieżące dane, że frakcja to około 0,25, więc podstawiamy ją zamiast najgorszego $p=0{,}5$ (mniejsza próba).

## Interpretacja
- **Zad.3:** "Z ufnością 90% przeciętna długość życia bateryjki mieści się w przedziale 31,1 - 37,3 h. Precyzja to 3,06 h (8,9%)."
- **Zad.5:** "Z ufnością 80% przeciętna wartość domu w Ventura County to 634 345 - 659 655 USD. Błąd graniczny 12 655 USD to 1,96% średniej, czyli bardzo precyzyjne oszacowanie."
- **Zad.7:** "Z ufnością 90% od 17,0% do 25,5% rozwiedzionych par ma duże trudności w podziale majątku."
- **Zad.8, 9:** "Aby wskaźnik precyzji nie przekroczył zadanej wartości przy podanej ufności, trzeba zbadać co najmniej 43 kuracjuszy (zad.8) i 125 osób (zad.9)."

## Pułapki
- **Zad.1 - 6 w tym pliku nie mają obliczeń**, tylko treść. Rozwiązania: [[Estymacja przedziałowa 1 - rozwiązania]].
- **Zad.8:** nie mylić wariantów. $\sigma$ znane: $z$ i $\sigma^2$. $\sigma$ nieznane: $t$ i $\hat S^2$ (stopnie swobody z próby pilotażowej). W treści jest "odchylenie standardowe w populacji", więc $z$.
- **Zad.9:** nie podstawiaj 0,5, skoro znasz przybliżone $p=0{,}25$. Dla $p=0{,}5$ wyszłoby $n=166$, czyli niepotrzebnie duża próba.
- **Zad.5:** dane w dolarach, nie w tysiącach; 647 000 to $\text{xsr}$ (średnia z próby w treści).
- **Zawsze zaokrąglaj $n$ w górę.**
- **Kwantyl dla $\gamma$:** rząd $\frac{1+\gamma}{2}$ (0,80 -> 0,90; 0,90 -> 0,95; 0,99 -> 0,995).
