"""Domain constants shared across modules."""

# Allowed return types offered in the "Add Return" form.
RETURN_TYPES = ["1040", "1041", "1065", "1120", "1120-S", "990", "990-T", "706", "709", "State", "Other"]

# Workflow statuses: (code, human-readable label, pipeline stage order).
# stage_order drives sorting and the red->green badge coloring.
STATUSES = [
    ("not_started",          "Not Started",                               1),
    ("partial_docs_started", "Some Documents Received, Return Started",   2),
    ("waiting_on_documents", "Waiting on Documents",                      3),
    ("all_docs_started",     "All Documents Received, Return Started",    4),
    ("with_reviewer",        "Return with Reviewer",                       5),
    ("open_review_points",   "Open Review Points",                         6),
    ("points_cleared",       "Review Points Cleared",                       7),
    ("with_central_review",  "With Central Review",                        8),
    ("open_central_points",  "Open Central Review Points",                 9),
    ("out_for_signatures",   "Out for Signatures",                        10),
    ("eforms_received",      "E-File Forms Received",                     11),
    ("returns_filed",        "Returns Filed",                             12),
    ("complete",             "E-File Confirmation Received - Complete",   13),
]

DEFAULT_THEME = "dark"