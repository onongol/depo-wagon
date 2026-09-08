"""Conversation states.

Two sets live here during the aiogram migration. The integers below are what
PTB's ConversationHandler still runs on; the StatesGroups at the bottom are
what replaces them, flow by flow. The integers go when the last router moves.

A StatesGroup serializes as "ClassName:attribute", and that string is what sits
in Redis. Renaming a class or an attribute therefore invalidates every
conversation in flight — those users land on no handler until they /cancel.
"""

from aiogram.fsm.state import State, StatesGroup

# Conversation states — defect registration
(
    WAGON_NUM,
    DEPARTMENT,
    NODE,
    PART_NUMBER,
    DEFECT_TYPE,
    SEVERITY,
    MEASUREMENT_CHOICE,
    MEASUREMENT_VALUE,
    PHOTO,
    DESC,
    CONFIRM,
    EMPLOYEE_VERDICT,
    RESPONSIBLE_EMPLOYEE,
) = range(13)

# Measurement sub-steps (separate range to avoid conflicts)
MEASUREMENT_DIMENSION = 30
MEASUREMENT_NORM = 31
MEASUREMENT_UNIT = 32

# No auth states: linking a Telegram account is a single /start carrying a
# deep-link token issued by the web app, so there is nothing to converse about.
# (20 and 21 were the old email/OTP steps — left unused rather than recycled.)

# Support conversation state
SUPPORT_MESSAGE = 40  # Awaiting the user's question to relay to support

# AI chat conversation state
AI_CHAT = 50  # Active AI assistant session


class DefectSG(StatesGroup):
    """Defect registration, in the order the flow walks them."""

    wagon_num = State()
    department = State()
    node = State()
    part_number = State()
    defect_type = State()
    severity = State()
    photo = State()
    responsible_employee = State()
    measurement_choice = State()
    measurement_dimension = State()
    measurement_value = State()
    measurement_norm = State()
    measurement_unit = State()
    desc = State()
    confirm = State()
    employee_verdict = State()


class SupportSG(StatesGroup):
    message = State()


class AiChatSG(StatesGroup):
    chatting = State()
