"""What every step of the defect form shares once it is a Scene."""

from typing import TYPE_CHECKING, Any

from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.scene import Scene, on
from aiogram.utils.formatting import Text

from apps.bot.callback_data import (
    CB_DEFECT_CONTINUE,
    CB_DEFECT_RESTART,
    CB_STEP_BACK,
)
from apps.bot.constants import BTN_NEW_DEFECT, UD_EDITING
from apps.bot.filters import NotACommand
from apps.bot.fsm import clear_defect_keys, load_defect
from apps.bot.keyboards.common import with_back_button
from apps.bot.keyboards.defect import defect_in_progress_keyboard
from apps.bot.keyboards.menu import MENU_TEXTS, form_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.bot.utils.screens import edit_or_send

from .start import open_blank_form
from .text import build_defect_in_progress_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State
    from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

    from apps.bot.user_data import DefectData

type Screen = tuple[Text | str, InlineKeyboardMarkup | None]

# A step's typed answer; menu buttons and commands are the base class's
STEP_TEXT = (F.text, NotACommand(), ~F.text.in_(MENU_TEXTS))


def as_send_kwargs(content: Text | str) -> dict[str, Any]:
    """HTML strings until every step's text has moved to a Text builder."""
    if isinstance(content, Text):
        return content.as_kwargs()
    return {"text": content, "parse_mode": M.PARSE_MODE}


async def ask_about_the_open_form(message: Message) -> None:
    """New Defect while a form is open: ask rather than wipe it."""
    await message.answer(
        **build_defect_in_progress_text().as_kwargs(),
        reply_markup=defect_in_progress_keyboard(),
    )


class DefectScene(Scene):
    """One DefectSG state per subclass.

    aiogram registers these handlers after each step's own, so a step's text
    filter has to leave menu buttons and commands alone; STEP_TEXT does.
    """

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        """The step as entering it shows it, which is also what retake() shows."""
        raise NotImplementedError

    @classmethod
    def previous(cls, form: DefectData) -> State | None:
        """The step before this one on the way here; the first step has none."""
        return None

    @classmethod
    def back_to(cls, form: DefectData, data: dict[str, Any]) -> State | None:
        """Where Back leads: the previous step, or from an Edit the summary."""
        if data.get(UD_EDITING):
            return DefectSG.confirm
        return cls.previous(form)

    @classmethod
    async def draw(
        cls, form: DefectData, data: dict[str, Any], **screen_args: Any
    ) -> Screen:
        """The screen with Back added wherever Back leads somewhere."""
        content, keyboard = await cls.screen(form, data, **screen_args)
        if cls.back_to(form, data):
            keyboard = with_back_button(keyboard)
        return content, keyboard

    async def go_on(self, state: FSMContext, next_step: State) -> None:
        """To the next step, whose scene draws its own screen; after an Edit, back.

        Not after=After.goto(...): that destination is fixed, and an Edit's is not.
        Not wizard.back() either: the snapshot it restores holds the form before
        the edit.
        """
        editing = (await state.get_data()).get(UD_EDITING)
        await self.wizard.goto(DefectSG.confirm if editing else next_step)

    @on.message.enter()
    async def show_as_message(self, message: Message, state: FSMContext) -> None:
        content, keyboard = await self.draw(
            await load_defect(state), await state.get_data()
        )
        # No step takes the menu for an answer, so a screen without buttons swaps it
        # for the form's Cancel
        await message.answer(
            **as_send_kwargs(content), reply_markup=keyboard or form_keyboard()
        )

    @on.callback_query.enter()
    async def show_as_edit(self, callback: CallbackQuery, state: FSMContext) -> None:
        content, keyboard = await self.draw(
            await load_defect(state), await state.get_data()
        )
        await edit_or_send(callback, **as_send_kwargs(content), reply_markup=keyboard)

    @on.message(Command("new_defect"))
    @on.message(F.text == str(BTN_NEW_DEFECT))
    async def new_defect(self, message: Message) -> None:
        await ask_about_the_open_form(message)

    @on.message(F.text.in_(MENU_TEXTS))
    @on.message(Command("start", "my_tasks", "ask", "support", "help"))
    async def show_again(self, _message: Message) -> None:
        """Every other button and command; /cancel is the way out."""
        await self.wizard.retake()

    @on.callback_query(F.data == CB_DEFECT_CONTINUE)
    async def carry_on(self, callback: CallbackQuery) -> None:
        await callback.answer()
        await self.wizard.retake()

    @on.callback_query(F.data == CB_DEFECT_RESTART)
    async def start_over(self, callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        await open_blank_form(state)
        await self.wizard.goto(DefectSG.wagon_num)

    @on.callback_query(F.data == CB_STEP_BACK)
    async def step_back(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Keeps the form: the step asked again shows it as it stands."""
        await callback.answer()
        target = self.back_to(await load_defect(state), await state.get_data())
        if target:
            await self.wizard.goto(target)

    # After every handler above: aiogram registers a class's own in the order written
    @on.callback_query()
    async def absorb(self, callback: CallbackQuery) -> None:
        """Any other tap dies quietly, as stale_callback does for plain steps."""
        await callback.answer()

    @on.message.exit()
    @on.callback_query.exit()
    async def drop_the_form(
        self, _event: Message | CallbackQuery, state: FSMContext
    ) -> None:
        """exit() only clears the state; the form is ours to drop."""
        await clear_defect_keys(state)
