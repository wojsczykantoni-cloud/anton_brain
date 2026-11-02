---
type: notatka
tags: [studia, matematyka-finansowa, stopa-efektywna]
project: ["[[Matematyka finansowa]]"]
people: []
created: 2026-11-02
---
# Efektywna i równoważna stopa procentowa
Część [[Matematyka finansowa]]. Pozwala porównać oferty o różnej kapitalizacji.

## Stopa efektywna
| | procentowa | dyskontowa |
|---|---|---|
| proste | ref(n) = r/(1+(n-1)*r) | def(n) = d/(1-(n-1)*d) |
| złożone, zgodna | ref = r | def = d |
| podokresy | ref = (1+r/m)^m - 1 | def = 1 - (1-d/m)^m |
| nadokresy | ref = (1+m*r)^(1/m) - 1 | def = 1 - (1-m*d)^(1/m) |

## Stopa równoważna
| | procentowa | dyskontowa |
|---|---|---|
| proste | r = d/(1-n*d) | d = r/(1+n*r) |
| złożone, zgodna | r = d/(1-d) | d = r/(1+r) |

## Dodatkowe wzory
- Nominalna z efektywnej: r = m*((1+ref)^(1/m) - 1)
- Intensywność oprocentowania: delta = LN(1 + ref)

## Typy zadań (zajęcia 3)
- Efektywna stopa dla różnych kapitalizacji, także dyskontowych i 2-, 3-letnich (zad. 1)
- Równoważna intensywność oprocentowania (zad. 2)
- Nominalna stopa przy efektywnej 4,8% i kapitalizacji kwartalnej (zad. 3)
- Czy dwie oferty są równoważne: półroczna 9% vs miesięczna 1,5% (zad. 4)
- Ranking banków, także z kapitalizacją ciągłą (zad. 5)
- Wybór najlepszego banku z kapitalizacją z dołu i z góry (zad. 6)
- Zmiana kapitalizacji kwartalnej na półroczną lub miesięcznej na kwartalną, nowa stopa (zad. 7, 8)

## Do uzupełnienia
- Stopa nominalna i realna (inflacja): wzoru i zadań brak w materiałach
- Przeciętna stopa procentowa: brak wzoru

## Zobacz też
[[Procent złożony]], [[Wzory do kolokwium]]
