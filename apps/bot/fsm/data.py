"""Typed access to the defect form held in FSM state.

A load/save pair, not a context manager: confirm saves mid-handler, and a save
on exit would restore the form the verdict and decline paths just dropped.
"""

from typing import TYPE_CHECKING

from apps.bot.constants import DEFECT_USER_DATA_KEYS, UD_DEFECT
from apps.bot.user_data import DefectData

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext


async def load_defect(state: FSMContext) -> DefectData | None:
    """Return the defect form, or None if it is gone or from another schema."""
    stored = (await state.get_data()).get(UD_DEFECT)
    return DefectData.from_dict(stored) if stored else None


async def save_defect(state: FSMContext, defect: DefectData) -> None:
    await state.update_data({UD_DEFECT: defect.to_dict()})


async def clear_defect_keys(state: FSMContext) -> None:
    """Drop every key the defect flow owns, leaving the state and other data alone.

    Not state.clear(): StaleSchemaMiddleware drops a stale form under any state
    and must not end the AI chat or support session running there. aiogram has
    no delete-one-key primitive, hence the read-modify-write.
    """
    data = await state.get_data()
    remaining = {k: v for k, v in data.items() if k not in DEFECT_USER_DATA_KEYS}
    await state.set_data(remaining)
