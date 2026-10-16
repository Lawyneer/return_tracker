"""Domain constants shared across modules."""

# Allowed return types offered in the "Add Return" form.
RETURN_TYPES = ["1040", "1041", "1065", "1120", "1120-S", "990", "990-PF", "990-T", "706", "709", "State", "Other"]

# Workflow statuses: (code, human-readable label, pipeline stage order).
# stage_order drives sorting and the red->green badge coloring.
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

# Kanban dashboard columns: (column title, status codes in that column).
# Codes refer to the STATUSES tuples above.
KANBAN_COLUMNS = [
    ("Not Started", ["not_started", "docs_requested"]),
    ("Preparing",   ["with_preparer", "docs_waiting"]),
    ("In Review",   ["with_reviewer", "with_or"]),
    ("Completed",   ["out_for_signatures", "eforms_received", "complete"]),
]

DEFAULT_THEME = "dark"