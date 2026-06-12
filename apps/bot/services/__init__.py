"""
Async service layer: wraps Django ORM calls for use in async PTB handlers.

Modules:
  employee    — get/register/link employees
  wagon       — wagon lookup
  defect      — create/update defects, open defects list
  photo       — save defect photos to storage
  measurement — create defect measurements
  otp         — OTP generation/verification in Redis
  email       — OTP/credentials email sending
"""

from .defect import (
    create_defect,
    get_open_defects,
    get_open_defects_count,
    save_employee_verdict,
    update_defect_ai_result,
    update_defect_status,
)
from .email import send_credentials_email, send_otp_email
from .otp import generate_and_store_otp, verify_otp
from .employee import (
    get_employee_by_email,
    get_employee_by_id,
    get_employee_by_telegram_id,
    get_employee_for_auth,
    get_employees_by_department,
    get_managers_and_engineers,
    link_employee_telegram,
    register_employee,
)
from .measurement import create_measurement, create_measurements_bulk
from .photo import create_photo_from_bytes
from .wagon import get_wagon_by_number

__all__ = [
    # employee
    "get_employee_by_id",
    "get_employee_by_email",
    "get_employee_by_telegram_id",
    "get_employee_for_auth",
    "get_employees_by_department",
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
    "create_measurements_bulk",
    # email
    "generate_and_store_otp",
    "verify_otp",
    "send_otp_email",
    "send_credentials_email",
]
