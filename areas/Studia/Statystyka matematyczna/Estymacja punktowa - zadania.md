---
type: notatka
tags: [statystyka, egzamin, estymacja-punktowa, zadania]
project: ["[[Statystyka matematyczna]]"]
people: []
created: 2026-11-10
---
# Estymacja punktowa - zadania
#statystyka #egzamin

Plik źródłowy: `Estymacja_punktowa.xlsx` (arkusze zad.1 - zad.10). Wzory: [[Wzory - estymacja]]. Skrót: [[00 Ściąga - Statystyka]]. Teoria: [[Estymacja punktowa]].

> [!info] O co chodzi w tych zadaniach
> Estymacja punktowa to oszacowanie parametru (średniej, wariancji, frakcji) **jedną liczbą**, razem z jej średnim błędem szacunku. Do tego: błąd średniokwadratowy estymatora i minimalna liczebność próby, żeby błąd nie przekroczył zadanej wartości.

| Zad. | Dane | Szukamy |
|---|---|---|
| 1 | 12 kwot na kontach, $n=12$ | $\text{xsr}$, $\hat S^2$, $\hat D(\text{xsr})$ |
| 2 | 17 cen kawy, $n=17$ | $\text{xsr}$, $\hat S^2$, $\hat S$, $\hat D(\text{xsr})$ |
| 3 | te same 12 kwot, próg 100 zł | $\hat p$, $\hat D(\hat p)$ |
| 4 | $m=1065$, $\sigma=500$, $n=100$ | $E(\text{xsr})$, $D^2(\text{xsr})$, $b$, MSE |
| 5 | $m=53$, $\sigma=10$, $n=400$ | $E(\text{xsr})$, $D^2$, $D$ |
| 6 | $\sigma^2=1\,000\,000$, $D(\text{xsr})\le 26$ | minimalne $n$ |
| 7 | $\hat S^2=185$ (pilotaż), $\hat D(\text{xsr})\le 1{,}2$ | minimalne $n$ |
| 8 | $p=0{,}22$, $\hat D(\hat p)\le 0{,}015$ | minimalne $n$ |
| 9 | $p$ nieznane, $\hat D(\hat p)\le 0{,}015$ | minimalne $n$ |
| 10 | $m=1{,}4$, $\sigma^2=1{,}04$, $n$ od 1 do 220 | $D(\text{xsr})$ i względny błąd |

## Ze slajdów wklejonych w arkusze
Wzory ze zdjęć (zad.1, 3, 4), przepisane:

- $\text{xsr}=\dfrac{1}{n}\sum_{i=1}^{n}X_i$ oraz $\hat S^2=\dfrac{1}{n-1}\sum_{i=1}^{n}(X_i-\text{xsr})^2$
- Błąd estymacji $U=T_n-\theta$, a $E(U)=E(T_n-\theta)=E(T_n)-\theta=b$ (obciążenie)
- Błąd średniokwadratowy: $E(U^2)=E(T_n-\theta)^2=D^2(T_n)+b^2$
- Błąd średni szacunku parametru $\theta$: $\sqrt{E(U^2)}$. Wskazuje, **o ile średnio rzecz biorąc wartość estymatora odchyla się (in plus lub in minus) od wartości $\theta$**. (Na slajdzie pod pierwiastkiem zapisano $E(U)^2$, to literówka.)
- Ocena błędu średniej z próby: $\hat D^2(\text{xsr})=\dfrac{\hat S^2}{n}$, $\;\hat D(\text{xsr})=\dfrac{\hat S}{\sqrt n}$
- Znane $\sigma$: $D^2(\text{xsr})=\dfrac{\sigma^2}{n}$ (zad.4)
- Frakcja (zad.3): $\hat p=\dfrac{K_n}{n}$, $D^2(\hat p)=\dfrac{p(1-p)}{n}$, $\hat D^2(\hat p)=\dfrac{\hat p(1-\hat p)}{n}$

## Rozwiązanie krok po kroku

### Zad.1
*Rewident: 12 kont bankowych. Oszacuj średnią kwotę, wariancję kwot i średni błąd szacunku średniej.*

Kwoty (zł): 87,5; 123,1; 45,3; 52,22; 213; 155; 39; 76,05; 49,8; 99,99; 132; 102,11.

1. Suma kwot: $\sum x_i=1175{,}07$.
2. Średnia: $\text{xsr}=\dfrac{1175{,}07}{12}=97{,}9225$ zł.
3. Dla każdej kwoty liczymy odchylenie $x_i-\text{xsr}$ i jego kwadrat, np. $87{,}5-97{,}9225=-10{,}4225$, kwadrat $108{,}6285$.
4. Suma kwadratów odchyleń: $\sum(x_i-\text{xsr})^2=29\,550{,}181$.
5. Wariancja: $\hat S^2=\dfrac{29\,550{,}181}{12-1}=2686{,}380$.
6. Średni błąd szacunku: $\hat D(\text{xsr})=\sqrt{\dfrac{2686{,}380}{12}}=14{,}962$ zł.

### Zad.2
*Ceny nowej kawy w Nowym Jorku (17 obserwacji). Oszacuj średnią i odchylenie standardowe.*

Ceny: 4,5; 4,25; 4,1; 4,75; 4,8; 3,9; 4,2; 4,55; 4,65; 4,85; 3,85; 4,15; 4,85; 3,95; 4,3; 4,6; 4.

1. Suma cen: $74{,}25$; średnia $\text{xsr}=\dfrac{74{,}25}{17}=4{,}3676$.
2. Suma kwadratów odchyleń: $1{,}94471$.
3. Wariancja: $\hat S^2=\dfrac{1{,}94471}{17-1}=0{,}12154$.
4. Odchylenie standardowe: $\hat S=\sqrt{0{,}12154}=0{,}3486$.
5. Średni błąd szacunku średniej: $\hat D(\text{xsr})=\sqrt{\dfrac{0{,}12154}{17}}=0{,}0846$.

### Zad.3
*Frakcja kont firmy z kwotą powyżej 100 zł (te same dane co w zad.1).*

1. Zliczamy kwoty $>100$: 123,1; 213; 155; 132; 102,11, czyli $K=5$ (99,99 nie spełnia warunku).
2. Frakcja: $\hat p=\dfrac{5}{12}=0{,}4167$.
3. Średni błąd szacunku: $\hat D(\hat p)=\sqrt{\dfrac{0{,}4167\cdot 0{,}5833}{12}}=0{,}1423$.

### Zad.4
*Populacja: $m=1065$, $\sigma=500$, $n=100$. Wartość oczekiwana i wariancja średniej z próby, błąd średniokwadratowy.*

1. $E(\text{xsr})=m=1065$.
2. $D^2(\text{xsr})=\dfrac{\sigma^2}{n}=\dfrac{500^2}{100}=2500$.
3. Obciążenie: $b=E(\text{xsr})-m=1065-1065=0$.
4. $\text{MSE}=D^2+b^2=2500+0=2500$.
5. $\text{RMSE}=\sqrt{2500}=50$.

### Zad.5
*$n=400$, $m=53$, $\sigma=10$. Wartość oczekiwana i odchylenie standardowe średniej z próby.*

1. $E(\text{xsr})=53$.
2. $D^2(\text{xsr})=\dfrac{10^2}{400}=0{,}25$.
3. $D(\text{xsr})=\sqrt{0{,}25}=0{,}5$.

### Zad.6
*$\sigma^2=1\,000\,000$, odchylenie standardowe średniej co najwyżej 26. Minimalne $n$.*

1. Warunek: $D^2(\text{xsr})=\dfrac{\sigma^2}{n}\le 26^2=676$.
2. $n\ge\dfrac{1\,000\,000}{676}=1479{,}29$.
3. Zaokrąglenie w górę: $n=1480$.

### Zad.7
*Pilotaż: wariancja z próby 185 min$^2$. Średni błąd szacunku średniej co najwyżej 1,2 min. Minimalne $n$.*

1. Warunek: $\hat D^2(\text{xsr})=\dfrac{\hat S^2}{n}\le 1{,}2^2=1{,}44$.
2. $n\ge\dfrac{185}{1{,}44}=128{,}47$.
3. Zaokrąglenie w górę: $n=129$.

### Zad.8
*Frakcja zmieniających pracę $p=0{,}22$, średni błąd szacunku frakcji co najwyżej 0,015.*

1. Warunek: $\hat D^2(\hat p)=\dfrac{p(1-p)}{n}\le 0{,}015^2=0{,}000225$.
2. $p(1-p)=0{,}22\cdot 0{,}78=0{,}1716$.
3. $n\ge\dfrac{0{,}1716}{0{,}000225}=762{,}67$.
4. Zaokrąglenie w górę: $n=763$.

### Zad.9
*Frakcja wadliwych sztuk nieznana, "absolutna pewność", średni błąd frakcji co najwyżej 0,015.*

1. Brak informacji o $p$, więc bierzemy najgorszy przypadek $\hat p=0{,}5$ (wtedy $p(1-p)=0{,}25$ jest największe).
2. $n\ge\dfrac{0{,}5\cdot 0{,}5}{0{,}000225}=1111{,}11$.
3. Zaokrąglenie w górę: $n=1112$.

### Zad.10
*$m=1{,}4$, $\sigma^2=1{,}04$ (czyli $\sigma=1{,}0198$). Odchylenie standardowe i względny błąd średniej dla różnych $n$.*

1. $D(\text{xsr})=\dfrac{\sigma}{\sqrt n}$.
2. Względny błąd: $V=\dfrac{D(\text{xsr})}{m}=\dfrac{D(\text{xsr})}{1{,}4}$.

| $n$ | $D(\text{xsr})$ | $V$ |
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
Ogólna wersja i legenda: [[Wzory - estymacja#Średnia i wariancja z próby]], [[Wzory - estymacja#Estymacja punktowa]], [[Wzory - estymacja#Niezbędna liczebność próby]].

| Co | Ogólny wzór | Z liczbami | Excel |
|---|---|---|---|
| średnia (zad.1) | $\text{xsr}=\frac{1}{n}\sum x_i$ | $\frac{1}{12}\cdot 1175{,}07=97{,}9225$ | `=ŚREDNIA(A6:A17)`; kontrolnie `=1/12*A18` |
| średnia (zad.2) | j.w. | $\frac{74{,}25}{17}=4{,}3676$ | `=1/17*A24` |
| wariancja (zad.1) | $\hat S^2=\frac{1}{n-1}\sum(x_i-\text{xsr})^2$ | $\frac{29550{,}181}{11}=2686{,}380$ | `=WARIANCJA.A(A6:A17)`; kontrolnie `=(1/(B19-1))*D18` |
| wariancja (zad.2) | j.w. | $\frac{1{,}94471}{16}=0{,}12154$ | `=(1/(17-1))*C24` |
| błąd średniej (zad.1) | $\hat D(\text{xsr})=\sqrt{\hat S^2/n}$ | $\sqrt{2686{,}380/12}=14{,}962$ | `=PIERWIASTEK(D23/B19)` |
| błąd średniej (zad.2) | j.w. | $\sqrt{0{,}12154/17}=0{,}0846$ | `=PIERWIASTEK(D27/17)` |
| frakcja (zad.3) | $\hat p=K/n$ | $5/12=0{,}4167$ | `=LICZ.JEŻELI(A7:A18;">100")`, potem `=E19/C19` |
| błąd frakcji (zad.3) | $\hat D(\hat p)=\sqrt{\hat p(1-\hat p)/n}$ | $\sqrt{0{,}4167\cdot0{,}5833/12}=0{,}1423$ | `=PIERWIASTEK(C21*(1-C21)/C19)` |
| wariancja średniej (zad.4, 5) | $D^2=\sigma^2/n$ | $500^2/100=2500$; $10^2/400=0{,}25$ | `=B8^2/B9`; `=E6^2/E4` |
| obciążenie, MSE (zad.4) | $b=E-m$; $\text{MSE}=D^2+b^2$ | $0$; $2500$ | `=B11-B7`; `=B12+B13^2` |
| RMSE, odchylenie średniej | $\sqrt{\text{MSE}}$, $\sqrt{D^2}$ | $50$; $0{,}5$ | `=PIERWIASTEK(B14)`; `=PIERWIASTEK(B7)` |
| min. $n$ (zad.6) | $n\ge\sigma^2/D^2$ | $1000000/676=1479{,}29$ | `=B4/B6`, `=ZAOKR.W.GÓRĘ(E4;0)` |
| min. $n$ (zad.7) | $n\ge\hat S^2/D^2$ | $185/1{,}44=128{,}47$ | `=B7/D9`, `=ZAOKR.W.GÓRĘ(B11;0)` |
| min. $n$ (zad.8) | $n\ge p(1-p)/D^2$ | $0{,}1716/0{,}000225=762{,}67$ | `=B7*(1-B7)/B9`, `=ZAOKR.W.GÓRĘ(B6;0)` |
| min. $n$ (zad.9) | $n\ge 0{,}25/D^2$ | $0{,}25/0{,}000225=1111{,}11$ | `=B8*(1-B8)/B10`, `=ZAOKR.W.GÓRĘ(B11;0)` |
| odchylenie średniej (zad.10) | $D=\sigma/\sqrt n$ | $1{,}0198/\sqrt{100}=0{,}1020$ | `=$B$20/PIERWIASTEK(A6)`, gdzie `B20` to `=PIERWIASTEK(B19)` |
| względny błąd (zad.10) | $V=D/m$ | $0{,}1020/1{,}4=7{,}28\%$ | `=B6/$B$18` |

## Dlaczego tak
- **Zad.1, 2: dzielimy przez $n-1$.** Wariancję populacji szacujemy z próby; dzielnik $n-1$ daje estymator nieobciążony ($E(\hat S^2)=\sigma^2$). Słowa-klucze: "oszacuj wariancję", "szacowany średni błąd szacunku".
- **Zad.1, 2: błąd średniej to $\hat S/\sqrt n$.** Średnia z próby ma rozrzut $\sigma/\sqrt n$, a nieznane $\sigma$ zastępujemy $\hat S$.
- **Zad.3:** frakcja to średnia zmiennej zero-jedynkowej, więc $\hat p=K/n$, a jej wariancja wynika z rozkładu dwumianowego. Słowa-klucze: "frakcja", "udział", "kwoty powyżej".
- **Zad.4, 5:** parametry populacji są znane, więc liczymy teoretyczne $E$ i $D^2$ bez szacowania. Słowa-klucze: "wartość oczekiwana i wariancja dla średniej z próby", "błąd średniokwadratowy".
- **MSE:** $D^2+b^2$ łączy rozrzut i obciążenie. Dla estymatora nieobciążonego MSE równa się wariancji.
- **Zad.6 - 9:** z warunku "błąd co najwyżej" robimy nierówność względem $n$. W zad.7 $\sigma$ jest nieznane, więc bierzemy wariancję z pilotażu. W zad.9 $p$ nieznane, więc $p=0{,}5$ (najgorszy przypadek, wystarcza dla każdego $p$). Słowa-klucze: "minimalna liczebność", "co najwyżej", "niezależnie od".
- **Zad.10:** pokazuje, że błąd maleje z $\sqrt n$: żeby zmniejszyć go o połowę, trzeba 4 razy większej próby.

## Interpretacja
- **Zad.1:** "Średnia kwota na kontach firmy jest szacowana na 97,92 zł, a wariancja kwot na 2686,38. Szacunek średniej odchyla się od rzeczywistej średniej średnio o 14,96 zł."
- **Zad.2:** "Średnia cena nowej kawy to ok. 4,37, odchylenie standardowe cen ok. 0,35; średni błąd szacunku średniej wynosi 0,085."
- **Zad.3:** "Szacujemy, że 41,67% kont ma kwotę powyżej 100 zł; średni błąd tego szacunku to 14,2 punktu procentowego."
- **Zad.4:** "Estymator jest nieobciążony ($b=0$), więc błąd średniokwadratowy równa się wariancji (2500); średnio średnia z próby odchyla się od $m$ o 50."
- **Zad.6 - 9:** "Aby średni błąd szacunku nie przekroczył zadanej wartości, trzeba wylosować co najmniej 1480 (zad.6), 129 (zad.7), 763 (zad.8) lub 1112 (zad.9) jednostek."
- **Zad.10:** "Przy $n=100$ średnia z próby odchyla się od $m$ średnio o 0,102, czyli o 7,3% wartości oczekiwanej."

## Pułapki
- **$n$ czy $n-1$:** $\hat S^2$ dzieli przez $n-1$, $S^2$ przez $n$. W tym pliku wszędzie $n-1$.
- **Zad.2: etykieta kłamie.** Komórka D27 ma podpis "szacowane odchylenie standardowe", a zawiera **wariancję** (0,12154). Odchylenie to 0,3486. **Błąd w arkuszu.**
- **Zad.4: etykiety.** B7 podpisane "xsr" to w rzeczywistości $m$ (średnia populacji); B8 podpisane "sigma^2" to $\sigma=500$ (formuła i tak podnosi do kwadratu, więc liczby się zgadzają). Obciążenie `=B11-B7` jest zawsze 0, bo B11 równa się B7; sensownie: $b=E(\text{xsr})-m$.
- **Zad.1:** użyto `WARIANCJA.A`, a nie funkcji dla próby. Dla zwykłych liczb to ten sam wynik co `WARIANCJA.PRÓBKI`, ale lepiej używać drugiej.
- **Zad.6 i "+1":** arkusz liczy $n\ge\sigma^2/D^2$ bez "+1" (1480). Skrypt z wykładu ma wzór z "+1" (dałby 1481). Zapytaj prowadzącego, którą wersję stosuje.
- **Zad.8:** podpis B8 to "D^(xsr)", a chodzi o błąd frakcji.
- **Zad.10:** kolumna "odchylenie" to odchylenie standardowe **średniej** ($\sigma/\sqrt n$), nie $\sigma$.
- **Zawsze zaokrąglaj $n$ w górę** (`ZAOKR.W.GÓRĘ`).
- **MSE kontra RMSE:** MSE to wariancja (kwadrat jednostki), RMSE to pierwiastek (jednostka danych).
