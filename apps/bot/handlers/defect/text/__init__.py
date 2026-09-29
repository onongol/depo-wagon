from .text_defect_type import (
    build_defect_type_confirmed_text,
    build_edit_defect_type_text,
    build_part_number_confirmed_text,
    build_part_number_skipped_text,
    build_responsible_employee_confirmed_text,
    build_responsible_employee_skipped_text,
)
from .text_department import build_department_confirmed_text
from .text_description import (
    build_ask_description_text,
    build_description_added_text,
    build_description_skipped_text,
    build_description_too_long_text,
    build_edit_description_text,
)
from .text_measurement import (
    build_ask_value_text,
    build_measurements_text,
    build_value_invalid_text,
)
from .text_node import build_edit_node_text, build_node_confirmed_text
from .text_part_number import (
    build_edit_part_number_text,
    build_part_number_too_long_text,
)
from .text_photo import (
    build_album_receiving_text,
    build_edit_photos_text,
    build_photo_received_text,
    build_photo_too_large_text,
    build_photos_attached_toast,
)
from .text_responsible_employee import (
    build_ask_responsible_employee_text,
    build_responsible_employee_search_text,
)
from .text_restart import build_defect_continued_text, build_defect_in_progress_text
from .text_start import build_new_defect_text
from .text_summary import build_summary_text
from .text_wagon import (
    build_ask_wagon_text,
    build_edit_wagon_text,
    build_wagon_confirmed_text,
    build_wagon_not_found_text,
)

__all__ = [
    "build_album_receiving_text",
    "build_ask_description_text",
    "build_ask_responsible_employee_text",
    "build_ask_value_text",
    "build_ask_wagon_text",
    "build_defect_continued_text",
    "build_defect_in_progress_text",
    "build_defect_type_confirmed_text",
    "build_department_confirmed_text",
    "build_description_added_text",
    "build_description_skipped_text",
    "build_description_too_long_text",
    "build_edit_defect_type_text",
    "build_edit_description_text",
    "build_edit_node_text",
    "build_edit_part_number_text",
    "build_edit_photos_text",
    "build_edit_wagon_text",
    "build_measurements_text",
    "build_new_defect_text",
    "build_node_confirmed_text",
    "build_part_number_confirmed_text",
    "build_part_number_skipped_text",
    "build_part_number_too_long_text",
    "build_photo_received_text",
    "build_photo_too_large_text",
    "build_photos_attached_toast",
    "build_responsible_employee_confirmed_text",
    "build_responsible_employee_search_text",
    "build_responsible_employee_skipped_text",
    "build_summary_text",
    "build_value_invalid_text",
    "build_wagon_confirmed_text",
    "build_wagon_not_found_text",
]
