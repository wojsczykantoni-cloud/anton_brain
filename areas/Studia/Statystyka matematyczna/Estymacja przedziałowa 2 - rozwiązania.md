---
type: notatka
tags: [statystyka, egzamin, estymacja-przedzialowa, zadania]
project: ["[[Statystyka matematyczna]]"]
people: []
created: 2026-11-10
---
# Estymacja przedziałowa 2 - rozwiązania
#statystyka #egzamin

Plik źródłowy: `Estymacja_przedzia_owa_2_-_rozw.xlsx` (arkusze Zad. 1 - Zad. 5). Wzory: [[Wzory - estymacja]]. Skrót: [[00 Ściąga - Statystyka]]. Poprzednie: [[Estymacja przedziałowa 1 - rozwiązania]].

**Co to za zadania:** minimalna liczebność próby dla przedziału średniej (zad.1), przedział ufności dla **wariancji** (zad.2, 3) i dla **współczynnika korelacji** (zad.4, 5).

| Zad. | Dane | Szukamy |
|---|---|---|
| 1 | delta0 = 15 N, gamma = 0,95, Shat = 35 N z próby n = 20 | min. n (sigma nieznane) |
| 2 | n = 29, S2 = 18 540, gamma = 0,95, rozkład normalny | przedział dla wariancji (chi2) |
| 3 | n = 122, S2hat = 8, gamma = 0,95, rozkład normalny | przedział dla wariancji: dokładny i duża próba |
| 4 | n = 150, R = -0,65, gamma = 0,95 | przedział dla korelacji (duża próba) |
| 5 | n = 29, R = 0,45, gamma = 0,90 | przedział dla korelacji (Fisher) |

## Rozwiązanie krok po kroku

### Zad. 1
1. Warunek: delta = t_gamma * Shat / pierwiastek(n) <= delta0 = 15, sigma nieznane.
2. t_gamma = T.INV(0,975; 19) = **2,0930** (19 = 20 - 1 stopni swobody z próby pilotażowej).
3. n >= Shat^2 * t_gamma^2 / delta0^2 = 35^2 * 2,0930^2 / 15^2 = 1225 * 4,3807 / 225 = **23,85**.
4. Zaokrąglamy w górę: **n = 24**.

### Zad. 2
1. n = 29, stopnie swobody n-1 = 28. S2 = 18 540 (zapis "S^2" bez daszka, więc wariancja z dzielnikiem n: licznik n * S2).
2. c1 = kwantyl chi2(28) rzędu 0,975 = **44,4608**; c2 = kwantyl rzędu 0,025 = **15,3079**.
3. T1n = n * S2 / c1 = 29 * 18 540 / 44,4608 = **12 092,90**.
4. T2n = n * S2 / c2 = 29 * 18 540 / 15,3079 = **35 123,13**.
5. Przedział dla wariancji: **(12 092,9; 35 123,1)**.

### Zad. 3
Dokładnie (chi2):
1. n = 122, n-1 = 121, c1 = chi2(121; 0,975) = **153,3379**, c2 = chi2(121; 0,025) = **92,4462**.
2. T1n = 121 * 8 / 153,3379 = **6,3129**; T2n = 121 * 8 / 92,4462 = **10,4710**. Przedział: **(6,31; 10,47)**.

Duża próba (przybliżenie normalne):
3. z_gamma = **1,9600**; pierwiastek(2 * 121) = 15,5563; z * pierwiastek(...) = 30,4899.
4. T1* = 121 * 8 / (121 + 30,4899) = 968 / 151,4899 = **6,3899**.
5. T2* = 968 / (121 - 30,4899) = 968 / 90,5101 = **10,6949**. Przedział: **(6,39; 10,69)**.

### Zad. 4
1. R = -0,65, 1 - R^2 = 1 - 0,4225 = **0,5775**.
2. z_gamma = **1,9600**; błąd = z * (1 - R^2) / pierwiastek(n) = 1,96 * 0,5775 / pierwiastek(150) = 1,96 * 0,5775 / 12,2474 = **0,0924**.
3. T1 = -0,65 - 0,0924 = **-0,7424**; T2 = -0,65 + 0,0924 = **-0,5576**.
4. Przedział dla korelacji: **(-0,7424; -0,5576)**.

### Zad. 5
1. n = 29 (mała próba), R = 0,45, gamma = 0,90: v_gamma = kwantyl N(0,1) rzędu 0,95 = **1,6449**.
2. un = (1/2) * ln((1 + 0,45)/(1 - 0,45)) = (1/2) * ln(2,6364) = **0,4847**.
3. v / pierwiastek(n-3) = 1,6449 / pierwiastek(26) = **0,3226**.
4. A1 = 0,4847 - 0,3226 = **0,1621**; A2 = 0,4847 + 0,3226 = **0,8073**.
5. T1 = (e^(2*A1) - 1)/(e^(2*A1) + 1) = **0,1607**; T2 = (e^(2*A2) - 1)/(e^(2*A2) + 1) = **0,6681**.
6. Przedział dla korelacji: **(0,1607; 0,6681)**.

## Wzory
Legenda: [[Wzory - estymacja#Niezbędna liczebność próby]], [[Wzory - estymacja#Przedział dla wariancji]], [[Wzory - estymacja#Przedział dla korelacji]].

**Zad. 1 (min. n, sigma nieznane)**
- ogólny: `n >= Shat^2 * t_gamma^2 / delta0^2` (z `Shat/pierwiastek(n) * t_gamma <= delta0`)
- z liczbami: `35^2 * 2,0930^2 / 15^2 = 23,85 -> 24`
- Excel PL: `B9 = ROZKŁ.T.ODWR(0,975;19)` (w pliku `T.INV(0,975;19)`); `B10: =B8^2*B9^2/B6^2`; `B11: =ZAOKR.W.GÓRĘ(B10;0)`

**Zad. 2 (wariancja, chi2)**
- ogólny: `T1n = n*S2/c1`, `T2n = n*S2/c2` (= `(n-1)*S2hat/c`)
- z liczbami: `29*18540/44,4608 = 12092,90`, `29*18540/15,3079 = 35123,13`
- Excel PL: `c1: =ROZKŁ.CHI.ODWR(0,975;28)` (w pliku `CHISQ.INV(0,975;28)`), `c2: =ROZKŁ.CHI.ODWR(0,025;28)`, `T1n: =29*B7/B8`, `T2n: =29*B7/B9`

**Zad. 3 (wariancja: dokładnie i duża próba)**
- ogólny: `T1n = (n-1)*S2hat/c1`, `T2n = (n-1)*S2hat/c2`; duża próba: `T1* = (n-1)*S2hat/(n-1 + z*pierwiastek(2(n-1)))`, `T2* = (n-1)*S2hat/(n-1 - z*pierwiastek(2(n-1)))`
- z liczbami: `121*8/153,3379 = 6,3129`, `121*8/92,4462 = 10,4710`; duża próba: `968/(121+30,4899) = 6,3899`, `968/(121-30,4899) = 10,6949`
- Excel PL: `=121*B6/B7`, `=121*B6/B8`, `z: =ROZKŁ.NORMALNY.S.ODWR(0,975)`, `=(B5-1)*B6/(B5-1+B13*PIERWIASTEK(2*(B5-1)))`, `=(B5-1)*B6/(B5-1-B13*PIERWIASTEK(2*(B5-1)))`

**Zad. 4 (korelacja, duża próba)**
- ogólny: `R +- z_gamma * (1 - R^2) / pierwiastek(n)`
- z liczbami: `-0,65 +- 1,96 * 0,5775 / pierwiastek(150) = -0,65 +- 0,0924`
- Excel PL: `=B7-B8*(1-B7^2)/PIERWIASTEK(B6)` i `=B7+B8*(1-B7^2)/PIERWIASTEK(B6)`; R z danych policzysz `=WSP.KORELACJI(X;Y)`

**Zad. 5 (korelacja, Fisher)**
- ogólny: `un = (1/2)*ln((1+R)/(1-R))`, `A1,2 = un -+ v/pierwiastek(n-3)`, `T = (e^(2A) - 1)/(e^(2A) + 1)`
- z liczbami: `un = 0,4847`, `A1 = 0,1621`, `A2 = 0,8073`, `T1 = 0,1607`, `T2 = 0,6681`
- Excel PL: `un: =1/2*(LN((1+B7)/(1-B7)))`, `A1: =C10-B9/PIERWIASTEK(B6-3)`, `A2: =C10+B9/PIERWIASTEK(B6-3)`, `T1: =(EXP(2*B12)-1)/(EXP(2*B12)+1)` lub `=ROZKŁAD.FISHER.ODW(B12)` (w pliku `FISHERINV`)

## Dlaczego tak
- **Zad. 1:** żeby delta nie przekroczyła delta0, przekształcamy nierówność względem n; sigma nieznane, więc Shat z pilotażu i t (zamiast u). Słowa-klucze: "wskaźnik precyzji nie większy niż", "minimalna wymagana liczebność".
- **Zad. 2, 3:** n*S2/sigma^2 ma rozkład chi2 (n-1 stopni swobody), a nie normalny, więc kwantyle bierzemy z chi2; przedział jest niesymetryczny. Słowa-klucze: "przedział ufności dla wariancji", "rozkład normalny", "kontrola wariancji".
- **Zad. 3 (duża próba):** dla dużego n chi2 przybliżamy normalnym, więc używamy z. Słowo-klucz: n = 122.
- **Zad. 4:** dla dużej próby R ma w przybliżeniu rozkład normalny z odch. std. (1-R^2)/pierwiastek(n). Słowa-klucze: "współczynnik korelacji", duże n, "rozkład normalny cech".
- **Zad. 5:** dla małej próby rozkład R jest skośny, więc transformacja Fishera (ln) "wyprostowuje" go do rozkładu zbliżonego do normalnego; po policzeniu przedziału wracamy funkcją odwrotną. Słowa-klucze: "współczynnik korelacji", mała próba (n = 29).

## Interpretacja
- **Zad. 1:** "Aby wskaźnik precyzji nie przekroczył 15 N przy ufności 95%, trzeba zbadać co najmniej 24 komponenty."
- **Zad. 2:** "Z ufnością 95% wariancja napełniania pojemników mieści się między 12 093 a 35 123."
- **Zad. 3:** "Z ufnością 95% wariancja czasu obsługi wynosi od 6,31 do 10,47 min^2 (z przybliżenia normalnego 6,39 - 10,69, wynik zbliżony)."
- **Zad. 4:** "Z ufnością 95% współczynnik korelacji między czasem nauki a rozrywki mieści się w (-0,742; -0,558): ujemna, dość silna zależność. Przedział nie zawiera zera."
- **Zad. 5:** "Z ufnością 90% korelacja między odległością a liczbą spóźnień jest dodatnia, od 0,16 do 0,67 (przedział nie zawiera zera, ale jest szeroki, bo n = 29)."

## Pułapki
- **Zad. 2: S2 czy S2hat?** W arkuszu użyto `29 * 18540 / c` (nS2). To poprawne, jeśli 18 540 to S2 (dzielnik n), tak jak w treści ("S^2" bez daszka). Gdyby 18 540 było S2hat (dzielnik n-1), trzeba `28 * 18540 / c`, czyli (11 675,9; 33 912,0). **Sprawdź zapis na egzaminie** (S2 kontra S2hat). W Zad.3 (S^^2 z daszkiem) użyto poprawnie `121 * 8` (n-1).
- **c1 i c2:** c1 to większy kwantyl (0,975) i daje dolny koniec T1n; c2 mniejszy (0,025) daje górny koniec. Łatwo odwrócić.
- **Stopnie swobody:** chi2 i t mają n-1 stopni swobody. W Zad. 1 df = 19 pochodzi z próby pilotażowej (n = 20), a nie z szukanego n (to przybliżenie).
- **Zad. 4: etykiety w arkuszu:** B9 i B10 obie mają etykietę "t2n"; B9 to w rzeczywistości **T1n** (dolna granica). Formuły są poprawne.
- **Zad. 5: układ komórek:** wartość u_n leży w C10, a etykieta w A10; T1 i T2 policzone dwoma sposobami (kol. B ręcznie, kol. C `FISHERINV`), wyniki identyczne (T1 = 0,16071, T2 = 0,66809).
- **n-3 (Fisher) kontra n-1 (chi2) kontra n (korelacja, duża próba):** trzy różne pierwiastki w mianownikach, nie mieszać.
- **Przedział korelacji musi leżeć w [-1; 1].**
- **Zaokrąglaj n w górę** (23,85 -> 24).
