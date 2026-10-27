"""Domain constants shared across modules."""
import string

RETURN_TYPES = ["1040", "1041", "1065", "1120", "1120-S", "990", "990-PF", "990-T", "706", "709", "State", "Other"]

STATUSES = [
    ("not_started",          "Not Started",                               1),
    ("docs_requested",       "Documents Requested",                       2),
    ("with_preparer",        "In Preparation",                            3),
    ("docs_waiting",         "Waiting on Documents",                      4),
    ("with_reviewer",        "With Reviewer",                             5),
    ("with_or",              "With Outside Reviewer",                     6),
    ("out_for_signatures",   "Out for Signatures",                        7),
    ("eforms_received",      "E-File Forms Received",                     8),
    ("complete",             "E-File Forms Uploaded - Complete",          9),
]

KANBAN_COLUMNS = [
    ("Not Started", ["not_started", "docs_requested"]),
    ("Preparing",   ["with_preparer", "docs_waiting"]),
    ("In Review",   ["with_reviewer", "with_or"]),
    ("Completed",   ["out_for_signatures", "eforms_received", "complete"]),
]

DEFAULT_THEME = "dark"

# ---------------------------- security settings -----------------------------

MIN_PASSWORD_LENGTH = 20
MAX_PASSWORD_LENGTH = 100

# Standard ASCII punctuation only (string.punctuation):
# !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~
PASSWORD_SPECIAL_CHARS = set(string.punctuation)

# After this many consecutive failures, BOTH the username key and the IP
# key are locked until an administrator runs `manage_users.py reset-lockouts`.
MAX_LOGIN_ATTEMPTS = 5

USERNAME_MAX_LEN = 254