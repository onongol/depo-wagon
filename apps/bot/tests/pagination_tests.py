from apps.bot.handlers.defect.responsible_employee.list import EMPLOYEE_PAGE_SIZE
from apps.bot.utils.pagination import clamp_page


class TestClampPage:
    def test_a_partial_last_page_still_counts(self):
        assert clamp_page(2 * EMPLOYEE_PAGE_SIZE + 1, 0, EMPLOYEE_PAGE_SIZE) == (3, 0)

    def test_a_page_in_range_is_kept(self):
        assert clamp_page(2 * EMPLOYEE_PAGE_SIZE + 1, 1, EMPLOYEE_PAGE_SIZE) == (3, 1)

    def test_a_page_past_the_end_becomes_the_last(self):
        assert clamp_page(EMPLOYEE_PAGE_SIZE + 1, 99, EMPLOYEE_PAGE_SIZE) == (2, 1)

    def test_a_negative_page_becomes_the_first(self):
        assert clamp_page(EMPLOYEE_PAGE_SIZE + 1, -1, EMPLOYEE_PAGE_SIZE) == (2, 0)

    def test_an_empty_list_still_has_one_page(self):
        assert clamp_page(0, 0, EMPLOYEE_PAGE_SIZE) == (1, 0)
