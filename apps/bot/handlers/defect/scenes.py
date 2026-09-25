"""The steps that are Scenes so far; the rest are still plain handlers."""

from typing import TYPE_CHECKING

from .defect_type import DefectTypeScene
from .department import DepartmentScene
from .node import NodeScene
from .part_number import PartNumberScene
from .photo import PhotoScene
from .severity import SeverityScene
from .wagon import WagonScene

if TYPE_CHECKING:
    from .scene import DefectScene

DEFECT_SCENES: tuple[type[DefectScene], ...] = (
    WagonScene,
    DepartmentScene,
    NodeScene,
    PartNumberScene,
    DefectTypeScene,
    SeverityScene,
    PhotoScene,
)

_BY_STATE = {scene.__scene_config__.state: scene for scene in DEFECT_SCENES}


def scene_for(state: str | None) -> type[DefectScene] | None:
    return _BY_STATE.get(state)
