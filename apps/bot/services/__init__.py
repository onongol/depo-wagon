"""
Async service layer: wraps Django ORM calls for use in async PTB handlers.

Modules:
  employee             — employee lookup
  responsible_employee — department employees to pick a defect's responsible from
  telegram_link        — resolve a web-issued deep-link token, then attach the chat
  wagon                — wagon lookup
  defect               — create/update defects, open defects list
  photo                — download defect photos, queue them for storage
  measurement          — create defect measurements

There is no OTP or credentials-email module any more: identity is established
on the web by allauth, and the bot only ever receives a token proving it.
"""

from .defect import (
    create_defect,
    get_open_defects,
    get_open_defects_count,
    save_employee_verdict,
    update_defect_ai_result,
    update_defect_status,
)
from .employee import get_employee_by_telegram_id, get_managers_and_engineers
from .measurement import create_measurements_bulk
from .photo import download_photo, queue_defect_photos
from .responsible_employee import (
    count_department_employees,
    get_department_employee,
    get_department_employees,
)
from .telegram_link import (
    attach_telegram,
    claim_pending_link,
    forget_pending_link,
    get_connect_url,
    remember_pending_link,
    resolve_link_token,
)
from .wagon import get_wagon_by_number

__all__ = [
    "attach_telegram",
    "claim_pending_link",
    "count_department_employees",
    "create_defect",
    "create_measurements_bulk",
    "download_photo",
    "forget_pending_link",
    "get_connect_url",
    "get_department_employee",
    "get_department_employees",
    "get_employee_by_telegram_id",
    "get_managers_and_engineers",
    "get_open_defects",
    "get_open_defects_count",
    "get_wagon_by_number",
    "queue_defect_photos",
    "remember_pending_link",
    "resolve_link_token",
    "save_employee_verdict",
    "update_defect_ai_result",
    "update_defect_status",
]
