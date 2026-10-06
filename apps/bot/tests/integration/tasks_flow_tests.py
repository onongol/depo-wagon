"""List → card → picker → confirmation → saved, through a real Dispatcher."""

import uuid

import pytest
from asgiref.sync import sync_to_async
from model_bakery import baker

from apps.bot.callback_data import (
    DefectCardCB,
    DefectOpenCB,
    StatusAskCB,
    StatusPickCB,
    StatusSetCB,
)
from apps.bot.constants import STATUS_LABEL
from apps.bot.handlers.tasks.text import (
    build_status_changed_toast,
    build_status_refused_toast,
)
from apps.bot.tests.builders import payloads
from apps.bot.tests.integration.conftest import (
    USER_ID,
    make_callback_update,
    make_message_update,
)
from apps.bot.utils.unregistered import build_not_registered_text
from apps.core.constants import EmployeeRole
from apps.defects.constants import DefectStatus
from apps.defects.models import Defect

make = sync_to_async(baker.make)


async def _status(defect_id) -> str:
    return (await sync_to_async(Defect.objects.get)(pk=defect_id)).status


@pytest.fixture
async def own_defect():
    inspector = await make(
        "core.Employee", role=EmployeeRole.INSPECTOR, telegram_id=USER_ID
    )
    wagon = await make("core.Wagon", number="60123456", manufacture_year=2000)
    return await make(
        "defects.Defect", wagon=wagon, inspector=inspector, status=DefectStatus.OPEN
    )


async def _tap(dp, bot, session, payload: str):
    session.clear()
    await dp.feed_update(bot, make_callback_update(payload))
    [edit] = session.calls("editMessageText")
    [answer] = session.calls("answerCallbackQuery")
    return edit, answer


@pytest.mark.django_db(transaction=True)
async def test_closing_a_defect_from_its_card(dp, bot, session, own_defect):
    await dp.feed_update(bot, make_message_update("/my_tasks", command=True))
    [listing] = session.calls("sendMessage")
    [open_card] = payloads(listing.reply_markup, DefectCardCB)

    card, _ = await _tap(dp, bot, session, open_card)
    assert "60123456" in card.text
    [change] = payloads(card.reply_markup, StatusPickCB)

    picker, _ = await _tap(dp, bot, session, change)
    asks = {
        StatusAskCB.unpack(p).status: p
        for p in payloads(picker.reply_markup, StatusAskCB)
    }
    assert set(asks) == {DefectStatus.IN_PROGRESS, DefectStatus.CLOSED}

    confirm, _ = await _tap(dp, bot, session, asks[DefectStatus.CLOSED])
    assert await _status(own_defect.pk) == DefectStatus.OPEN
    [save] = payloads(confirm.reply_markup, StatusSetCB)

    card, answer = await _tap(dp, bot, session, save)
    assert await _status(own_defect.pk) == DefectStatus.CLOSED
    assert answer.text == build_status_changed_toast(DefectStatus.CLOSED)
    assert not answer.show_alert
    assert str(STATUS_LABEL[DefectStatus.CLOSED]) in card.text
    assert payloads(card.reply_markup, StatusPickCB) == []


@pytest.mark.django_db(transaction=True)
async def test_an_old_button_cannot_reopen_a_closed_defect(
    dp, bot, session, own_defect
):
    await sync_to_async(own_defect.set_status)(DefectStatus.CLOSED)
    reopen = StatusSetCB(
        defect_id=own_defect.pk, status=DefectStatus.IN_PROGRESS, page=0
    ).pack()

    _, answer = await _tap(dp, bot, session, reopen)

    assert answer.text == build_status_refused_toast()
    assert answer.show_alert
    assert await _status(own_defect.pk) == DefectStatus.CLOSED


@pytest.mark.django_db(transaction=True)
async def test_a_card_opens_on_an_inaccessible_message(dp, bot, session, own_defect):
    open_card = DefectCardCB(defect_id=own_defect.pk, page=0).pack()

    await dp.feed_update(bot, make_callback_update(open_card, inaccessible=True))

    [card] = session.calls("editMessageText")
    assert "60123456" in card.text


@pytest.mark.django_db(transaction=True)
async def test_a_deleted_list_gets_the_card_anew(dp, bot, session, own_defect):
    session.refuse("editMessageText", "Bad Request: message to edit not found")
    open_card = DefectCardCB(defect_id=own_defect.pk, page=0).pack()

    await dp.feed_update(bot, make_callback_update(open_card))

    [card] = session.calls("sendMessage")
    assert "60123456" in card.text
    assert payloads(card.reply_markup, StatusPickCB)


@pytest.mark.django_db(transaction=True)
async def test_a_chat_linked_to_nobody_is_refused_the_card(dp, bot, session):
    open_card = DefectCardCB(defect_id=uuid.uuid4(), page=0).pack()

    await dp.feed_update(bot, make_callback_update(open_card))

    [edit] = session.calls("editMessageText")
    assert edit.text == build_not_registered_text().render()[0]


@pytest.mark.django_db(transaction=True)
async def test_a_card_opened_from_a_notification_comes_under_it(
    dp, bot, session, own_defect
):
    open_card = DefectOpenCB(defect_id=own_defect.pk).pack()

    await dp.feed_update(bot, make_callback_update(open_card))

    assert session.calls("editMessageText") == []
    [card] = session.calls("sendMessage")
    assert "60123456" in card.text
    assert payloads(card.reply_markup, StatusPickCB)
