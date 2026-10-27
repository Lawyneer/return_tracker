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

4. Set the secret key. The app refuses to start without one:

       export TAX_TRACKER_SECRET="any-random-string-for-local-dev"

   (For local development any fixed string is fine; production deployments must use a strong secret kept out of version control.)

5. Run the app locally to make sure everything works:

       python app.py

   Then open http://localhost:5000 in your browser.

6. Create a local user so you can log in (there is no self-registration):

       venv/bin/python manage_users.py add dev@example.com

   Follow the password policy prompts. Run `manage_users.py list` to see existing users.

## Running the tests

Run the full suite from the project root:

    pytest

Notes on the test setup:

- Tests run against a throwaway SQLite database created in a temporary directory per test — your local tax_returns.db is never touched.
- CSRF protection and the session cookie `Secure` flag are disabled in the test configuration so tests can post plain form data; a dedicated test asserts that the *production* `Config` keeps the hardened cookie flags, so relaxing them for real is a test failure, not a silent regression.
- Test users are provisioned directly into the throwaway database with properly hashed passwords; the shared fixtures handle login.
- The suite spends a noticeable amount of time in argon2 verification (~25s for the full run). That's the hashing library doing real work in the lockout tests — expected, not a problem.

Always run the full suite before opening a pull request; CI will run it again on every push and pull request (Python 3.10, 3.11, and 3.12).

## Guidelines

- **Match the existing structure**: routes live in the blueprints (auth.py, returns.py), queries in db.py, shared template helpers in helpers.py, and authentication/password/lockout logic in security.py. Add new statuses/return types to constants.py.
- **Every bug fix should come with a test** that fails without the fix. Place new tests in the tests/ directory, following the naming convention of the existing files.
- Keep the project's philosophy: a single Flask app with no build step — no JavaScript bundlers, npm dependencies, or heavyweight frameworks.
- Follow standard Python style (PEP 8); keep docstrings on public functions.
- The SQLite schema is migration-sensitive: never rename existing columns; add new ones as nullable and let init_db() handle the ALTER TABLE migration.
- **Security-sensitive changes** (anything touching auth.py, security.py, config.py, or the login template) need proportionate test coverage. See tests/test_security_auth.py for the established patterns: policy validation, generic error messages, lockout semantics, and drift guards on the production configuration.
- Don't commit tax_returns.db — it's runtime data, not source. It should already be covered by .gitignore and treated as binary by .gitattributes.
- Never commit secrets: no real passwords, no production TAX_TRACKER_SECRET values, no .env files.

## Pull request checklist

- [ ] pytest passes locally
- [ ] New functionality has test coverage
- [ ] Security-relevant changes have security-relevant tests
- [ ] README.md updated if behavior or setup changed
- [ ] No changes to tax_returns.db committed (it's runtime data)
- [ ] No secrets, hashes, or real credentials committed

## Reporting bugs

Open an issue with:

1. What you did (steps to reproduce)
2. What you expected to happen
3. What actually happened (including the full traceback, if any)
4. Your Python version and operating system

Security-related issues should never be opened as public issues — please contact the maintainer directly.

## Licensing

By submitting a pull request, you agree that your contributions will be licensed under the MIT License, the same license that covers this project.