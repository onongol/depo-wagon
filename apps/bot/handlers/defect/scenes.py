"""The steps that are Scenes so far; the rest are still plain handlers."""

from typing import TYPE_CHECKING

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
from .wagon import WagonScene

if TYPE_CHECKING:
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
    SummaryScene,
)

_BY_STATE = {scene.__scene_config__.state: scene for scene in DEFECT_SCENES}


def scene_for(state: str | None) -> type[DefectScene] | None:
    return _BY_STATE.get(state)


def walk(form: DefectData, upto: type[DefectScene] | None = None) -> list[str]:
    """The steps walked to reach upto, or the whole walk, which ends at the severity.

    previous() already follows the branch a human factor takes.
    """
    last = upto or SeverityScene
    steps = [] if upto else [last.__scene_config__.state]
    step = last.previous(form)
    while step is not None:
        steps.insert(0, step.state)
        step = _BY_STATE[step.state].previous(form)
    return steps
