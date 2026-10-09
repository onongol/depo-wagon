from aiogram.fsm.state import State, StatesGroup


class DefectSG(StatesGroup):
    """Defect registration, in the order the flow walks them."""

    wagon_num = State()
    department = State()
    node = State()
    part_number = State()
    defect_type = State()
    responsible_employee = State()
    photo = State()
    measurement_choice = State()
    desc = State()
    severity = State()
    employee_verdict = State()
    confirm = State()
    saving = State()


class SupportSG(StatesGroup):
    message = State()


class AiChatSG(StatesGroup):
    chatting = State()


ALL_GROUPS = (DefectSG, SupportSG, AiChatSG)
