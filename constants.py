"""Domain constants shared across modules."""

# Allowed return types offered in the "Add Return" form.
RETURN_TYPES = ["1040", "1041", "1065", "1120", "1120-S", "990", "990-PF", "990-T", "706", "709", "State", "Other"]

# Workflow statuses: (code, human-readable label, pipeline stage order).
# stage_order drives sorting and the red->green badge coloring.
STATUSES = [
    ("not_started",          "Not Started",                               1),
    ("docs_requested",       "Documents Requested",                       2),
    ("prep_ready",           "Ready for Preparation",                     3),
    ("with_preparer",        "In Preparation",                            4),
    ("docs_waiting",         "Waiting on Documents",                      5),
    ("with_reviewer",        "Return with Reviewer",                      6),
    ("open_review_points",   "Open Review Points",                        7),
    ("points_cleared",       "Review Points Cleared",                     8),
    ("with_cri",             "With CRI",                                  9),
    ("open_cri_points",      "Open CRI Points",                           10),
    ("out_for_signatures",   "Out for Signatures",                       11),
    ("eforms_received",      "E-File Forms Received",                     12),
    ("complete",             "E-File Forms Uploaded - Complete",         13),
]

# Kanban dashboard columns: (column title, status codes in that column).
# Codes refer to the STATUSES tuples above.
KANBAN_COLUMNS = [
    ("Not Started", ["not_started", "docs_requested", "prep_ready"]),
    ("Preparing",   ["with_preparer", "docs_waiting",
                     "open_review_points", "open_cri_points"]),
    ("In Review",   ["with_reviewer", "points_cleared", "with_cri"]),
    ("Completed",   ["out_for_signatures", "eforms_received", "complete"]),
]

DEFAULT_THEME = "dark"