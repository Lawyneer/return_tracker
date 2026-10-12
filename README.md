# Tax Return Status Tracker

[![CI](https://github.com/Lawyneer/return_tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/Lawyneer/return_tracker/actions/workflows/ci.yml)

A lightweight, single-database web application for tracking the status
of tax returns through not started all the way completion via e-file
confirmation. Built with Flask and SQLite and designed for small firms or
teams that want a shared checklist-style tracker with a full audit trail.

## Features

- **13-stage workflow tracking** — statuses progress from "Not Started" through
  document collection, preparer/reviewer stages, signature collection, filing,
  and finally e-file confirmation
- **Full status history** — every status change is timestamped, attributed to a
  user, and optionally annotated with a note
- **Dashboard overview** — at-a-glance count of returns in each workflow stage
- **Kanban workflow board** — a board view grouping active returns into
  four columns (Not Started, Preparing, In Review, Completed) with
  per-column counts, filterable by return type and searchable by name
- **Overdue highlighting** — returns past their effective due date (extended due
  date if set) are flagged automatically
- **Soft archiving** — completed returns can be archived and later restored,
  with history preserved
- **Filtering & search** — filter by status, return type, or search by name
- **CSV export** — download active or archived returns as a spreadsheet
- **Dual themes** — dark mode (default) and light mode
- **Tested** — pytest suite covering login, the status-change audit trail,
  archiving, filtering, and CSV export, run automatically in CI
- **Zero external services** — single SQLite database file, no server setup,
  no accounts or passwords to manage

## Supported Return Types

1040, 1041, 1065, 1120, 1120-S, 990, 990-PF, 990-T, 706, 709, State, Other

## Project Structure

```text
return_tracker/
├── .github/
│   └── workflows/
│       └── ci.yml          # GitHub Actions: pytest on Python 3.10–3.12
├── templates/
│   ├── base.html
│   ├── board.html
│   ├── login.html
│   ├── index.html
│   ├── new_return.html
│   └── detail.html
├── static/
│   └── css/
│       ├── dark.css
│       └── light.css
├── tests/
│   ├── conftest.py         # Shared fixtures (temp database, client, user)
│   ├── test_auth.py        # Login flow, access control, theme toggle
│   ├── test_returns.py     # Creation, validation, status changes, history, form details
│   ├── test_board.py       # Kanban board: columns, counts, filters
│   └── test_dashboard_archive_export.py
├── app.py                  # Application factory + entry point
├── auth.py                  # Blueprint: login / logout / theme toggle
├── config.py                # Configuration (secret key, DB path)
├── constants.py             # Return types and workflow status definitions
├── db.py                    # SQLite connection handling & schema
├── helpers.py               # Shared utilities, template context, Jinja filters
├── returns.py               # Blueprint: return CRUD, archive, CSV export
├── .gitattributes           # Line-ending normalization; DB treated as binary
├── CONTRIBUTING.md          # How to contribute
├── pytest.ini               # Test runner configuration
├── requirements.txt         # Runtime dependencies
├── requirements-dev.txt     # Development dependencies (pytest)
└── tax_returns.db           # SQLite database (created on first run, not committed)
```

## Getting Started

### Prerequisites

- Python 3.10+
- Flask

### Setup

**1. Create and activate a virtual environment**

Keeping dependencies in a virtual environment avoids conflicts with your
system's Python packages and makes the project portable:

```bash
# From the project root
python3 -m venv venv

# Activate it:
# Linux / macOS
source venv/bin/activate
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

(For development, also install the test dependencies — see
[Testing](#testing) below.)

**3. Run the app**

```bash
python app.py
```

The app starts on `http://0.0.0.0:5000`, making it reachable from other
machines on your local network. Open `http://localhost:5000` in your browser,
add yourself as a user, and start adding returns.

To deactivate the virtual environment when you're done:

```bash
deactivate
```

### First-Time Use

1. On the login page, add your name under **Add a new user**
2. Select your name from the dropdown and sign in
3. Click **+ Add Return** to create your first tax return
4. Open a return to change its status, add notes, or edit due dates
5. Click **Workflow Board** in the nav bar for the four-column kanban
   overview of where every return stands

## Testing

The test suite uses pytest with an isolated, throwaway SQLite database per
test — your local `tax_returns.db` is never touched.

```bash
pip install -r requirements-dev.txt
pytest
```

The suite covers the login flow, return creation and validation, the full
status-change audit trail (who, when, and any note), backward status moves,
dashboard counting, the kanban board's column grouping and count, archiving/
restoring, filtering, and CSV export.

CI runs the suite on Python 3.10–3.12 for every push and pull request —
see the badge at the top of this page.

## Contributing

Bug reports, feature ideas, and pull requests are welcome! See
[CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, coding
guidelines, and the pull-request checklist.

## Configuration

Both settings can be overridden with environment variables:

| Setting | Default | Environment Variable |
|---|---|---|
| Secret key | Randomly generated at startup | `TAX_TRACKER_SECRET` |
| Database path | `./tax_returns.db` | `TAX_TRACKER_DB` |

Setting a fixed `TAX_TRACKER_SECRET` is recommended for production so user
sessions survive app restarts.

## Backups & Data

All data lives in a single SQLite file (`tax_returns.db`). To back up, simply
copy that file while the app is stopped. To reset, delete the file — the schema
and default statuses are recreated on next launch.

Existing databases from earlier versions of this app are migrated
automatically (an `archived_at` column is added if missing).

## Security Notes

This app uses **passwordless, name-based login**: anyone who can reach the app
can sign in as any user. It is designed for a **trusted internal network**, not
public internet exposure.

Before exposing it beyond a private LAN, consider:

- Putting it behind a VPN or reverse proxy with authentication
- Adding real password-based authentication
- Serving over HTTPS

## License

This project is licensed under the MIT License — see the
[LICENSE](LICENSE) file for details.