"""Typed access to the defect form held in FSM state.

A load/save pair, not a context manager: confirm saves mid-handler, and a save
on exit would restore the form the save and decline paths just dropped.
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


async def drop_keys(state: FSMContext, *keys: str) -> None:
    """Read-modify-write: aiogram has no way to delete one key."""
    data = await state.get_data()
    await state.set_data({k: v for k, v in data.items() if k not in keys})


async def clear_defect_keys(state: FSMContext) -> None:
    """Not state.clear(): the AI chat or support session may be running there."""
    await drop_keys(state, *DEFECT_USER_DATA_KEYS)
