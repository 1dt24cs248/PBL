# PBL - Project Instructions

## Project Overview
PBL is an intelligent campus management and resource optimization system.

## Technology Stack
- Frontend: Flutter and Dart
- Backend: Python and FastAPI
- Database: PostgreSQL
- ORM: SQLAlchemy
- Optimization: Google OR-Tools CP-SAT

## Development Rules

1. Keep the Flutter application inside the existing project root.
2. Keep all Python backend code inside the `backend/` directory.
3. Use REST APIs for communication between Flutter and FastAPI.
4. Enforce authentication and role-based access control on the backend.
5. Never rely only on frontend role restrictions for security.
6. Never use an LLM to make official room-allocation decisions.
7. Use deterministic optimization algorithms for room allocation.
8. The optimizer must generate proposals; it must not directly change official timetable records.
9. Only authorized approval workflows can apply optimization proposals.
10. What-If simulations must never modify official campus records.
11. Add tests for important backend functionality.
12. Never commit passwords, API keys, tokens, or other secrets.
13. Clearly distinguish real, synthetic, simulated, and predicted data.
14. Do not claim research novelty without verified supporting research.

## Important Project Features
- Role-based login
- Student, Faculty, HOD, Admin and Maintenance dashboards
- Room and building management
- Timetable management
- Intelligent classroom allocation
- Maintenance priority based on academic impact
- Maintenance ticket management
- Event and extra-class approval
- What-If campus planning simulator
- 2D campus map

## Coding Guidelines
- Write readable, modular code.
- Avoid unnecessary dependencies.
- Preserve existing working functionality.
- Do not overwrite existing Flutter files without checking them first.
- Explain significant changes and provide testing instructions.

## Scope and Data Rules

- Work only with DSATM A-Block data. Exclude all B-Block rooms, equipment, energy rows, and references.
- Validate official student identifiers against the authoritative roster; admission identifiers are not USNs.
- Treat HOD as a Faculty sub-role, not an administrator. Enforce authorization in the backend.
- Optimizers generate proposals only. Official records change only through authorized approval and version-checked application in one transaction. What-If simulations never modify official records.
- Every seeded row has a provenance status: `REAL_DSATM_PDF`, `SYNTHETIC`, or `INFERRED`. Show provenance in API responses and relevant UI.
- Student names and USNs are personal data. Keep `docs/dataset_spec.md` and `backend/data/real/` out of Git. Keep any hosted repository private or anonymize the roster first.
- Use bcrypt and environment-driven secrets. `Pass@123` is synthetic and development-only.

## Dataset and Conflict Rules

- Use `docs/dataset_spec.md` as the authoritative dataset. Never reconstruct missing data or invent names, USNs, rooms, schedules, or citations.
- Mark undocumented facts `SYNTHETIC` or `INFERRED` and record them in `docs/DATA_ISSUES.md`.
- Follow the documented rules for canonical A-Block room IDs, aliases, timetable periods, batches, no-room sessions, and room inference. Log ambiguous parsing and known conflicts.
- Store subject codes as given in the dataset and preserve known ERP alternatives separately. Seed only the confirmed Deepavali holiday.
- Never model fees, attendance, or internal marks.

## Honesty Rules

1. Never claim code works unless you ran it; label results `tested` or `unverified`.
2. Never invent DSATM data, names, USNs, rooms, schedules or citations. Synthetic data is labelled `SYNTHETIC`; derived data is labelled `INFERRED`.
3. Do not overwrite working code without reading it.
4. Allocation decisions come only from deterministic code or CP-SAT. Any LLM-written text is explanation only.
5. Report solver status honestly, including INFEASIBLE. No silent constraint relaxation.
6. Do not claim research novelty. Energy results are on synthetic wattages and a placeholder tariff and must be described that way.
7. Keep API contracts and DB schema consistent across Flutter, backend and tests; when one changes, update the others in the same commit.
