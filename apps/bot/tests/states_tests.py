"""Tests for the aiogram state groups.

The state string is a storage contract: it is what sits in Redis for every
conversation in flight. Renaming a group or an attribute strands those users,
so the names are pinned here rather than left to drift.
"""

from apps.bot import states
from apps.bot.states import AiChatSG, DefectSG, SupportSG


class TestStateStringsArePinned:
    def test_defect_states_serialize_by_group_and_attribute(self):
        assert DefectSG.wagon_num.state == "DefectSG:wagon_num"
        assert DefectSG.employee_verdict.state == "DefectSG:employee_verdict"

    def test_support_and_ai_chat(self):
        assert SupportSG.message.state == "SupportSG:message"
        assert AiChatSG.chatting.state == "AiChatSG:chatting"

    def test_groups_do_not_share_a_namespace(self):
        names = {s.state for s in (*DefectSG.__states__, *SupportSG.__states__)}

        assert len(names) == len(DefectSG.__states__) + len(SupportSG.__states__)


class TestEveryPtbStateHasACounterpart:
    """Guards the flow-by-flow conversion against dropping a step."""

    def test_the_defect_group_covers_all_sixteen_ptb_states(self):
        ptb_defect = {
            states.WAGON_NUM,
            states.DEPARTMENT,
            states.NODE,
            states.PART_NUMBER,
            states.DEFECT_TYPE,
            states.SEVERITY,
            states.PHOTO,
            states.RESPONSIBLE_EMPLOYEE,
            states.MEASUREMENT_CHOICE,
            states.MEASUREMENT_DIMENSION,
            states.MEASUREMENT_VALUE,
            states.MEASUREMENT_NORM,
            states.MEASUREMENT_UNIT,
            states.DESC,
            states.CONFIRM,
            states.EMPLOYEE_VERDICT,
        }

        assert len(ptb_defect) == 16
        assert len(DefectSG.__states__) == 16

    def test_the_other_two_conversations_are_single_state(self):
        assert len(SupportSG.__states__) == 1
        assert len(AiChatSG.__states__) == 1
