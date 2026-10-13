# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Bulk import of returns from a CSV file on a new "Import" page. The
  import expects the same columns as the CSV export (Return Name, Tax
  Year, Type, Due Date, Extended Due Date), so exported spreadsheets can
  be edited and re-imported. Rows are validated individually: valid rows
  are inserted, and a summary reports how many were imported, skipped as
  duplicates, or rejected with the reason per row.
- Assignment of returns to users. Each return has an assignee shown on
  the list, board, and detail pages; the assignee can be changed when
  updating a status (for example, handing a return from the preparer to
  the reviewer when it moves to a review stage) or on its own. Every
  assignment change is recorded in the status history with its
  timestamp and the user who made the change.
- Pipeline statistics page showing how long returns spend at each
  workflow status, computed from the status history, plus counts of
  returns moved per status by each user.
- Database backup download, which produces a consistent snapshot of the
  SQLite database using SQLite's online backup API, safe to run while
  the app is serving requests.
- Login rate limiting with temporary lockout after repeated failed
  attempts from the same username.

### Changed
- Login now requires a password. Passwords are stored salted and hashed
  (Werkzeug PBKDF2), never in plaintext; existing users are prompted to
  set a password on first login after the upgrade.
- CSV export now includes the assignee column.

### Security
- Added cross-site request forgery (CSRF) protection on all forms and
  session-cookie hardening (`HttpOnly`, `SameSite=Lax`) in preparation
  for internet-facing deployments.

## [1.2.0] - 2026-10-12

### Added
- Kanban workflow board at `/board`, linked from the nav bar as "Workflow
  Board". Active (or archived) returns are grouped into four columns —
  Not Started, Preparing, In Review, Completed — with a per-column count
  in each header, clickable cards linking to the return detail page, and
  the same return-type filter and name search as the list view. Column
  membership is defined by `KANBAN_COLUMNS` in `constants.py`. No
  drag-and-drop: status changes still happen from the return detail page.
- `tests/test_board.py` covering the board's login requirement, column
  rendering and empty state, the full status-to-column mapping, archive
  scoping, and the type/name filters.
- Test coverage for the newly changed behaviors: the pre-selected status
  dropdown, note-only status updates, silent archive/restore redirects,
  the styled Cancel button, and a drift guard verifying every status in
  `constants.py` is seeded into the database.

### Changed
- The status dropdown on the return detail page now pre-selects the
  return's current status, so a note can be recorded without re-picking
  the status first. Submitting without changing the selection logs a
  same-status history entry carrying the note.
- Archiving and restoring are now silent: the confirmation flash messages
  and the JavaScript `confirm()` dialog were removed. Archiving returns
  to the active list; restoring a return now opens its detail page
  (previously it returned to the list). The "Return not found" error
  flash remains.
- Buttons now inherit the page font, and the Cancel link on the New
  Return page is styled to match the adjacent submit button (equal
  height, font size, and white text in dark mode) with all link states
  (`:visited`, `:hover`) explicitly styled.

### Fixed
- The return type dropdown on the New Return page listed "Other" twice
  (once from the `RETURN_TYPES` loop, once hardcoded in the template).

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

[Unreleased]: https://github.com/Lawyneer/return_tracker/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/Lawyneer/return_tracker/releases/tag/v1.2.0
[1.1.0]: https://github.com/Lawyneer/return_tracker/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Lawyneer/return_tracker/releases/tag/v1.0.0