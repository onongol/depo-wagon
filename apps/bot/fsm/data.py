"""Typed access to the defect form held in FSM state.

Deliberately a load/save pair rather than a context manager: about eight
handlers return early when the form is gone, and a yield-based wrapper makes
that path awkward. The safety net for a missed save is the full-flow
integration test, not an abstraction.
"""

from typing import TYPE_CHECKING

from apps.bot.constants import DEFECT_USER_DATA_KEYS, UD_DEFECT
from apps.bot.user_data import DefectData

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext


async def load_defect(state: FSMContext) -> DefectData | None:
    """Return the defect form, or None if the flow is not in progress."""
    stored = (await state.get_data()).get(UD_DEFECT)
    return DefectData.from_dict(stored) if stored else None


async def save_defect(state: FSMContext, defect: DefectData) -> None:
    await state.update_data({UD_DEFECT: defect.to_dict()})


async def clear_defect_keys(state: FSMContext) -> None:
    """Drop every key the defect flow owns, leaving the rest of the data alone.

    aiogram has no delete-one-key primitive, hence the read-modify-write. This
    is the equivalent of the pops PTB does on cancel — not state.clear(), which
    would also discard the AI chat history.
    """
    data = await state.get_data()
    remaining = {k: v for k, v in data.items() if k not in DEFECT_USER_DATA_KEYS}
    await state.set_data(remaining)
