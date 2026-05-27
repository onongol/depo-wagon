"""
Async service layer: wraps Django ORM calls for use in async PTB handlers.

Modules:
  employee    — get/register/link employees
  wagon       — wagon lookup
  defect      — create/update defects, open defects list
  photo       — save defect photos to storage
  measurement — create defect measurements
  email       — OTP generation/verification + email sending
"""

from .defect import (
    create_defect,
    get_open_defects,
    get_open_defects_count,
    save_employee_verdict,
    update_defect_ai_result,
    update_defect_status,
)
from .email import (
    generate_and_store_otp,
    send_credentials_email,
    send_otp_email,
    verify_otp,
)
from .employee import (
    get_employee_by_email,
    get_employee_by_id,
    get_employee_by_telegram_id,
    get_managers_and_engineers,
    link_employee_telegram,
    register_employee,
)
from .measurement import create_measurement
from .photo import create_photo_from_bytes
from .wagon import get_wagon_by_number

__all__ = [
    # employee
    "get_employee_by_id",
    "get_employee_by_email",
    "get_employee_by_telegram_id",
    "get_managers_and_engineers",
    "register_employee",
    "link_employee_telegram",
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
    # email
    "generate_and_store_otp",
    "verify_otp",
    "send_otp_email",
    "send_credentials_email",
]
