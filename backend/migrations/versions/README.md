# Migration Versions

Generated Alembic migration files are stored here.

New files must follow the convention documented in `../README.md`:

```text
YYYYMMDD_HHMMSS_<revision>_<action>_<object>.py
```

## Current revision chain

The chain is determined by each file's `revision` and `down_revision`, not by
alphabetical filename order.

| Order | Created at | Revision | Purpose |
| ---: | --- | --- | --- |
| 1 | 2026-07-20 22:20:57 | `bbd627449743` | Create rebuilt core tables |
| 2 | 2026-08-09 13:00:00 | `8a9c4d2e1f01` | Expand resume file type for canonical MIME values |
| 3 | 2026-08-09 16:00:00 | `d3f6a8c1b204` | Allow resumes before candidate confirmation |
| 4 | 2026-08-12 16:00:00 | `f5a7c9e2d104` | Add independent resume structure state |
| 5 | 2026-08-15 11:00:00 | `c8e1a6f4d205` | Structure jobs for Stage 6 |
| 6 | 2026-08-17 16:00:00 | `e7b1c9d4a206` | Add Stage 7 application foundation |

`e7b1c9d4a206` has passed an isolated PostgreSQL 16
`c8 -> e7 -> c8 -> e7` round trip and `alembic check`. The production/development
database remains on `c8e1a6f4d205` until an explicit upgrade is approved.
