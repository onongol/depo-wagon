"""
Defect registration handlers (9 steps).

Flow:
  /new_defect
    → start       : check auth, reset draft
    → wagon       : enter wagon number
    → node        : select node (inline keyboard)
    → defect_type : select defect type (inline keyboard)
    → severity    : select severity (inline keyboard)
    → photo       : send photos (multiple) or skip
    → description : type description or skip
    → confirm     : review summary → save → AI analysis
    → verdict     : employee gives own verdict
"""

from .cancel import cancel_defect
from .conversation import get_defect_handler
from .start import new_defect_start

__all__ = [
    "get_defect_handler",
    "cancel_defect",
    "new_defect_start",
]
