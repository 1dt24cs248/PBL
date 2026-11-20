# M1 Dataset Seed Report

Counts after idempotent seed (A-Block only):
- Rooms: 66 (64 parsed CSV rows + 2 M1 additions)
- Official USNs: 342
- Students without USN: 2
- Students per division: CSE-1: 58, CSE-2: 58, CSE-3: 58, CSE-4: 59, CSE-5: 60, CSE-6: 51
- Equipment rows: 129
- Energy baselines: 66
- Room aliases: 5
- Sections: 6
- Division-section mappings: 344
- Holidays: 1

## INFERRED decisions
- A-F2-11: added per M1; floor 2 inferred from ID; name, type, capacity, load, and eligibility remain unspecified (zero/false placeholders).
- A-F2-12: added per M1; floor 2 inferred from ID; name, type, capacity, load, and eligibility remain unspecified (zero/false placeholders).
- A-409: alias is documented against the A-F4-06–10 range; assigned to A-F4-06 as the first room in that range.
- 24UGDT1805-CS1: admission number is not a USN; student stored with NULL USN and source_identifier preserved.
- 24UGDT0186-CS1: admission number is not a USN; student stored with NULL USN and source_identifier preserved.
- 1DT24CS198 PRITHVINATH A: explicit master-list addendum has no gender/batch; those fields remain NULL; division derived from USN sequence (CSE-4).
- 1DT24CS239 SANJANA LN: explicit master-list addendum has no gender/batch; those fields remain NULL; division derived from USN sequence (CSE-5).
- 1DT24CS272 SIDDHARTHA HEGDE MS: explicit master-list addendum has no gender/batch; those fields remain NULL; division derived from USN sequence (CSE-5).
- CSE-4: roster parser finds 59 assigned student rows but heading declares 58; source memberships preserved without reallocation.
- CSE-5: roster parser finds 60 assigned student rows but heading declares 58; source memberships preserved without reallocation.
- Energy baseline connected loads are calculated from the synthetic equipment wattage rules (not copied from room CSV estimates); for example A-G04 is 0.71 kW in the baseline and 2.5 kW in the room estimate, retained separately.
- Deepavali 2026-11-10: date/name supplied by M1; holiday status is not evidenced in the dataset spec, so tagged INFERRED.

## Provenance
Student roster and division assignments are REAL_DSATM_PDF. Room infrastructure, equipment and energy calculations are SYNTHETIC per the spec. Additional room fields, missing source attributes, and the Deepavali entry supplied by M1 are tagged INFERRED.

No timetable sessions were seeded (M2 scope).
