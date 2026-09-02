"""
Async service layer: wraps Django ORM calls for use in async PTB handlers.

Modules:
  employee      — employee lookup
  telegram_link — resolve a web-issued deep-link token, then attach the chat
  login_link    — one-time web sign-in links sent over Telegram
  wagon         — wagon lookup
  defect        — create/update defects, open defects list
  photo         — save defect photos to storage
  measurement   — create defect measurements

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
from .employee import (
    get_employee_by_email,
    get_employee_by_id,
    get_employee_by_telegram_id,
    get_employee_for_auth,
    get_employees_by_department,
    get_managers_and_engineers,
    link_employee_telegram,
)
from .login_link import build_login_link, get_connect_url
from .measurement import create_measurement, create_measurements_bulk
from .photo import create_photo_from_bytes
from .telegram_link import attach_telegram, resolve_link_token
from .wagon import get_wagon_by_number

__all__ = [
    # employee
    "get_employee_by_id",
    "get_employee_by_email",
    "get_employee_by_telegram_id",
    "get_employee_for_auth",
    "get_employees_by_department",
    "get_managers_and_engineers",
    "link_employee_telegram",
    # telegram linking
    "resolve_link_token",
    "attach_telegram",
    # login link
    "build_login_link",
    "get_connect_url",
    # wagon
    "get_wagon_by_number",
    # defect
    "create_defect",
    "update_defect_ai_result",
    "update_defect_status",
    "save_employee_verdict",
    "get_open_defects",
    "get_open_defects_count",
    # photo
    "create_photo_from_bytes",
    # measurement
    "create_measurement",
    "create_measurements_bulk",
]
