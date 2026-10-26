"""The work after Save, one step per module; none of it talks to the user."""

from .alert import alert_decommission
from .analyze import run_ai_analysis
from .persist import persist_defect
from .register import PersistResult, register_defect

__all__ = [
    "PersistResult",
    "alert_decommission",
    "persist_defect",
    "register_defect",
    "run_ai_analysis",
]
