# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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

### Security
- Added cross-site request forgery (CSRF) protection on all forms and
  session-cookie hardening (`HttpOnly`, `SameSite=Lax`) in preparation
  for internet-facing deployments.

## [1.3.0] - 2026-10-15

### Added
- Signer field on returns. A free-text signer can be set when a return
  is created and edited any time from its detail page. The signer is
  shown on the main list, the Kanban board, and the detail page, and
  both views gained a filter (populated from signers actually in use,
  matched case-insensitively). The CSV export includes a Signer column.
- Bulk import of returns from a CSV file on the main list page, with a
  sample `import_template.csv`. Required columns: Return Name, Tax
  Year, and Return Type; optional: Due Date, Extended Due Date, Signer,
  and Status (by code or label). Headers are matched regardless of case
  or punctuation, and a UTF-8 BOM (as written by Excel) is handled.
  Rows are validated individually and committed one at a time, so one
  bad row never blocks the rest: a summary reports counts of added,
  skipped-as-duplicate, and rejected rows, with a reason per rejected
  row. Imported returns get an audit-history entry recording their
  starting signer, due dates, and origin.
- Extended audit trail for field edits: changes to a return's signer or
  due dates are now recorded in the status history alongside status
  changes, with who made the change and when. A `change_type` column
  distinguishes Status, Signer, and Due Date entries (existing rows are
  back-filled as Status on migration), and the history table on the
  detail page shows a Change column. No-op submissions are not logged,
  and each edit writes its update and history entry in one transaction.
- `tests/test_signer_audit_import.py` covering the new features:
  signer creation, editing, display, and filtering; `change_type`
  audit-trail entries (including no-op suppression and keeping the
  list page's Note column scoped to status-change notes); and CSV
  import validation (header aliasing, UTF-8 BOM handling, per-row
  rejection reasons, duplicates, status matching by code and label).
  The shared `add_return` test helper gained a `signer` parameter.

### Changed
- The Note column on the main list and Kanban board now reflects only
  notes from status changes (including the creation entry), so signer
  and date edits no longer surface there.
- The Note column on the main list has a bounded width (160–320px,
  ~260px target) so long notes wrap instead of stretching the table;
  the full text remains available via hover and on the detail page.

### Fixed
- The board column-mapping test referenced status codes that don't
  exist in `constants.py` ("Open Review Points", "Points Cleared",
  "Open CRI Points", "With CRI"); it now exercises the statuses
  actually defined, covering every status code end to end.

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

[Unreleased]: https://github.com/Lawyneer/return_tracker/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/Lawyneer/return_tracker/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Lawyneer/return_tracker/releases/tag/v1.2.0
[1.1.0]: https://github.com/Lawyneer/return_tracker/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Lawyneer/return_tracker/releases/tag/v1.0.0