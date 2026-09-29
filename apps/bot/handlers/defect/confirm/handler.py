import logging
from typing import TYPE_CHECKING

from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.scene import Scene, on

from apps.bot.callback_data import CB_DEFECT_CONTINUE, CB_DEFECT_RESTART
from apps.bot.constants import BTN_NEW_DEFECT, UD_SCREEN
from apps.bot.fsm import clear_defect_keys, drop_keys, load_defect
from apps.bot.handlers.defect.scene import ask_about_the_open_form
from apps.bot.handlers.defect.start import open_blank_form
from apps.bot.handlers.defect.text import (
    build_ai_analyzing_text,
    build_defect_continued_text,
    build_save_failed_text,
    build_saving_text,
)
from apps.bot.keyboards.menu import MENU_TEXTS, main_menu_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.bot.utils.screens import answer_anew, edit_or_send

from .pipeline import alert_decommission, persist_defect, run_ai_analysis
from .result import send_result

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message

    from apps.core.models import Employee

logger = logging.getLogger(__name__)


class SavingScene(Scene, state=DefectSG.saving.state):
    """The save, then the AI; being here is what stops a second Save.

    Not a DefectScene: nothing may cancel or redraw the form mid-save. Updates
    wait on the per-user lock until the save ends, so the handlers after the
    entry only ever meet a save that died half-way.
    """

    @on.callback_query.enter()
    async def save(
        self,
        callback: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        employee: Employee | None,
    ) -> None:
        await callback.answer()
        await drop_keys(state, UD_SCREEN)
        progress = callback.message

        if not employee:
            await progress.edit_text(str(M.NOT_REGISTERED))
            await self.wizard.exit()
            return

        defect_data = await load_defect(state)

        await progress.edit_text(**build_saving_text().as_kwargs())

        try:
            saved = await persist_defect(state, defect_data, employee, bot)
        except Exception:
            logger.exception("Failed to save defect")
            await answer_anew(
                callback,
                **build_save_failed_text().as_kwargs(),
                reply_markup=main_menu_keyboard(),
            )
            await self.wizard.exit()
            return

        await alert_decommission(bot, employee, defect_data)

        await progress.edit_text(**build_ai_analyzing_text().as_kwargs())
        ai_result = await run_ai_analysis(
            defect_data, saved.defect.id, saved.photo_bytes
        )

        await send_result(bot, progress, ai_result)
        await self.wizard.exit()

    @on.message(Command("new_defect"))
    @on.message(F.text == str(BTN_NEW_DEFECT))
    async def new_defect(self, message: Message) -> None:
        await ask_about_the_open_form(message)

    @on.message(F.text.in_(MENU_TEXTS))
    @on.message(Command("start", "my_tasks", "ask", "support", "help"))
    async def menu_button(self, message: Message) -> None:
        """No screen to show again; /cancel is the way out."""
        await message.answer(**build_defect_continued_text().as_kwargs())

    @on.callback_query(F.data == CB_DEFECT_CONTINUE)
    async def carry_on(self, callback: CallbackQuery) -> None:
        await callback.answer()
        await edit_or_send(callback, **build_defect_continued_text().as_kwargs())

    @on.callback_query(F.data == CB_DEFECT_RESTART)
    async def start_over(self, callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        await open_blank_form(state)
        await self.wizard.goto(DefectSG.wagon_num)

    # After every handler above: aiogram registers a class's own in the order written
    @on.callback_query()
    async def absorb(self, callback: CallbackQuery) -> None:
        """An old button tapped here dies quietly rather than as expired."""
        await callback.answer()

    @on.message.exit()
    @on.callback_query.exit()
    async def drop_the_form(
        self, event: Message | CallbackQuery, state: FSMContext
    ) -> None:
        """exit() only clears the state; the form is ours to drop."""
        await clear_defect_keys(state)
