---
type: notatka
tags: [statystyka, egzamin, estymacja-przedzialowa, zadania]
project: ["[[Statystyka matematyczna]]"]
people: []
created: 2026-11-10
---
# Estymacja przedziałowa 2 - rozwiązania
#statystyka #egzamin

Plik źródłowy: `Estymacja_przedzia_owa_2_-_rozw.xlsx` (arkusze Zad. 1 - Zad. 5). Wzory: [[Wzory - estymacja]]. Skrót: [[00 Ściąga - Statystyka]]. Poprzednia część: [[Estymacja przedziałowa 1 - rozwiązania]].

> [!info] O co chodzi w tych zadaniach
> Minimalna liczebność próby dla przedziału średniej (zad.1), przedział ufności dla **wariancji** (zad.2, 3) i dla **współczynnika korelacji** (zad.4, 5).

| Zad. | Dane | Szukamy |
|---|---|---|
| 1 | $\Delta_0=15$ N, $\gamma=0{,}95$, $\hat S=35$ N z próby $n=20$ | minimalne $n$ ($\sigma$ nieznane) |
| 2 | $n=29$, $S^2=18\,540$, $\gamma=0{,}95$, rozkład normalny | przedział dla wariancji ($\chi^2$) |
| 3 | $n=122$, $\hat S^2=8$, $\gamma=0{,}95$, rozkład normalny | przedział dla wariancji: dokładny i duża próba |
| 4 | $n=150$, $R=-0{,}65$, $\gamma=0{,}95$ | przedział dla korelacji (duża próba) |
| 5 | $n=29$, $R=0{,}45$, $\gamma=0{,}90$ | przedział dla korelacji (Fisher) |

## Ze slajdów wklejonych w arkusze
- **Zad.1:** $\dfrac{\hat S}{\sqrt n}t_\gamma\le\Delta_0$, czyli $n\ge\dfrac{\hat S^2}{\Delta_0^2}t_\gamma^2$; $P(|T_{n-1}|<t_\gamma)=\gamma$ oraz $P(|U_n|\le u_\gamma)=\gamma$, $U_n\sim N(0;1)$.
- **Zad.2:** $U_{n-1}=\dfrac{nS^2}{\sigma^2}=\dfrac{(n-1)\hat S^2}{\sigma^2}$ ma rozkład $\chi^2_{n-1}$. Przedział: $P\{T_{1n}<\sigma^2<T_{2n}\mid\sigma^2\}=\gamma$, gdzie $T_{1n}=\dfrac{(n-1)\hat S^2}{c_1}=\dfrac{nS^2}{c_1}$, $T_{2n}=\dfrac{(n-1)\hat S^2}{c_2}=\dfrac{nS^2}{c_2}$. $c_1$ i $c_2$ to kwantyle $\chi^2_{n-1}$ rzędów $\frac{1+\gamma}{2}$ i $\frac{1-\gamma}{2}$: $P(U_{n-1}<c_1)=\frac{1+\gamma}{2}$, $P(U_{n-1}<c_2)=\frac{1-\gamma}{2}$.
- **Zad.3 (duża próba):** $T_{*1n}=\dfrac{(n-1)\hat S^2}{n-1+z_\gamma\sqrt{2(n-1)}}$, $T_{*2n}=\dfrac{(n-1)\hat S^2}{n-1-z_\gamma\sqrt{2(n-1)}}$, przy czym $P\{Z<z_\gamma\}=\frac{1+\gamma}{2}$, $Z\sim N(0;1)$.
- **Zad.4 (duża próba):** $T_{1n}=R-z_\gamma\dfrac{1-R^2}{\sqrt n}$, $T_{2n}=R+z_\gamma\dfrac{1-R^2}{\sqrt n}$, $P\{Z<z_\gamma\}=\frac{1+\gamma}{2}$.
- **Zad.5 (umiarkowana liczebność, Fisher):** $U_n=\frac12\ln\frac{1+R}{1-R}$; $A_{1n}=U_n-\frac{v_\gamma}{\sqrt{n-3}}$, $A_{2n}=U_n+\frac{v_\gamma}{\sqrt{n-3}}$; $T_{1*n}=\frac{e^{2A_{1n}}-1}{e^{2A_{1n}}+1}$, $T_{2*n}=\frac{e^{2A_{2n}}-1}{e^{2A_{2n}}+1}$; $P\{|V|<v_\gamma\}=\gamma$, $V\sim N(0;1)$.

Pełny opis: [[Wzory - estymacja#Przedział dla wariancji]], [[Wzory - estymacja#Przedział dla korelacji]].

## Rozwiązanie krok po kroku

### Zad. 1
*Wytrzymałość komponentów lotniczych: wskaźnik precyzji co najwyżej 15 N przy 95%, pilotaż n = 20, S^ = 35 N. Minimalne n.*

1. Warunek: $\Delta=\dfrac{\hat S}{\sqrt n}t_\gamma\le\Delta_0=15$, $\sigma$ nieznane, więc kwantyl $t$.
2. Kwantyl: rząd $0{,}975$, stopnie swobody z pilotażu $20-1=19$: $t_\gamma=2{,}0930$.
3. $n\ge\dfrac{\hat S^2t_\gamma^2}{\Delta_0^2}=\dfrac{35^2\cdot2{,}0930^2}{15^2}=\dfrac{1225\cdot4{,}3807}{225}=23{,}85$.
4. Zaokrąglenie w górę: $n=24$.

### Zad. 2
*Maszyna napełniająca kawę: n = 29, S^2 = 18 540. Przedział dla wariancji, 95%.*

1. Stopnie swobody: $n-1=28$. W treści jest "S^2" bez daszka, czyli wariancja z dzielnikiem $n$: licznik $nS^2=29\cdot18\,540$.
2. Kwantyle $\chi^2_{28}$: $c_1$ rzędu $0{,}975$: $44{,}4608$; $c_2$ rzędu $0{,}025$: $15{,}3079$.
3. Dolny koniec: $T_{1n}=\dfrac{29\cdot18\,540}{44{,}4608}=12\,092{,}90$.
4. Górny koniec: $T_{2n}=\dfrac{29\cdot18\,540}{15{,}3079}=35\,123{,}13$.
5. Przedział dla wariancji: $(12\,092{,}9;\ 35\,123{,}1)$.

### Zad. 3
*Czas obsługi w banku: n = 122, S^2 = 8, 95%. Przedział dla wariancji.*

**Dokładnie ($\chi^2$):**
1. $n-1=121$; $c_1=153{,}3379$ (rząd 0,975), $c_2=92{,}4462$ (rząd 0,025).
2. $T_{1n}=\dfrac{121\cdot8}{153{,}3379}=6{,}3129$; $T_{2n}=\dfrac{121\cdot8}{92{,}4462}=10{,}4710$.
3. Przedział: $(6{,}31;\ 10{,}47)$.

**Duża próba (przybliżenie normalne):**
4. $z_\gamma=1{,}9600$; $\sqrt{2\cdot121}=15{,}5563$; $z_\gamma\sqrt{2(n-1)}=30{,}4899$.
5. $T_{*1n}=\dfrac{968}{121+30{,}4899}=\dfrac{968}{151{,}4899}=6{,}3899$.
6. $T_{*2n}=\dfrac{968}{121-30{,}4899}=\dfrac{968}{90{,}5101}=10{,}6949$.
7. Przedział: $(6{,}39;\ 10{,}69)$.

### Zad. 4
*150 studentów: R = -0,65 (nauka vs rozrywka), 95%. Przedział dla korelacji.*

1. $1-R^2=1-0{,}4225=0{,}5775$.
2. $z_\gamma=1{,}9600$ (rząd 0,975); $\sqrt{150}=12{,}2474$.
3. Błąd: $z_\gamma\dfrac{1-R^2}{\sqrt n}=1{,}9600\cdot\dfrac{0{,}5775}{12{,}2474}=0{,}0924$.
4. $T_{1n}=-0{,}65-0{,}0924=-0{,}7424$; $T_{2n}=-0{,}65+0{,}0924=-0{,}5576$.
5. Przedział: $(-0{,}7424;\ -0{,}5576)$.

### Zad. 5
*29 pracowników: R = 0,45 (odległość vs spóźnienia), 90%. Przedział dla korelacji.*

1. Mała liczebność ($n=29$), więc transformacja Fishera. $v_\gamma$ to kwantyl $N(0;1)$ rzędu $0{,}95$: $v_\gamma=1{,}6449$.
2. $U_n=\frac12\ln\dfrac{1+0{,}45}{1-0{,}45}=\frac12\ln2{,}6364=0{,}4847$.
3. $\dfrac{v_\gamma}{\sqrt{n-3}}=\dfrac{1{,}6449}{\sqrt{26}}=0{,}3226$.
4. $A_{1n}=0{,}4847-0{,}3226=0{,}1621$; $A_{2n}=0{,}4847+0{,}3226=0{,}8073$.
5. Powrót do skali korelacji: $T_{1*n}=\dfrac{e^{2\cdot0{,}1621}-1}{e^{2\cdot0{,}1621}+1}=0{,}1607$; $T_{2*n}=\dfrac{e^{2\cdot0{,}8073}-1}{e^{2\cdot0{,}8073}+1}=0{,}6681$.
6. Przedział: $(0{,}1607;\ 0{,}6681)$.

## Wzory
Legenda: [[Wzory - estymacja#Niezbędna liczebność próby]], [[Wzory - estymacja#Przedział dla wariancji]], [[Wzory - estymacja#Przedział dla korelacji]].

| Zad. | Ogólny wzór | Z liczbami | Excel |
|---|---|---|---|
| 1 | $n\ge\frac{\hat S^2t_\gamma^2}{\Delta_0^2}$ | $\frac{35^2\cdot2{,}0930^2}{15^2}=23{,}85\to24$ | `t: =ROZKŁ.T.ODWR(0,975;19)`; `=B8^2*B9^2/B6^2`; `=ZAOKR.W.GÓRĘ(B10;0)` |
| 2 | $T_{1n}=\frac{nS^2}{c_1}$, $T_{2n}=\frac{nS^2}{c_2}$ | $\frac{29\cdot18540}{44{,}4608}=12092{,}90$; $\frac{29\cdot18540}{15{,}3079}=35123{,}13$ | `c1: =ROZKŁ.CHI.ODWR(0,975;28)`; `c2: =ROZKŁ.CHI.ODWR(0,025;28)`; `=29*B7/B8`; `=29*B7/B9` |
| 3 dokładnie | $T_{1n}=\frac{(n-1)\hat S^2}{c_1}$, $T_{2n}=\frac{(n-1)\hat S^2}{c_2}$ | $\frac{121\cdot8}{153{,}3379}=6{,}3129$; $\frac{121\cdot8}{92{,}4462}=10{,}4710$ | `=121*B6/B7`; `=121*B6/B8` (kwantyle `ROZKŁ.CHI.ODWR(0,975;121)` i `(0,025;121)`) |
| 3 duża próba | $T_{*1n}=\frac{(n-1)\hat S^2}{n-1+z_\gamma\sqrt{2(n-1)}}$ | $\frac{968}{121+30{,}4899}=6{,}3899$; $\frac{968}{121-30{,}4899}=10{,}6949$ | `z: =ROZKŁ.NORMALNY.S.ODWR(0,975)`; `=(B5-1)*B6/(B5-1+B13*PIERWIASTEK(2*(B5-1)))`; z minusem dla $T_{*2n}$ |
| 4 | $R\pm z_\gamma\frac{1-R^2}{\sqrt n}$ | $-0{,}65\pm1{,}96\cdot\frac{0{,}5775}{\sqrt{150}}$ | `=B7-B8*(1-B7^2)/PIERWIASTEK(B6)` i `+`; $R$ z danych: `=WSP.KORELACJI(X;Y)` |
| 5 | $U_n$, $A_{1{,}2}=U_n\mp\frac{v_\gamma}{\sqrt{n-3}}$, $T=\frac{e^{2A}-1}{e^{2A}+1}$ | $0{,}4847$; $0{,}1621$ i $0{,}8073$; $0{,}1607$ i $0{,}6681$ | `=1/2*(LN((1+B7)/(1-B7)))`; `=C10-B9/PIERWIASTEK(B6-3)`; `=(EXP(2*B12)-1)/(EXP(2*B12)+1)` lub `=ROZKŁAD.FISHER.ODW(B12)` |

## Dlaczego tak
- **Zad. 1:** żeby $\Delta$ nie przekroczyło $\Delta_0$, przekształcamy nierówność względem $n$. $\sigma$ nieznane, więc $\hat S$ z pilotażu i $t$ zamiast $u$. Słowa-klucze: "wskaźnik precyzji nie większy niż", "minimalna wymagana liczebność".
- **Zad. 2, 3:** $nS^2/\sigma^2$ ma rozkład $\chi^2$, a nie normalny, więc kwantyle bierzemy z $\chi^2$, a przedział nie jest symetryczny. Słowa-klucze: "przedział ufności dla wariancji", "rozkład normalny", "kontrola wariancji".
- **Zad. 3 (duża próba):** dla dużego $n$ rozkład $\chi^2$ przybliżamy normalnym, więc używamy $z$.
- **Zad. 4:** dla dużej próby $R$ ma w przybliżeniu rozkład normalny z odchyleniem $\frac{1-R^2}{\sqrt n}$. Słowa-klucze: "współczynnik korelacji", duże $n$.
- **Zad. 5:** dla małej próby rozkład $R$ jest skośny, więc transformacja Fishera (logarytm) "prostuje" go do rozkładu zbliżonego do normalnego; po policzeniu przedziału wracamy funkcją odwrotną. Słowa-klucze: "współczynnik korelacji", małe $n$.

## Interpretacja
- **Zad. 1:** "Aby wskaźnik precyzji nie przekroczył 15 N przy ufności 95%, trzeba zbadać co najmniej 24 komponenty."
- **Zad. 2:** "Z ufnością 95% wariancja napełniania pojemników mieści się między 12 093 a 35 123."
- **Zad. 3:** "Z ufnością 95% wariancja czasu obsługi wynosi od 6,31 do 10,47 min$^2$ (przybliżenie normalne: 6,39 - 10,69, wynik zbliżony)."
- **Zad. 4:** "Z ufnością 95% współczynnik korelacji między czasem nauki a rozrywki mieści się w (-0,742; -0,558): zależność ujemna i dość silna. Przedział nie zawiera zera."
- **Zad. 5:** "Z ufnością 90% korelacja między odległością a liczbą spóźnień jest dodatnia, od 0,16 do 0,67. Przedział nie zawiera zera, ale jest szeroki, bo $n=29$."

## Pułapki
- **Zad. 2: $S^2$ czy $\hat S^2$?** Arkusz liczy $29\cdot18\,540$, czyli $nS^2$. To poprawne, jeśli 18 540 to $S^2$ (dzielnik $n$), tak jak w treści ("S^2" bez daszka). Gdyby 18 540 było $\hat S^2$ (dzielnik $n-1$), trzeba $28\cdot18\,540$, czyli (11 675,9; 33 912,0). **Sprawdź zapis na egzaminie.** W zad. 3 (S^^2 z daszkiem) użyto poprawnie $121\cdot8$.
- **$c_1$ i $c_2$:** $c_1$ to większy kwantyl (0,975) i daje **dolny** koniec; $c_2$ mniejszy (0,025) daje górny. Łatwo odwrócić.
- **Stopnie swobody:** $\chi^2$ i $t$ mają $n-1$. W zad. 1 stopnie swobody (19) pochodzą z próby pilotażowej ($n=20$), a nie z szukanego $n$; to przybliżenie.
- **Zad. 4: podpisy w arkuszu.** Obie komórki wyników mają etykietę "t2n"; pierwsza to w rzeczywistości $T_{1n}$ (dolna granica). Formuły są poprawne.
- **Zad. 5: układ komórek.** Wartość $U_n$ leży w C10, a jej podpis w A10. $T_{1*n}$ i $T_{2*n}$ policzone dwoma sposobami (kolumna B ręcznie, kolumna C funkcją `ROZKŁAD.FISHER.ODW`), wyniki identyczne (0,16071 i 0,66809).
- **Trzy różne pierwiastki:** $\sqrt{n-3}$ (Fisher), $\sqrt{2(n-1)}$ (wariancja, duża próba), $\sqrt n$ (korelacja, duża próba). Nie mieszać.
- **Przedział korelacji musi leżeć w $[-1;\,1]$.**
- **Zaokrąglaj $n$ w górę** (23,85 -> 24).
