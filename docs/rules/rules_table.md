# Scoring Rules - National Court Administration

## Overview
Reglerne er opdelt i følgende kategorier med forskellige penalty ranges:
- **Double use of resources = Hard [1000:100.000]** - Overbooking af ressourcer
- **Structural conflicts = Hard [0:1000]** - Strukturelle konflikter der gør planlægning umulig
- **Impractical conflicts = Hard [0:1000]** - Konflikter der gør planlægning upraktisk
- **Time usage = Soft [0:342]** - Tidsforbrug og optimering
- **Business priorities = Soft [2000:8000]** - Forretningsmæssige prioriteter
- **Planning heuristics = Soft [100:1200]** - Planlægningsheuristikker
- **Employee preferences = Soft [0:100]** - Medarbejderpræferencer

## Scoring Formel
Score = Offset + (Step × Overtrædelses_Antal)

Hvor:
- **Offset**: Grundpenalty for første overtrædelse
- **Step**: Ekstra penalty for hver yderligere overtrædelse
- **M:n**: Multiplikator og enhed (H=Hard penalty multiplier, S=Soft penalty multiplier, M=Minute penalty)
- **Range**: Min-max range for total penalty

## Detaljerede Regler

| Regel nr | Navn | Implementeret? | Kategori | Offset | Step | M:n | Range | Beskrivelse |
|----------|------|----------------|----------|--------|------|-----|-------|-------------|
| **1** | OVERBOOKED_ROOM_IN_TIME_BLOCK | Ja | Double use of resources | 1000 | 20 | 1H | [1020,73420] | Et lokale kan ikke dobbeltbookes. Penalty øges med 20 for hver ekstra overbooking i samme tidsblok |
| **2** | OVERBOOKED_EMPLOYEE_IN_TIME_BLOCK | Ja | Double use of resources | 1000 | 10 | 1H | [1010,73410] | En dommer kan ikke dobbeltbookes. Penalty øges med 10 for hver ekstra overbooking |
| **3** | OVERBOOKED_PROSECUTOR_IN_TIME_BLOCK | Nej - Vi arbejder ikke med anklagere | Double use of resources | 1000 | 0 | 1H | [1000,73400] | Anklager overbooking |
| **4** | REQUIRED_ROOM_CAPACITY | Nej - Stretch | Structural conflicts | 50 | 0 | 1H | [50-150] | Lokalet skal have plads til alle obligatoriske deltagere |
| **5** | PROSECUTOR_TYPE_ERROR | Nej - Vi arbejder ikke med anklagere | Structural conflicts | 0 | 0 | 56H | {56} | Civilsager må ikke have anklagere |
| **6** | VIRTUAL_ROOM_MUST_HAVE_VIRTUAL_MEETING | Ja | Structural conflicts | 0 | 0 | 55H | {55} | Virtuelle lokaler skal have virtuelle møder |
| **7** | ALL_COURT_MEETING_TO_SAME_EMPLOYEE | Nej - Automatisk opfyldt | Structural conflicts | 50 | 1 | 1H | [50-100] | Alle møder i en sag skal have samme dommer |
| **8** | SKILL_MATCH | Ja | Structural conflicts | 0 | 0 | 54H | {54} | Dommers skills skal matche sagens krav |
| **9** | PROSECUTOR_SKILL_MATCH | Nej - Vi arbejder ikke med anklagere | Structural conflicts | 0 | 0 | 53H | {53} | Anklagers skills skal matche |
| **10** | CASE_TYPE_ALLOCATION_NOT_ALLOWED_EMP | Nej - Ingen præferencer | Structural conflicts | 0 | 0 | 52H | {52} | Dommer skal følge workpreferences |
| **11** | CASE_TYPE_ALLOCATION_NOT_ALLOWED_PRO | Nej - Vi arbejder ikke med anklagere | Structural conflicts | 0 | 0 | 51H | {51} | Anklager skal følge workpreferences |
| **12** | PRIORITY_EMPLOYEE_HAS_UNPRIORITIES_MEETING | Nej - Ingen prioritering | Structural conflicts | 0 | 0 | 50H | {50} | Prioriterede anklagere skal have prioriterede møder |
| **13** | PRIORITY_BLOCK_USED_TO_EARLY | Nej - Ingen prioritering | Structural conflicts | 0 | 0 | 1H | [0-1000] | Møder prioriteret efter bestemt dato må ikke ligge for tidligt |
| **14** | NORMAL_CASE_MUST_HAVE_NORMAL_EMPLOYEE | Nej - Vi har fjernet physical attribute | Impractical conflicts | 0 | 0 | 10H | {10} | Normale sager skal have normale dommere |
| **15** | PRIORITY_EMPLOYEE_HAS_UNPRIORITIES_MEETING (duplikat) | Nej | Impractical conflicts | 0 | 0 | 2H | {2} | Prioriterede ressourcer til prioriterede møder |
| **16** | VIRTUAL_CASE_MUST_HAVE_VIRTUAL_EMPLOYEE | Ja | Impractical conflicts | 0 | 0 | 1H | {1} | Virtuelle sager skal have virtuelle dommere |
| **17** | RESERVATIONS_MUST_BE_DIFFERENT | Nej - Uklart formål | Impractical conflicts | 0 | 0 | 1H | [0-59] | Reservationer må ikke overlappe (max 60 reservationer) |
| **18** | UNUSED_TIME_BLOCK | Nej - Could do | Time usage | 0 | 0 | 36M/342M | {0-36}/{0-342} | Penalty for helt ubrugte timeblocks. Kan bruge simpel (36M) eller progressiv scoring (342M) |
| **19** | UNUSED_TIME_GRAIN | Ja | Time usage | 0/1/0 | 0 | 1M | [0-340] | Penalty for ubrugte timegrains. Tre varianter: simpel, offset+1, eller progressiv S(X)=342-X*((X/2)+1)/2 |
| **20** | CASE_MUST_BE_ASSIGNED_SPECIFIC_EMPLOYEE | Ja | Business priorities | 6550 | 0 | 1S | {6550} | Sager tildelt specifik dommer SKAL have den dommer |
| **21** | MAX_WEEKLY_COVERAGE | Ja | Business priorities | 6550 | 0 | 10S | [6550-7550] | Dommere må ikke overskride deres max coverage (0-100%) |
| **22** | COURTCASE_NOT_PLANNED_ALL_MEETINGS | Ja | Business priorities | 4000 | 0 | 1S | [4000-6550] | Alle møder i en sag skal planlægges. Progressiv scoring: 2550-X*((X/2)+1)/2 hvor X er % manglende møder |
| **23** | CASE_TYPE_TIME_DISTRIBUTION | Nej - Could do | Business priorities | 2000 | 0 | 1S | [2000-4000] | Møder må ikke ligge for spredt (max 2000 timeblocks = 1000 dage) |
| **24** | Prioriter sager i grupper | Nej - Stretch | Business priorities | 200 | 22500 | 500S | {23000} | Sager i højere prioritetsgrupper skal komme før lavere (>4 dages forskel) |
| **25** | Prioriter sager efter liggetid | Nej - Stretch | Business priorities | ? | 0 | 1S | [0-22500] | Ældre sager skal komme før nyere inden for samme gruppe. Scoring: (planlagt_dato - oprettet_dato)² |
| **26** | ROOM_MISSING_VIDEO4 | Nej - Could do | Planning heuristics | 200 | 0 | 200S | {400} | Lokale mangler video4 udstyr |
| **27** | ROOM_MISSING_OPTIONAL_ENTRY | Nej - Could do | Planning heuristics | 200 | 0 | 100S | {300} | Lokale mangler valgfri indgang (f.eks. vidneindgang) |
| **28** | OVER_DUE_CASE_NOT_PLANNED | Nej - Could do | Planning heuristics | 200 | 0 | 1S | {1200} | Overdue sag er slet ikke planlagt (værre end at planlægge sent) |
| **29** | OVER_DUE_COURT_CASE | Nej - Could do | Planning heuristics | 200 | 0 | 1S | [200,1200] | Sag er forsinket 0-1000 dage |
| **30** | ROOM_STABILITY | Ja | Employee preferences | 0 | 0 | 1S | [0,60] | Antal ekstra lokaler ud over det første på en dag (max 60) |

## Fortolkningsnoter

### Progressiv Scoring for UNUSED_TIME_GRAIN
Der foreslås tre varianter:
1. **Simpel**: Alle timegrains vægtes ens (sort i dokumentet)
2. **Offset variant**: Første 2-grain møde fjerner kun 1 penalty, sidste 2-grain møde fjerner 3 (orange)
3. **Progressiv**: S(X) = 342 - X*((X/2)+1)/2 hvor X er antal brugte grains (grøn)

### Progressiv Scoring for COURTCASE_NOT_PLANNED_ALL_MEETINGS
For at skelne mellem næsten færdige sager og nye sager:
- Beregnes som % af manglende møder
- S(X) = 2550 - X*((X/2)+1)/2 hvor X er % manglende møder
- S(100%) = 2550 (alle møder mangler)
- S(0%) = 0 (alle møder planlagt)

### Prioritetsgrupper vs Liggetid
To sammenhængende regler der skal implementeres sammen:
1. Sager i højere prioritetsgrupper skal altid komme før lavere grupper
2. Inden for samme gruppe skal ældre sager komme først (med 5 dages fleksibilitet)