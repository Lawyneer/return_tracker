# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-10-27

### Breaking changes
- The passwordless dropdown login is gone. Authentication now requires a
  username (email address or alphanumeric name) and a password, verified
  against an argon2id hash stored per user. Users cannot register or change
  their own passwords; an administrator provisions all accounts.
- The application refuses to start unless the `TAX_TRACKER_SECRET`
  environment variable is set. Previously a random key was silently
  generated at startup, invalidating all sessions on every restart.
- All state-changing forms (login, status/signer/date edits, archive/
  restore, CSV import) now require a CSRF token. Clients posting without
  one receive HTTP 400.
- Existing users are locked out until an administrator sets a password for
  them: `venv/bin/python manage_users.py set-password <username>`.

### Security
- Passwords are hashed with argon2id (`argon2-cffi`); hashes are salted and
  never stored or logged in plaintext. Verification burns identical CPU
  time for unknown usernames so login timing does not reveal which
  accounts exist, and all login failures return the same generic message.
- Password policy, enforced when an admin creates or resets a password:
  20–100 characters with at least one lowercase letter, one uppercase
  letter, one digit, and one standard ASCII special character.
- Usernames are either a valid email address (≤254 chars) or a 3–64
  character alphanumeric/underscore name, matched case-insensitively.
- Brute-force lockout persisted in the database: after five failed login
  attempts the affected username and the client IP are both locked until an
  administrator resets them (`manage_users.py reset-lockouts`). A successful
  login clears the user's own failure counter; the IP counter is cumulative
  and only resets via the admin command. Lockouts survive application and
  server restarts.
- Sessions hardened for HTTPS deployment: cookies are `Secure`, `HttpOnly`,
  and `SameSite=Lax`, and the session is regenerated on login to prevent
  session fixation.
- CSRF protection on all POST forms via Flask-WTF.
- The login page now displays flashed error messages (previously a failed
  login rendered a silent, unchanged form).

### Added
- `manage_users.py` admin CLI: `add`, `set-password`, `list`,
  `reset-lockouts`, and `lock-status` commands for provisioning users and
  administering lockouts. Passwords are entered via hidden prompts and
  validated against the policy before hashing.
- `security.py` module: password/username validation, argon2 hashing and
  verification, and persistent lockout bookkeeping (tables
  `failed_attempts` and `lockouts`, created and migrated automatically by
  `init_db()`).
- `tests/test_security_auth.py`: password and username policy (length
  bounds, character classes, ASCII-only specials, email vs. alphanumeric),
  argon2 hash format and salting, generic login errors and user
  enumeration resistance, legacy user lockout, IP and user lockout
  semantics (cumulative IP counting, manual-reset-only unlocking,
  persistence across client instances), CSRF enforcement when enabled,
  and drift guards asserting the production session-cookie flags stay
  hardened.
- Password history auditing of deployments: `requirements.txt` gains
  `Flask-WTF` and `argon2-cffi`.

### Changed
- `tests/conftest.py` rewritten for the new authentication: test users are
  provisioned directly into the throwaway database with hashed passwords
  and logged in through the password form. CSRF is disabled and the
  session cookie `Secure` flag relaxed *in the test config only*; a test
  asserts the production `Config` keeps both hardened. The duplicated
  `add_return` helper definition (the second silently shadowed the first)
  was collapsed into one.
- Gunicorn is the supported production server (systemd unit template in
  the deployment notes); the Flask dev server binds to 127.0.0.1 only.
- `ProxyFix` applied (one proxy hop) so client IPs seen by the lockout
  logic are the real addresses forwarded by nginx, not 127.0.0.1.

### Fixed
- `app.py` exits with a clear FATAL message when `TAX_TRACKER_SECRET` is
  unset, instead of silently generating an ephemeral key.
- The login page showed no feedback on failed login (flash messages were
  queued but never rendered) — see Security above.
- Leftover broken test fragment in `test_signer_audit_import.py` removed.

## [1.4.0] - 2026-10-17

### Added
- New sidebar-based page shell built on the iPortfolio (Bootstrap)
  template. All post-login pages share a fixed left sidebar with the
  site navigation (All Returns, Archived Returns, Kanban Board,
  Add Return, Export CSV, Import CSV Guide, logout, and the theme
  toggle); the sidebar is styled independently of the active theme.
  Supported by new `static/css/main.css`, `static/css/sidebar.css`,
  and `static/css/layout.css`, plus bundled Bootstrap/vendor assets.
- Import CSV Guide page at `/import-info` (sidebar link "Import CSV
  Guide"), consolidating the CSV upload form and format documentation
  on one page, with a downloadable sample file served from
  `/import-sample`.

### Changed
- The login page is now a standalone, centered card with no sidebar or
  site navigation, and all other pages require an authenticated session.
- The CSV import control moved from the main list page to the Import
  CSV Guide page; the main list keeps the status dashboard, filters,
  and table only.
- The "Show archived returns" toggle on the list and board pages was
  replaced by a permanent "Archived Returns" link in the sidebar.
- Theme stylesheets (`light.css`, `dark.css`) now restyle the template
  by overriding its color variables rather than painting over it, so
  dark mode applies consistently to the page banner, sections, footer,
  tables, and form controls.
- The footer is pinned to the bottom of the browser window on pages
  without enough content to scroll, and flows below content on long
  pages.

### Fixed
- Table text (Year, Type, Due Date, Signer, Note columns) was
  black-on-black in dark mode and unreadable; cells now use the theme
  text color.
- The native file-input "Browse" button showed white-on-white text in
  dark mode; it now renders black text on white in both themes.

## [1.3.0] - 2026-10-15

### Added
- Signer field on returns. A free-text signer can be set when a return
  is created and edited any time from its detail page. The signer is
  shown on the main list, the Kanban board, and the detail page, and
  both views gained a filter (populated from signers actually in use,
  matched case-insensitively). The CSV export includes a Signer column.
- Bulk import of returns from a CSV file on the main list page, with a
  sample `import_template.csv`. Required columns: Return Name, Tax Year, and Return Type; optional: Due Date, Extended Due Date, Signer, and Status (by code or label). Headers are matched regardless of case or punctuation, and a UTF-8 BOM (as written by Excel) is handled. Rows are validated individually and committed one at a time, so one bad row never blocks the rest: a summary reports counts of added, skipped-as-duplicate, and rejected rows, with a reason per rejected row. Imported returns get an audit-history entry recording their starting signer, due dates, and origin.
- Extended audit trail for field edits: changes to a return's signer or due dates are now recorded in the status history alongside status changes, with who made the change and when. A `change_type` column distinguishes Status, Signer, and Due Date entries (existing rows are back-filled as Status on migration), and the history table on the detail page shows a Change column. No-op submissions are not logged, and each edit writes its update and history entry in one transaction.
- `tests/test_signer_audit_import.py` covering the new features: signer creation, editing, display, and filtering; `change_type` audit-trail entries (including no-op suppression and keeping the list page's Note column scoped to status-change notes); and CSV import validation (header aliasing, UTF-8 BOM handling, per-row rejection reasons, duplicates, status matching by code and label). The shared `add_return` test helper gained a `signer` parameter.

### Changed
- The Note column on the main list and Kanban board now reflects only notes from status changes (including the creation entry), so signer and date edits no longer surface there.
- The Note column on the main list has a bounded width (160–320px, ~260px target) so long notes wrap instead of stretching the table; the full text remains available via hover and on the detail page.
  - Reduced the workflow from 13 stages to 9, trimming statuses that were no longer used; returns sitting on a removed status are migrated to the nearest remaining stage and board column mappings are updated accordingly.

### Fixed
- The board column-mapping test referenced status codes that don't exist in `constants.py` ("Open Review Points", "Points Cleared", "Open CRI Points", "With CRI"); it now exercises the statuses actually defined, covering every status code end to end.

## [1.2.0] - 2026-10-12

### Added
- Kanban workflow board at `/board`, linked from the nav bar as "Workflow Board". Active (or archived) returns are grouped into four columns — Not Started, Preparing, In Review, Completed — with a per-column count in each header, clickable cards linking to the return detail page, and the same return-type filter and name search as the list view. Column membership is defined by `KANBAN_COLUMNS` in `constants.py`. No drag-and-drop: status changes still happen from the return detail page.
- `tests/test_board.py` covering the board's login requirement, column rendering and empty state, the full status-to-column mapping, archive scoping, and the type/name filters.
- Test coverage for the newly changed behaviors: the pre-selected status dropdown, note-only status updates, silent archive/restore redirects, the styled Cancel button, and a drift guard verifying every status in `constants.py` is seeded into the database.

### Changed
- The status dropdown on the return detail page now pre-selects the return's current status, so a note can be recorded without re-picking the status first. Submitting without changing the selection logs a same-status history entry carrying the note.
- Archiving and restoring are now silent: the confirmation flash messages and the JavaScript `confirm()` dialog were removed. Archiving returns to the active list; restoring a return now opens its detail page (previously it returned to the list). The "Return not found" error flash remains.
- Buttons now inherit the page font, and the Cancel link on the New Return page is styled to match the adjacent submit button (equal height, font size, and white text in dark mode) with all link states (`:visited`, `:hover`) explicitly styled.

### Fixed
- The return type dropdown on the New Return page listed "Other" twice (once from the `RETURN_TYPES` loop, once hardcoded in the template).

## [1.1.0] - 2026-10-11

### Added
- pytest test suite covering login and access control, the theme toggle, return creation and validation, the status-change audit trail, backward status moves, dashboard counts, archiving and restoring, filtering, and CSV export. Tests run against an isolated throwaway database, so local data is never touched.
- GitHub Actions CI workflow running the full test suite on Python 3.10, 3.11, and 3.12 for every push and pull request, with a status badge in the README.
- CONTRIBUTING.md with setup instructions, coding guidelines, and a pull request checklist.
- CHANGELOG.md (this file).
- `requirements-dev.txt` for development-only dependencies (pytest).

### Changed
- Restructured the application into a modular layout: Flask application factory in `app.py`, route blueprints in `auth.py` and `returns.py`, database handling in `db.py`, and shared template helpers and Jinja filters in `helpers.py`. No behavioral changes.
- Configuration centralized in `config.py`; the secret key and database path can now be overridden with the `TAX_TRACKER_SECRET` and `TAX_TRACKER_DB` environment variables. Existing databases are picked up automatically.
- README rewritten to cover the new project structure, testing setup, and contribution workflow.
- `.gitattributes` added to normalize line endings and treat the SQLite database and CSV exports as binary.

### Fixed
- Dashboard status cards no longer show a phantom count of 1 for statuses with no returns (a LEFT JOIN null-handling bug).
- Visited links rendered in an unreadable dark purple in dark mode; all link states are now explicitly styled for both themes.

## [1.0.0] - 2026-09-30

### Added
- 13-stage tax return workflow, from "Not Started" through "E-File Confirmation Received - Complete", with freely allowed backward moves.
- Add tax returns by name (individual or company), tax year, and return type (1040, 1041, 1065, 1120, 1120-S, 990, 990-PF, 990-T, 706, 709, State, Other).
- Full audit trail: every status change is logged with the old status, new status, the user who made it, a timestamp, and an optional note. Status updates and history entries are written in a single atomic transaction.
- Due dates and extended due dates per return, with automatic OVERDUE highlighting based on the effective (extended-if-set) due date.
- Dashboard count of returns at each status; stages with zero active returns are hidden.
- Filter the return list by status and return type, plus search by name.
- Most recent status note shown on the main list.
- Soft archiving with restore, preserving full status history. Archived returns are hidden from the active list and excluded from the active CSV export.
- CSV export for active and archived returns, with dated filenames.
- Dark mode (black background, red-to-green status badges with black badge text) and light mode, toggleable per user session. Dark is the default.
- Passwordless, name-based login suitable for trusted internal networks.

[Unreleased]: https://github.com/Lawyneer/return_tracker/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/Lawyneer/return_tracker/compare/v1.4.0...v2.0.0
[1.4.0]: https://github.com/Lawyneer/return_tracker/releases/tag/v1.4.0
[1.3.0]: https://github.com/Lawyneer/return_tracker/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Lawyneer/return_tracker/releases/tag/v1.2.0
[1.1.0]: https://github.com/Lawyneer/return_tracker/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Lawyneer/return_tracker/releases/tag/v1.0.0