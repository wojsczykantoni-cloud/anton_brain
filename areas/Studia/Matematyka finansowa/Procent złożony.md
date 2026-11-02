---
type: notatka
tags: [studia, matematyka-finansowa, procent-zlozony]
project: ["[[Matematyka finansowa]]"]
people: []
created: 2026-11-02
---
# Procent złożony
Część [[Matematyka finansowa]]. Odsetki doliczane do kapitału, kolejne odsetki liczone od większej kwoty.

## Wzory
| Kapitalizacja | z dołu | z góry |
|---|---|---|
| zgodna (roczna) | Kn = K0*(1+r)^n | Kn = K0*(1-d)^(-n) |
| w podokresach (m razy w roku) | Kn = K0*(1+r/m)^(m*n) | Kn = K0*(1-d/m)^(-m*n) |
| w nadokresach | K(n/m) = K0*(1+m*r)^(n/m) | K(n/m) = K0*(1-m*d)^(-n/m) |

## Szukana wielkość
- stopa: r = (Kn/K0)^(1/n) - 1
- stopa w podokresach: r = m*((Kn/K0)^(1/(m*n)) - 1)
- stopa dyskontowa: d = 1 - (K0/Kn)^(1/n)
- czas: n = LOG(Kn/K0; 1+r) w Excelu

## Kapitalizacja ciągła (poza zakresem kolokwium)
- Kt = K0*e^(delta*t), delta - intensywność oprocentowania
- Zadania (zajęcia 2, zad. 15-19): przyszła wartość, stopa potrojenia, czas wzrostu, kapitał początkowy, zmienne stopy w kolejnych latach

## Typy zadań (zajęcia 2)
- Porównanie procentu prostego i złożonego po 5 latach (zad. 1)
- Wpłaty na początku kolejnych lat, stan konta i odsetki skumulowane (zad. 2, 3)
- Dwa okresy z różnymi stopami, procent należny za dany rok (zad. 4)
- Jaki kapitał utworzy daną kwotę (zad. 5), jaka stopa podwoi kapitał (zad. 6), po ilu latach (zad. 7, 8), jaka stopa (zad. 9, 10)
- Wpłata i wypłata w trakcie, kapitalizacja z dołu i z góry (zad. 11)
- Kapitalizacja półroczna, kwartalna, miesięczna, tygodniowa, dzienna (zad. 12)
- Zmiana kapitalizacji w trakcie lokaty: roczna, półroczna, miesięczna (zad. 13)
- Szukana stopa przy kapitalizacji miesięcznej (zad. 14)
- Dopłata i zmiana kapitalizacji, szukana stopa w drugim okresie (zad. 20, wynik końcowy 38746,71 zł)

## Do uzupełnienia
- Sposób liczenia procentu należnego za wybrany rok (zad. 4)

## Zobacz też
[[Procent prosty]], [[Efektywna i równoważna stopa procentowa]], [[Wzory do kolokwium]]
