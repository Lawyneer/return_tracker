# Contributing to the Tax Return Status Tracker

Thanks for helping improve this project! This document covers the basics.

## Getting set up

1. Fork the repository on GitHub, then clone your fork locally:

       git clone https://github.com/YOUR_USERNAME/return_tracker.git
       cd return_tracker

   (Replace YOUR_USERNAME with your GitHub username.)

2. Create and activate a virtual environment:

       python3 -m venv venv
       source venv/bin/activate

   On Windows PowerShell, use:

       .\venv\Scripts\Activate.ps1

3. Install dependencies (runtime + development):

       pip install -r requirements.txt -r requirements-dev.txt

4. Run the app locally to make sure everything works:

       python app.py

   Then open http://localhost:5000 in your browser.

## Running the tests

Run the full suite from the project root:

    pytest

Tests run against a throwaway SQLite database created in a temporary
directory per test — your local tax_returns.db is never touched. Always
run the full suite before opening a pull request; CI will run it again on
every push and pull request (Python 3.10, 3.11, and 3.12).

## Guidelines

- **Match the existing structure**: routes live in the blueprints
  (auth.py, returns.py), queries in db.py, shared template helpers in
  helpers.py. Add new statuses/return types to constants.py.
- **Every bug fix should come with a test** that fails without the fix.
  Place new tests in the tests/ directory, following the naming convention
  of the existing files.
- Keep the project's philosophy: a single Flask app with no build step — no
  JavaScript bundlers, npm dependencies, or heavyweight frameworks.
- Follow standard Python style (PEP 8); keep docstrings on public functions.
- The SQLite schema is migration-sensitive: never rename existing columns;
  add new ones as nullable and let init_db() handle the ALTER TABLE
  migration.
- Don't commit tax_returns.db — it's runtime data, not source. It should
  already be covered by .gitignore and treated as binary by .gitattributes.

## Pull request checklist

- [ ] pytest passes locally
- [ ] New functionality has test coverage
- [ ] README.md updated if behavior or setup changed
- [ ] No changes to tax_returns.db committed (it's runtime data)

## Reporting bugs

Open an issue with:

1. What you did (steps to reproduce)
2. What you expected to happen
3. What actually happened (including the full traceback, if any)
4. Your Python version and operating system

Security-related issues should never be opened as public issues — please
contact the maintainer directly.

## Licensing

By submitting a pull request, you agree that your contributions will be
licensed under the MIT License, the same license that covers this project.