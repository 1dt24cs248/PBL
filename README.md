# pbl

## Data privacy

The official dataset includes student names and USNs. Keep the GitHub repository
private, or anonymize the roster before publishing it. The local dataset
specification, source PDFs, and `backend/data/real/` files are excluded from Git.

A new Flutter project.

## Synthetic development accounts

The local seed creates these synthetic development accounts, all using the
development-only password `Pass@123`:

- `admin1` — admin
- `maint1` — maintenance
- `hod_cse` — HOD
- `fac1` — teaching faculty
- `stu1` — synthetic student
- Student roster accounts are keyed by USN and selected through the configurable
  `DEMO_STUDENT_USNS` setting. The default roster account list is kept out of
  tracked documentation to avoid publishing student identifiers.

Do not use this shared password outside local development or tests.

## Getting Started

This project is a starting point for a Flutter application.

A few resources to get you started if this is your first Flutter project:

- [Learn Flutter](https://docs.flutter.dev/get-started/learn-flutter)
- [Write your first Flutter app](https://docs.flutter.dev/get-started/codelab)
- [Flutter learning resources](https://docs.flutter.dev/reference/learning-resources)

For help getting started with Flutter development, view the
[online documentation](https://docs.flutter.dev/), which offers tutorials,
samples, guidance on mobile development, and a full API reference.
