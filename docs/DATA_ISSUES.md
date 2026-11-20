# M1 Dataset Seed Report

Counts after idempotent seed (A-Block only):
- Rooms: 66 (64 parsed CSV rows + 2 M1 additions)
- Official USNs: 342
- Students without USN: 2
- Students per division: CSE-1: 58, CSE-2: 58, CSE-3: 58, CSE-4: 59, CSE-5: 60, CSE-6: 51
- Equipment rows: 129
- Energy baselines: 66
- Room aliases: 54
- Sections: 6
- Division-section mappings: 6
- Holidays: 1

## INFERRED decisions
- A-F2-11: added per M1; floor 2 inferred from ID; name, type, capacity, load, and eligibility remain unspecified (zero/false placeholders).
- A-F2-12: added per M1; floor 2 inferred from ID; name, type, capacity, load, and eligibility remain unspecified (zero/false placeholders).
- A-409: alias is documented against the A-F4-06–10 range; resolved to A-F4-09 from its room number and the floor/room numbering rule.
- 2 admission-number roster entries are not official USNs; NULL USN stored and source identifiers retained in the database.
- 3 explicit master-list addendum records have no gender/batch; those fields remain NULL; divisions are derived from USN sequence.
- CSE division to 5th-semester section mapping is the requested inferred admin-editable mapping: CSE-1->A, CSE-2->B, CSE-3->C, CSE-4->D, CSE-5->E, CSE-6->F.
- CSE-4: roster parser finds 59 assigned student rows but heading declares 58; source memberships preserved without reallocation.
- CSE-5: roster parser finds 60 assigned student rows but heading declares 58; source memberships preserved without reallocation.
- Energy baseline connected loads are calculated from the synthetic equipment wattage rules (not copied from room CSV estimates); for example A-G04 is 0.71 kW in the baseline and 2.5 kW in the room estimate, retained separately.
- Deepavali 2026-11-10: date/name supplied by M1; holiday status is not evidenced in the dataset spec, so tagged INFERRED.

## Provenance
Student roster and division assignments are REAL_DSATM_PDF. Room infrastructure, equipment and energy calculations are SYNTHETIC per the spec. Additional room fields, missing source attributes, and the Deepavali entry supplied by M1 are tagged INFERRED.

M1 roster, room and energy seed report. M2 timetable import results are appended below.

## M2 Timetable Import Report

Counts are parsed from the three timetable datasets; no clash was automatically corrected.
- Sessions per term: 2024-25-EVEN: 115, 2025-26-ODD: 183, 2026-27-ODD: 177
- Sessions per section: 2024-25-EVEN CS-DS: 25, 2024-25-EVEN CS-ICB: 23, 2024-25-EVEN CSE-2: 23, 2024-25-EVEN CSE-4: 21, 2024-25-EVEN CSE-5: 23, 2025-26-ODD A: 29, 2025-26-ODD B: 30, 2025-26-ODD C: 32, 2025-26-ODD D: 30, 2025-26-ODD E: 32, 2025-26-ODD F: 30, 2026-27-ODD A: 29, 2026-27-ODD B: 29, 2026-27-ODD C: 29, 2026-27-ODD D: 30, 2026-27-ODD E: 30, 2026-27-ODD F: 30
- Distinct rooms used by inferred room assignments: 16
- Sessions with an INFERRED room assignment: 323
- Sessions with room_required=False: 58
- Excluded B-Block lab entries: 10
- Conflicts per type: room: 62, faculty: 26, section: 0
- Conflicts per term/type: 2024-25-EVEN faculty: 2, 2025-26-ODD faculty: 16, 2025-26-ODD room: 50, 2026-27-ODD faculty: 8, 2026-27-ODD room: 12
- Room conflicts involving at least one inferred room assignment: 55 (these are provisional pending room confirmation).

### Detected source clashes
- 2026-27-ODD faculty clash on Mon P6: section A `Mon P5-P6 ML LAB (SK, RKP, RS) @ 305 A` and section D `Mon P6 TOC (RKP)`.
- 2026-27-ODD faculty clash on Mon P4: section B `Mon P3-P4 CG LAB / NEXT GEN LAB (B1: MN, AB @ 210 A / B2: AV, LK @ 206 A)` and section D `Mon P4 FCG (AB)`.
- 2026-27-ODD room clash on Mon P3: section B `Mon P3-P4 CG LAB / NEXT GEN LAB (B1: MN, AB @ 210 A / B2: AV, LK @ 206 A)` and section F `Mon P3-P4 CG LAB / NEXT GEN LAB (B1: SD, MS @ 210 A / B2: LK, VI @ 206 A)`.
- 2026-27-ODD room clash on Mon P3: section B `Mon P3-P4 CG LAB / NEXT GEN LAB (B1: MN, AB @ 210 A / B2: AV, LK @ 206 A)` and section F `Mon P3-P4 CG LAB / NEXT GEN LAB (B1: SD, MS @ 210 A / B2: LK, VI @ 206 A)`.
- 2026-27-ODD faculty clash on Mon P3: section B `Mon P3-P4 CG LAB / NEXT GEN LAB (B1: MN, AB @ 210 A / B2: AV, LK @ 206 A)` and section F `Mon P3-P4 CG LAB / NEXT GEN LAB (B1: SD, MS @ 210 A / B2: LK, VI @ 206 A)`.
- 2026-27-ODD room clash on Tue P5: section A `Tue P5 CNS (KS)` and section E `Tue P5 TOC`. [inferred room assignment involved]
- 2026-27-ODD room clash on Wed P5: section A `Wed P5 TOC (SA)` and section E `Wed P5 CNS @ A 202`. [inferred room assignment involved]
- 2026-27-ODD room clash on Wed P6: section A `Wed P6 ML (SHK)` and section E `Wed P6 FCG @ A 202`. [inferred room assignment involved]
- 2026-27-ODD faculty clash on Wed P6: section C `Wed P5-P6 CG LAB / NEXT GEN LAB (B1: AB, RKP @ 210 A / B2: RM, LM @ 206 A)` and section D `Wed P6 TOC (RKP)`.
- 2026-27-ODD room clash on Thu P3: section A `Thu P3 CNS (KS)` and section E `Thu P3 TOC @ A 202`. [inferred room assignment involved]
- 2026-27-ODD room clash on Thu P4: section A `Thu P4 ML (SHK)` and section E `Thu P4 CNS @ A 202`. [inferred room assignment involved]
- 2026-27-ODD faculty clash on Thu P6: section A `Thu P6 FCG (SD)` and section F `Thu P6 FCG @ A 201`.
- 2026-27-ODD room clash on Thu P1: section C `Thu P1-P2 CG LAB / NEXT GEN LAB (B2: AB, SD @ 210 A / B1: RM, LM @ 206 A)` and section F `Thu P1 ML @ A 211`.
- 2026-27-ODD room clash on Thu P2: section C `Thu P1-P2 CG LAB / NEXT GEN LAB (B2: AB, SD @ 210 A / B1: RM, LM @ 206 A)` and section F `Thu P2 CNS @ A 211`.
- 2026-27-ODD faculty clash on Thu P4: section D `Thu P4 CNS (UCR)` and section E `Thu P4 CNS @ A 202`.
- 2026-27-ODD room clash on Thu P6: section D `Thu P6-P7 CG LAB / NEXT GEN LAB (B2: MN, RM @ 210 A / B1: RS, KM @ 206 A)` and section E `Thu P5-P6 CG LAB / NEXT GEN LAB (B2: MS, AL @ 210 A / B1: MA, KSL @ 206 A)`.
- 2026-27-ODD room clash on Thu P6: section D `Thu P6-P7 CG LAB / NEXT GEN LAB (B2: MN, RM @ 210 A / B1: RS, KM @ 206 A)` and section E `Thu P5-P6 CG LAB / NEXT GEN LAB (B2: MS, AL @ 210 A / B1: MA, KSL @ 206 A)`.
- 2026-27-ODD faculty clash on Fri P1: section A `Fri P1-P2 CG LAB / NEXT GEN LAB (B2: SD, KM @ 210 A / B1: KSL, MA @ 206 A)` and section F `Fri P1 FCG @ A 203`.
- 2026-27-ODD faculty clash on Sat P1: section A `Sat P1-P2 PBL-MAD (KDK)` and section B `Sat P1-P2 PBL-MAD (KDK)`.
- 2026-27-ODD room clash on Sat P3: section D `Sat P3-P4 PBL-MAD (DR)` and section F `Sat P3-P4 PBL-MAD (HHN)`. [inferred room assignment involved]
- 2025-26-ODD room clash on Mon P5: section D `Mon P5-P6 DDCO/PYT (B1: MR,DB / B2: VI,SA)` and section F `Mon P5-P6 DDCO/PYT (B1: MR,DB / B2: YG,SA)`. [inferred room assignment involved]
- 2025-26-ODD faculty clash on Mon P5: section D `Mon P5-P6 DDCO/PYT (B1: MR,DB / B2: VI,SA)` and section F `Mon P5-P6 DDCO/PYT (B1: MR,DB / B2: YG,SA)`.
- 2025-26-ODD room clash on Mon P5: section D `Mon P5-P6 DDCO/PYT (B1: MR,DB / B2: VI,SA)` and section F `Mon P5-P6 DDCO/PYT (B1: MR,DB / B2: YG,SA)`. [inferred room assignment involved]
- 2025-26-ODD faculty clash on Mon P5: section D `Mon P5-P6 DDCO/PYT (B1: MR,DB / B2: VI,SA)` and section F `Mon P5-P6 DDCO/PYT (B1: MR,DB / B2: YG,SA)`.
- 2025-26-ODD faculty clash on Tue P3: section A `Tue P3 OS (SM)` and section E `Tue P3 DS (SM)`.
- 2025-26-ODD room clash on Tue P3: section A `Tue P3 OS (SM)` and section F `Tue P3 OS @ 101`. [inferred room assignment involved]
- 2025-26-ODD room clash on Tue P4: section A `Tue P4 DDCO (BV)` and section F `Tue P4 DS @ 101`. [inferred room assignment involved]
- 2025-26-ODD room clash on Tue P5: section A `Tue P5-P6 DDCO/PYT (B1: BV,AV / B2: KS,DHN)` and section B `Tue P5-P6 DDCO/PYT (B1: BV,SB / B2: DB,SA)`. [inferred room assignment involved]
- 2025-26-ODD faculty clash on Tue P5: section A `Tue P5-P6 DDCO/PYT (B1: BV,AV / B2: KS,DHN)` and section B `Tue P5-P6 DDCO/PYT (B1: BV,SB / B2: DB,SA)`.
- 2025-26-ODD room clash on Tue P5: section A `Tue P5-P6 DDCO/PYT (B1: BV,AV / B2: KS,DHN)` and section C `Tue P5-P6 DDCO/PYT (B1: SJK,MA / B2: KS,YG)`. [inferred room assignment involved]
- 2025-26-ODD room clash on Tue P5: section A `Tue P5-P6 DDCO/PYT (B1: BV,AV / B2: KS,DHN)` and section B `Tue P5-P6 DDCO/PYT (B1: BV,SB / B2: DB,SA)`. [inferred room assignment involved]
- 2025-26-ODD room clash on Tue P5: section A `Tue P5-P6 DDCO/PYT (B1: BV,AV / B2: KS,DHN)` and section C `Tue P5-P6 DDCO/PYT (B1: SJK,MA / B2: KS,YG)`. [inferred room assignment involved]
- 2025-26-ODD faculty clash on Tue P5: section A `Tue P5-P6 DDCO/PYT (B1: BV,AV / B2: KS,DHN)` and section C `Tue P5-P6 DDCO/PYT (B1: SJK,MA / B2: KS,YG)`.
- 2025-26-ODD room clash on Tue P5: section B `Tue P5-P6 DDCO/PYT (B1: BV,SB / B2: DB,SA)` and section C `Tue P5-P6 DDCO/PYT (B1: SJK,MA / B2: KS,YG)`. [inferred room assignment involved]
- 2025-26-ODD room clash on Tue P5: section B `Tue P5-P6 DDCO/PYT (B1: BV,SB / B2: DB,SA)` and section C `Tue P5-P6 DDCO/PYT (B1: SJK,MA / B2: KS,YG)`. [inferred room assignment involved]
- 2025-26-ODD faculty clash on Tue P6: section B `Tue P5-P6 DDCO/PYT (B1: BV,SB / B2: DB,SA)` and section D `Tue P6 EDC (SA)`.
- 2025-26-ODD room clash on Wed P6: section B `Wed P5-P6 DS LAB (CG,RM) @ 305 A` and section C `Wed P6-P7 DS LAB (PR,CG) @ 305 A`.
- 2025-26-ODD room clash on Wed P1: section E `Wed P1 DDCO (SJK)` and section F `Wed P1 OS @ 402`. [inferred room assignment involved]
- 2025-26-ODD room clash on Wed P2: section E `Wed P2 MAT (GA)` and section F `Wed P2 EDC @ 402`. [inferred room assignment involved]
- 2025-26-ODD faculty clash on Thu P6: section E `Thu P6 DDCO (SJK)` and section F `Thu P5-P6 DDCO/PYT (B2: MR,SJK / B1: YG)`.
- 2025-26-ODD room clash on Fri P6: section A `Fri P6-P7 DDCO/PYT (B2: BV,AV / B1: KS,SA)` and section B `Fri P6-P7 DDCO/PYT (B2: BV,SB / B1: DB,UKC)`. [inferred room assignment involved]
- 2025-26-ODD faculty clash on Fri P6: section A `Fri P6-P7 DDCO/PYT (B2: BV,AV / B1: KS,SA)` and section B `Fri P6-P7 DDCO/PYT (B2: BV,SB / B1: DB,UKC)`.
- 2025-26-ODD room clash on Fri P6: section A `Fri P6-P7 DDCO/PYT (B2: BV,AV / B1: KS,SA)` and section C `Fri P6-P7 DDCO/PYT (B2: SJK,MA / B1: KS,VI)`. [inferred room assignment involved]
- 2025-26-ODD room clash on Fri P6: section A `Fri P6-P7 DDCO/PYT (B2: BV,AV / B1: KS,SA)` and section D `Fri P5-P6 DDCO/PYT (B2: MR,DB / B1: VI,SA)`. [inferred room assignment involved]
- 2025-26-ODD room clash on Fri P6: section A `Fri P6-P7 DDCO/PYT (B2: BV,AV / B1: KS,SA)` and section E `Fri P5-P6 DDCO/PYT (B2: SJK,DB / B1: SM)`. [inferred room assignment involved]
- 2025-26-ODD room clash on Fri P6: section A `Fri P6-P7 DDCO/PYT (B2: BV,AV / B1: KS,SA)` and section B `Fri P6-P7 DDCO/PYT (B2: BV,SB / B1: DB,UKC)`. [inferred room assignment involved]
- 2025-26-ODD room clash on Fri P6: section A `Fri P6-P7 DDCO/PYT (B2: BV,AV / B1: KS,SA)` and section C `Fri P6-P7 DDCO/PYT (B2: SJK,MA / B1: KS,VI)`. [inferred room assignment involved]
- 2025-26-ODD faculty clash on Fri P6: section A `Fri P6-P7 DDCO/PYT (B2: BV,AV / B1: KS,SA)` and section C `Fri P6-P7 DDCO/PYT (B2: SJK,MA / B1: KS,VI)`.
- 2025-26-ODD room clash on Fri P6: section A `Fri P6-P7 DDCO/PYT (B2: BV,AV / B1: KS,SA)` and section D `Fri P5-P6 DDCO/PYT (B2: MR,DB / B1: VI,SA)`. [inferred room assignment involved]
- 2025-26-ODD faculty clash on Fri P6: section A `Fri P6-P7 DDCO/PYT (B2: BV,AV / B1: KS,SA)` and section D `Fri P5-P6 DDCO/PYT (B2: MR,DB / B1: VI,SA)`.
- 2025-26-ODD room clash on Fri P6: section A `Fri P6-P7 DDCO/PYT (B2: BV,AV / B1: KS,SA)` and section E `Fri P5-P6 DDCO/PYT (B2: SJK,DB / B1: SM)`. [inferred room assignment involved]
- 2025-26-ODD room clash on Fri P6: section B `Fri P6-P7 DDCO/PYT (B2: BV,SB / B1: DB,UKC)` and section C `Fri P6-P7 DDCO/PYT (B2: SJK,MA / B1: KS,VI)`. [inferred room assignment involved]
- 2025-26-ODD room clash on Fri P6: section B `Fri P6-P7 DDCO/PYT (B2: BV,SB / B1: DB,UKC)` and section D `Fri P5-P6 DDCO/PYT (B2: MR,DB / B1: VI,SA)`. [inferred room assignment involved]
- 2025-26-ODD room clash on Fri P6: section B `Fri P6-P7 DDCO/PYT (B2: BV,SB / B1: DB,UKC)` and section E `Fri P5-P6 DDCO/PYT (B2: SJK,DB / B1: SM)`. [inferred room assignment involved]
- 2025-26-ODD room clash on Fri P6: section B `Fri P6-P7 DDCO/PYT (B2: BV,SB / B1: DB,UKC)` and section C `Fri P6-P7 DDCO/PYT (B2: SJK,MA / B1: KS,VI)`. [inferred room assignment involved]
- 2025-26-ODD faculty clash on Fri P6: section B `Fri P6-P7 DDCO/PYT (B2: BV,SB / B1: DB,UKC)` and section D `Fri P5-P6 DDCO/PYT (B2: MR,DB / B1: VI,SA)`.
- 2025-26-ODD room clash on Fri P6: section B `Fri P6-P7 DDCO/PYT (B2: BV,SB / B1: DB,UKC)` and section D `Fri P5-P6 DDCO/PYT (B2: MR,DB / B1: VI,SA)`. [inferred room assignment involved]
- 2025-26-ODD faculty clash on Fri P6: section B `Fri P6-P7 DDCO/PYT (B2: BV,SB / B1: DB,UKC)` and section E `Fri P5-P6 DDCO/PYT (B2: SJK,DB / B1: SM)`.
- 2025-26-ODD room clash on Fri P6: section B `Fri P6-P7 DDCO/PYT (B2: BV,SB / B1: DB,UKC)` and section E `Fri P5-P6 DDCO/PYT (B2: SJK,DB / B1: SM)`. [inferred room assignment involved]
- 2025-26-ODD room clash on Fri P1: section C `Fri P1 DDCO (SJK)` and section F `Fri P1 OS @ 103`. [inferred room assignment involved]
- 2025-26-ODD faculty clash on Fri P2: section C `Fri P2 EDC (SA)` and section D `Fri P2 EDC (SA)`.
- 2025-26-ODD room clash on Fri P2: section C `Fri P2 EDC (SA)` and section F `Fri P2 MAT @ 103`. [inferred room assignment involved]
- 2025-26-ODD room clash on Fri P6: section C `Fri P6-P7 DDCO/PYT (B2: SJK,MA / B1: KS,VI)` and section D `Fri P5-P6 DDCO/PYT (B2: MR,DB / B1: VI,SA)`. [inferred room assignment involved]
- 2025-26-ODD room clash on Fri P6: section C `Fri P6-P7 DDCO/PYT (B2: SJK,MA / B1: KS,VI)` and section E `Fri P5-P6 DDCO/PYT (B2: SJK,DB / B1: SM)`. [inferred room assignment involved]
- 2025-26-ODD faculty clash on Fri P6: section C `Fri P6-P7 DDCO/PYT (B2: SJK,MA / B1: KS,VI)` and section E `Fri P5-P6 DDCO/PYT (B2: SJK,DB / B1: SM)`.
- 2025-26-ODD room clash on Fri P6: section C `Fri P6-P7 DDCO/PYT (B2: SJK,MA / B1: KS,VI)` and section D `Fri P5-P6 DDCO/PYT (B2: MR,DB / B1: VI,SA)`. [inferred room assignment involved]
- 2025-26-ODD faculty clash on Fri P6: section C `Fri P6-P7 DDCO/PYT (B2: SJK,MA / B1: KS,VI)` and section D `Fri P5-P6 DDCO/PYT (B2: MR,DB / B1: VI,SA)`.
- 2025-26-ODD room clash on Fri P6: section C `Fri P6-P7 DDCO/PYT (B2: SJK,MA / B1: KS,VI)` and section E `Fri P5-P6 DDCO/PYT (B2: SJK,DB / B1: SM)`. [inferred room assignment involved]
- 2025-26-ODD room clash on Fri P5: section D `Fri P5-P6 DDCO/PYT (B2: MR,DB / B1: VI,SA)` and section E `Fri P5-P6 DDCO/PYT (B2: SJK,DB / B1: SM)`. [inferred room assignment involved]
- 2025-26-ODD faculty clash on Fri P5: section D `Fri P5-P6 DDCO/PYT (B2: MR,DB / B1: VI,SA)` and section E `Fri P5-P6 DDCO/PYT (B2: SJK,DB / B1: SM)`.
- 2025-26-ODD room clash on Fri P5: section D `Fri P5-P6 DDCO/PYT (B2: MR,DB / B1: VI,SA)` and section E `Fri P5-P6 DDCO/PYT (B2: SJK,DB / B1: SM)`. [inferred room assignment involved]
- 2025-26-ODD room clash on Sat P1: section A `Sat P1-P2 JAVA LAB` and section B `Sat P1-P2 JAVA LAB`. [inferred room assignment involved]
- 2025-26-ODD room clash on Sat P1: section A `Sat P1-P2 JAVA LAB` and section C `Sat P1-P2 JAVA LAB`. [inferred room assignment involved]
- 2025-26-ODD room clash on Sat P1: section A `Sat P1-P2 JAVA LAB` and section D `Sat P1-P2 JAVA LAB`. [inferred room assignment involved]
- 2025-26-ODD room clash on Sat P1: section A `Sat P1-P2 JAVA LAB` and section E `Sat P1-P2 JAVA LAB`. [inferred room assignment involved]
- 2025-26-ODD room clash on Sat P1: section A `Sat P1-P2 JAVA LAB` and section F `Sat P1-P2 JAVA LAB`. [inferred room assignment involved]
- 2025-26-ODD room clash on Sat P1: section B `Sat P1-P2 JAVA LAB` and section C `Sat P1-P2 JAVA LAB`. [inferred room assignment involved]
- 2025-26-ODD room clash on Sat P1: section B `Sat P1-P2 JAVA LAB` and section D `Sat P1-P2 JAVA LAB`. [inferred room assignment involved]
- 2025-26-ODD room clash on Sat P1: section B `Sat P1-P2 JAVA LAB` and section E `Sat P1-P2 JAVA LAB`. [inferred room assignment involved]
- 2025-26-ODD room clash on Sat P1: section B `Sat P1-P2 JAVA LAB` and section F `Sat P1-P2 JAVA LAB`. [inferred room assignment involved]
- 2025-26-ODD room clash on Sat P1: section C `Sat P1-P2 JAVA LAB` and section D `Sat P1-P2 JAVA LAB`. [inferred room assignment involved]
- 2025-26-ODD room clash on Sat P1: section C `Sat P1-P2 JAVA LAB` and section E `Sat P1-P2 JAVA LAB`. [inferred room assignment involved]
- 2025-26-ODD room clash on Sat P1: section C `Sat P1-P2 JAVA LAB` and section F `Sat P1-P2 JAVA LAB`. [inferred room assignment involved]
- 2025-26-ODD room clash on Sat P1: section D `Sat P1-P2 JAVA LAB` and section E `Sat P1-P2 JAVA LAB`. [inferred room assignment involved]
- 2025-26-ODD room clash on Sat P1: section D `Sat P1-P2 JAVA LAB` and section F `Sat P1-P2 JAVA LAB`. [inferred room assignment involved]
- 2025-26-ODD room clash on Sat P1: section E `Sat P1-P2 JAVA LAB` and section F `Sat P1-P2 JAVA LAB`. [inferred room assignment involved]
- 2024-25-EVEN faculty clash on Wed P6: section CS-ICB `Wed P6 KAN (SL)` and section CS-DS `Wed P6 KAN (SL)`.
- 2024-25-EVEN faculty clash on Thu P2: section CSE-4 `Thu P2 CHE (AA)` and section CSE-5 `Thu P2 CHE (AA)`.

### Parser notes
- 2024-25-EVEN has no subject-code catalogue in the source text; source abbreviations are retained as subject codes and marked INFERRED.
