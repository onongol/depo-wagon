"""
Tasks handlers — paginated defect list with status management.

Modules:
  constants — PAGE_SIZE, labels, status options
  utils     — shared helpers: get_employee, build_text, keyboards
  list      — /my_tasks command handler
  status    — status picker + status update handlers
  handlers  — get_tasks_handlers() registration
"""

from .handlers import get_tasks_handlers
from .list import my_tasks

__all__ = [
    "get_tasks_handlers",
    "my_tasks",
]
