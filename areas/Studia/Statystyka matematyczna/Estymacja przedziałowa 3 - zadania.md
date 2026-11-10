---
type: notatka
tags: [statystyka, egzamin, estymacja-przedzialowa, zadania]
project: ["[[Statystyka matematyczna]]"]
people: []
created: 2026-11-10
---
# Estymacja przedziałowa 3 - zadania
#statystyka #egzamin

Plik źródłowy: `Estymacja_przedzia_owa_3.xlsx` (arkusze Zad. 1, Zad. 2). To wersja robocza tych samych zadań, co w [[Estymacja przedziałowa 3 - rozwiązania]]. Różnice: Zad.1 ma dodatkowo kolumnę **"bezkorekt"** (przedział bez poprawki na skończoność populacji), a Zad.2 ma **tylko treść** (bez obliczeń; rozwiązanie w pliku z rozwiązaniami: 333). Wzory: [[Wzory - estymacja]]. Skrót: [[00 Ściąga - Statystyka]].

**Co to za zadanie:** Zad.1: przedział dla frakcji z N = 500, n = 100 (bezzwrotnie), k = 40, gamma = 0,95. Zad.2: min. n dla N = 1000, delta0 = 0,05, gamma = 0,99, phat = 0,25 (bezzwrotnie). Dane i opis jak w [[Estymacja przedziałowa 3 - rozwiązania]].

## Rozwiązanie krok po kroku

### Zad.1 (z porównaniem)
1. phat = 40 / 100 = **0,4**; z_gamma = **1,9600**.
2. Z poprawką (bezzwrotnie): przedział **(0,3140; 0,4860)** (E6, E7), delta = **0,0860**.
3. Bez poprawki (kolumna "bezkorekt", G6, G7): błąd = 1,96 * pierwiastek(0,4 * 0,6 / 100) = 1,96 * 0,04899 = **0,0960**; przedział **(0,3040; 0,4960)**.
4. Porównanie: z poprawką przedział jest węższy (0,172 kontra 0,192 długości), bo losujemy bez zwracania 20% populacji.
5. wdelta: z poprawką 0,0860 / 0,4 = **0,2149** (21,5%); bez poprawki 0,0960 / 0,4 = **0,2400** (24,0%) (policzone przeze mnie, w arkuszu nie ma).

### Zad.2
Tylko treść w arkuszu. Wynik **n = 333**, rozwiązanie krok po kroku: [[Estymacja przedziałowa 3 - rozwiązania#Zad. 2]].

## Wzory
Ogólne: [[Wzory - estymacja#Przedział dla frakcji]].

- z poprawką, ogólny: `phat +- z * pierwiastek( (N-n)/((N-1)*n) * phat(1-phat) )`; z liczbami: `0,4 +- 1,96 * pierwiastek(400/(499*100)*0,24) = 0,4 +- 0,0860`; Excel PL: `=B9-E5*PIERWIASTEK((B8-B6)/((B8-1)*B6)*(B9*(1-B9)))`
- bez poprawki, ogólny: `phat +- z * pierwiastek( phat(1-phat)/n )`; z liczbami: `0,4 +- 1,96 * pierwiastek(0,24/100) = 0,4 +- 0,0960`; Excel PL: `=B9-E5*PIERWIASTEK(B9*(1-B9)/B6)` (kol. G)
- phat: `=B7/B6`; z: `=ROZKŁ.NORMALNY.S.ODWR(0,975)`

## Dlaczego tak
Kolumna "bezkorekt" pokazuje, ile daje poprawka na skończoność populacji: przy losowaniu bez zwracania i dużym udziale próby w populacji (n/N = 20%) przedział ma być węższy. Słowa-klucze w treści: "bezzwrotnie" / "bez zwracania".

## Interpretacja
"Uwzględnienie faktu, że próba to 20% populacji, skraca przedział ufności z 0,304 - 0,496 do 0,314 - 0,486, czyli zwiększa precyzję oszacowania udziału zadowolonych pracowników."

## Pułapki
- Etykieta w arkuszu: "gammna" (literówka) w A5; "bezkorekt" i "bezzwrotna" to tylko notatki autora.
- Mylenie wersji: z poprawką (bezzwrotnie z N) kontra bez poprawki (zwrotnie lub N bardzo duże).
- Zad.2 nie ma obliczeń w tym pliku, wynik bierz z notatki z rozwiązaniami.
