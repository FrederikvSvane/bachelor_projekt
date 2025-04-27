| Regel nr | Navn | Implementeret? | Scoring |
|----------|------|----------------|---------|
| 1 | Overbooked room in timeslot | Ja | |
| 2 | Overbooked judge (employee) in timeslot | Ja | |
| 3 | Overbooked prosecutor in timeslot | Nej - Vi arbejder ikke med anklagere | |
| 4 | Required room capacity | Nej - Stretch. Vi har ikke room capacity og meeting capacity requirements | |
| 5 | Prosecutor type error | Nej - vi arbejder ikke med anklagere | |
| 6 | Virtual room must have virtual meeting | Ja | |
| 7 | All court meeting to same judge (employee) | Nej - Mødekæder har altid samme dommer i vores løsning pt. | |
| 8 | Skill match | Ja | |
| 9 | Prosecutor skill match | Nej - Vi arbejder ikke med anklagere | |
| 10 | Case type judge (employee) preference | Nej - Vi har ikke nogen prioriteringslister af mødetyper for dommerne | |
| 11 | Case type prosecutor preference | Nej - vi arbejder ikke med anklagere | |
| 12 | Priority block respected | Nej - vi har ikke prioriteret vigtigheder af møder | |
| 13 | Physical case must have physical judge | Nej - vi har fjernet physical attribute fra judge og meetings | |
| 14 | Virtual case must have virtual judge | Ja | |
| 15 | Prioritized employee assigned to prioritized meeting | Nej - vi har ikke nogen måde at prioritere dommere til møder | |
| 16 | Reservation must be different | Nej - what? | |
| 17 | Unused timeblock (39 timegrains) | Nej - could do | |
| 18 | Unused timegrain | Ja | |
| 19 | Case must be assigned specific judge | Ja. Denne er vigtigere end "courtcase not planned all meetings", ie: hvis en sag med 5 møder mangler af få det sidste møde planlagt, vil vi hellere lade det være uplanlagt end at tilskrive det en dommer, som ikke er den samme som har taget de første fire møder | |
| 20 | Max weekly coverage | Ja. Vi sætter en faktor "max_weekly_coverage" på hver dommer, imellem 0 og 100 procent af timegrains om ugen, som angiver hvor mange af de ugentlige timegrains, som dommeren må sidde i møde | |
| 21 | Case not planned all meetings | Ja. En sag bestående af 5 møder skal have alle 5 møder planlagt | |
| 22 | Case time distribution | Nej - could do. Hvis en retssag kræver 5 møder giver det straf at planlægge 2 møder med mere end 1 timeblocks mellemrum | |
| 23 | Planlæg sager i grupper | Nej - stretch. Feks: Alle straffesager, som har samme prioritetsgruppe, skal planlægges sådan at alle sagerne i de højeste prioritetsgrupper kommer før de lave - uanset liggetid. Kun på ugebasis! | |
| 24 | Prioriter sager i specifikke rækkefølger ud fra liggetid | Nej - strech. Efter sorteringen er lavet på baggrund af ovenstående regel, skal alle sagerne i denne pulje placeres efter liggetid, så ældste kommer først | |
| 25 | Room missing video | Nej - could do | |
| 26 | Room missing optional entry | Nej - could do | |
| 27 | Overdue case not planned | Nej - could do. Overdue case er ikke planlagt - giver større penalty end at planlægge så sent som muligt | |
| 28 | Overdue case | Overdue court case, from 0 to 1000 days | |
| 29 | Room stability | Ja | |