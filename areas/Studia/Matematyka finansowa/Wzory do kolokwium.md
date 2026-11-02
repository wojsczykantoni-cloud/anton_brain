---
type: notatka
tags: [studia, matematyka-finansowa, wzory, kolokwium]
project: ["[[Matematyka finansowa]]"]
people: []
created: 2026-11-02
---
# Wzory do kolokwium
Podsumowanie wszystkich wzorów z [[Matematyka finansowa]]. Kolokwium: 4.11.2026, 4 krótkie zadania, wzory dozwolone.
Oznaczenia: K0 - kapitał początkowy, Kn - wartość końcowa, n - czas w latach, r - stopa procentowa, d - stopa dyskontowa, m - liczba kapitalizacji w roku, I = Kn - K0 - odsetki.

## 1. Rachunek czasu
Szczegóły: [[Rachunek czasu]]
| Reguła | N (liczba lat) |
|---|---|
| dokładna | dokładna liczba dni / rzeczywista liczba dni w roku |
| księgowa | dokładna liczba dni / 365 |
| przybliżona | przybliżona liczba dni / 365 |
| bankowa | dokładna liczba dni / 360 |
| zwykła | przybliżona liczba dni / 360 |

- Dokładna liczba dni = data końcowa - data początkowa (Excel: zwykłe odejmowanie).
- Przybliżona liczba dni = funkcja DNI.360.

## 2. Oprocentowanie proste
Szczegóły: [[Procent prosty]]
- z dołu: Kn = K0*(1 + n*r)
- z góry: Kn = K0*(1 - n*d)^(-1)
- r = (Kn - K0)/(n*K0)
- d = (Kn - K0)/(n*Kn)

## 3. Oprocentowanie złożone
Szczegóły: [[Procent złożony]] (w tym kapitalizacja ciągła)
| Kapitalizacja | z dołu | z góry |
|---|---|---|
| zgodna | Kn = K0*(1+r)^n | Kn = K0*(1-d)^(-n) |
| w podokresach | Kn = K0*(1+r/m)^(m*n) | Kn = K0*(1-d/m)^(-m*n) |
| w nadokresach | K(n/m) = K0*(1+m*r)^(n/m) | K(n/m) = K0*(1-m*d)^(-n/m) |
| ciągła | Kt = K0*e^(delta*t) | |

Przekształcenia:
- r = (Kn/K0)^(1/n) - 1
- r (podokresy) = m*((Kn/K0)^(1/(m*n)) - 1)
- d = 1 - (K0/Kn)^(1/n)
- n = LOG(Kn/K0; 1+r) (Excel), czyli log o podstawie (1+r) z Kn/K0
- K0 = Kn*(1+r)^(-n)

## 4. Stopa efektywna i równoważna
Szczegóły: [[Efektywna i równoważna stopa procentowa]]
| Efektywna | procentowa | dyskontowa |
|---|---|---|
| proste | ref(n) = r/(1+(n-1)*r) | def(n) = d/(1-(n-1)*d) |
| złożone, zgodna | ref = r | def = d |
| podokresy | ref = (1+r/m)^m - 1 | def = 1 - (1-d/m)^m |
| nadokresy | ref = (1+m*r)^(1/m) - 1 | def = 1 - (1-m*d)^(1/m) |

| Równoważna | procentowa | dyskontowa |
|---|---|---|
| proste | r = d/(1-n*d) | d = r/(1+n*r) |
| złożone, zgodna | r = d/(1-d) | d = r/(1+r) |

- Nominalna z efektywnej: r = m*((1+ref)^(1/m) - 1)
- Intensywność: delta = LN(1 + ref)

## 5. Stopa nominalna i realna
Do uzupełnienia: wzoru nie było w materiałach (wpisz z zajęć).

## 6. Pułapki i kolejność działań
1. Najpierw okres: daty na n (reguła z polecenia), potem sprawdź jednostkę stopy (rok, półrocze, miesiąc).
2. Z dołu (r) czy z góry (d)? To inny wzór.
3. Kapitalizacja częstsza niż roczna: m w wykładniku, r/m w nawiasie.
4. Zmiana stopy lub wpłata w trakcie: licz etapami, wartość końcowa etapu to kapitał początkowy następnego.
5. Szukasz r: Kn/K0; szukasz d: K0/Kn (odwrotnie). Potem pierwiastek.
6. Odsetki skumulowane = Kn - suma wpłat. Wypłata pomniejsza kapitał w momencie wypłaty.
7. Stopa jako ułamek (3,5% = 0,035). Zaokrąglaj dopiero na końcu.

PDF do wydruku: "Wzory - Matematyka finansowa.pdf" (wrzuć obok tej notatki).
