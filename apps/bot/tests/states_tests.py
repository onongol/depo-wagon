"""Tests for the aiogram state groups.

The state string is a storage contract: it is what sits in Redis for every
conversation in flight. Renaming a group or an attribute strands those users,
so the names are pinned here rather than left to drift.

The defect group is pinned as a whole set, not as a count: adding or dropping
a step of the flow has to be a deliberate edit here, and a renamed step cannot
pass by keeping the total the same.
"""

from apps.bot.states import AiChatSG, DefectSG, SupportSG

GROUPS = (DefectSG, SupportSG, AiChatSG)


class TestStateStringsArePinned:
    def test_the_defect_group_is_the_whole_flow(self):
        assert {s.state for s in DefectSG.__states__} == {
            "DefectSG:wagon_num",
            "DefectSG:department",
            "DefectSG:node",
            "DefectSG:part_number",
            "DefectSG:defect_type",
            "DefectSG:severity",
            "DefectSG:photo",
            "DefectSG:responsible_employee",
            "DefectSG:measurement_choice",
            "DefectSG:measurement_dimension",
            "DefectSG:measurement_value",
            "DefectSG:measurement_unit",
            "DefectSG:desc",
            "DefectSG:confirm",
            "DefectSG:saving",
            "DefectSG:employee_verdict",
        }

    def test_the_other_two_conversations_are_single_state(self):
        assert {s.state for s in SupportSG.__states__} == {"SupportSG:message"}
        assert {s.state for s in AiChatSG.__states__} == {"AiChatSG:chatting"}

    def test_groups_do_not_share_a_namespace(self):
        names = {s.state for group in GROUPS for s in group.__states__}

        assert len(names) == sum(len(group.__states__) for group in GROUPS)
