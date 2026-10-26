"""Every state of the defect flow, each a Scene."""

from typing import TYPE_CHECKING

from .confirm import SavingScene
from .defect_type import DefectTypeScene
from .department import DepartmentScene
from .description import DescriptionScene
from .measurement import MeasurementChoiceScene
from .node import NodeScene
from .part_number import PartNumberScene
from .photo import PhotoScene
from .responsible_employee import ResponsibleEmployeeScene
from .severity import SeverityScene
from .summary import SummaryScene
from .verdict import VerdictScene
from .wagon import WagonScene

if TYPE_CHECKING:
    from aiogram.fsm.scene import Scene

    from apps.bot.user_data import DefectData

    from .scene import DefectScene

DEFECT_SCENES: tuple[type[DefectScene], ...] = (
    WagonScene,
    DepartmentScene,
    NodeScene,
    PartNumberScene,
    DefectTypeScene,
    ResponsibleEmployeeScene,
    PhotoScene,
    MeasurementChoiceScene,
    DescriptionScene,
    SeverityScene,
    VerdictScene,
    SummaryScene,
)

# The form's steps, then the save that ends it
FLOW_SCENES: tuple[type[Scene], ...] = (*DEFECT_SCENES, SavingScene)

_BY_STATE = {scene.__scene_config__.state: scene for scene in DEFECT_SCENES}


def walk(form: DefectData, upto: type[DefectScene] | None = None) -> list[str]:
    """The steps walked to reach upto, or the whole walk, which ends at the verdict.

    previous() already follows the branch a human factor takes.
    """
    last = upto or VerdictScene
    steps = [] if upto else [last.__scene_config__.state]
    step = last.previous(form)
    while step is not None:
        steps.insert(0, step.state)
        step = _BY_STATE[step.state].previous(form)
    return steps
