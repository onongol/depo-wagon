"""Typed access to the defect form held in FSM state.

Deliberately a load/save pair rather than a context manager: about eight
handlers return early when the form is gone, and a yield-based wrapper makes
that path awkward. The safety net for a missed save is the full-flow
integration test, not an abstraction.
"""

from typing import TYPE_CHECKING

from apps.bot.constants import DEFECT_USER_DATA_KEYS, UD_DEFECT, UD_RESP_EMPLOYEES
from apps.bot.user_data import DefectData, EmployeeRef

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext


async def load_defect(state: FSMContext) -> DefectData | None:
    """Return the defect form, or None if it is gone or from another schema."""
    stored = (await state.get_data()).get(UD_DEFECT)
    return DefectData.from_dict(stored) if stored else None


async def save_defect(state: FSMContext, defect: DefectData) -> None:
    await state.update_data({UD_DEFECT: defect.to_dict()})


async def load_employees(state: FSMContext) -> list[EmployeeRef]:
    """The department roster cached for the responsible-employee picker."""
    stored = (await state.get_data()).get(UD_RESP_EMPLOYEES) or []
    refs = (EmployeeRef.from_dict(ref) for ref in stored)
    return [ref for ref in refs if ref is not None]


async def save_employees(state: FSMContext, employees: list[EmployeeRef]) -> None:
    await state.update_data({UD_RESP_EMPLOYEES: [e.to_dict() for e in employees]})


async def clear_defect_keys(state: FSMContext) -> None:
    """Drop every key the defect flow owns, leaving the rest of the data alone.

    aiogram has no delete-one-key primitive, hence the read-modify-write. This
    is the equivalent of the pops PTB does on cancel — not state.clear(), which
    would also discard the AI chat history.
    """
    data = await state.get_data()
    remaining = {k: v for k, v in data.items() if k not in DEFECT_USER_DATA_KEYS}
    await state.set_data(remaining)
