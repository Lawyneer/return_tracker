# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-10-11

### Added
- pytest test suite covering login and access control, the theme toggle,
  return creation and validation, the status-change audit trail, backward
  status moves, dashboard counts, archiving and restoring, filtering, and
  CSV export. Tests run against an isolated throwaway database, so local
  data is never touched.
- GitHub Actions CI workflow running the full test suite on Python 3.10,
  3.11, and 3.12 for every push and pull request, with a status badge in
  the README.
- CONTRIBUTING.md with setup instructions, coding guidelines, and a pull
  request checklist.
- CHANGELOG.md (this file).
- `requirements-dev.txt` for development-only dependencies (pytest).

### Changed
- Restructured the application into a modular layout: Flask application
  factory in `app.py`, route blueprints in `auth.py` and `returns.py`,
  database handling in `db.py`, and shared template helpers and Jinja
  filters in `helpers.py`. No behavioral changes.
- Configuration centralized in `config.py`; the secret key and database
  path can now be overridden with the `TAX_TRACKER_SECRET` and
  `TAX_TRACKER_DB` environment variables. Existing databases are picked
  up automatically.
- README rewritten to cover the new project structure, testing setup, and
  contribution workflow.
- `.gitattributes` added to normalize line endings and treat the SQLite
  database and CSV exports as binary.

### Fixed
- Dashboard status cards no longer show a phantom count of 1 for statuses
  with no returns (a LEFT JOIN null-handling bug).
- Visited links rendered in an unreadable dark purple in dark mode; all
  link states are now explicitly styled for both themes.

## [1.0.0] - 2026-09-30

### Added
- 13-stage tax return workflow, from "Not Started" through "E-File
  Confirmation Received - Complete", with freely allowed backward moves.
- Add tax returns by name (individual or company), tax year, and return
  type (1040, 1041, 1065, 1120, 1120-S, 990, 990-PF, 990-T, 706, 709,
  State, Other).
- Full audit trail: every status change is logged with the old status, new
  status, the user who made it, a timestamp, and an optional note. Status
  updates and history entries are written in a single atomic transaction.
- Due dates and extended due dates per return, with automatic OVERDUE
  highlighting based on the effective (extended-if-set) due date.
- Dashboard count of returns at each status; stages with zero active
  returns are hidden.
- Filter the return list by status and return type, plus search by name.
- Most recent status note shown on the main list.
- Soft archiving with restore, preserving full status history. Archived
  returns are hidden from the active list and excluded from the active
  CSV export.
- CSV export for active and archived returns, with dated filenames.
- Dark mode (black background, red-to-green status badges with black
  badge text) and light mode, toggleable per user session. Dark is the
  default.
- Passwordless, name-based login suitable for trusted internal networks.

[Unreleased]: https://github.com/Lawyneer/return_tracker/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/Lawyneer/return_tracker/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Lawyneer/return_tracker/releases/tag/v1.0.0