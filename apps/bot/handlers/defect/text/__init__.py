from .text_confirm import (
    build_ai_analyzing_text,
    build_recommendation_text,
    build_result_messages,
    build_result_text,
    build_save_failed_text,
    build_saving_text,
)
from .text_defect_type import build_ask_defect_type_text, build_edit_defect_type_text
from .text_department import build_ask_department_text
from .text_description import (
    build_ask_description_text,
    build_description_too_long_text,
    build_edit_description_text,
)
from .text_measurement import (
    build_ask_measurement_text,
    build_ask_value_text,
    build_measurement_line,
    build_value_invalid_text,
)
from .text_node import build_ask_node_text, build_edit_node_text
from .text_notifications import build_decommission_alert_text
from .text_part_number import (
    build_ask_part_number_text,
    build_edit_part_number_text,
    build_part_number_too_long_text,
)
from .text_photo import (
    build_album_receiving_text,
    build_ask_more_photos_text,
    build_ask_photo_text,
    build_edit_photos_text,
    build_photo_too_large_text,
    build_photos_attached_toast,
)
from .text_responsible_employee import (
    build_ask_responsible_employee_text,
    build_responsible_employee_search_text,
)
from .text_restart import build_defect_continued_text, build_defect_in_progress_text
from .text_screen import (
    build_editing_heading,
    build_fields,
    build_review_heading,
    build_save_question_text,
    build_screen_text,
    build_step_heading,
    build_stray_input_text,
)
from .text_severity import build_ask_severity_text, build_edit_severity_text
from .text_verdict import build_ask_verdict_text, build_edit_verdict_text
from .text_wagon import (
    build_ask_wagon_text,
    build_edit_wagon_text,
    build_wagon_not_found_text,
)

__all__ = [
    "build_ai_analyzing_text",
    "build_album_receiving_text",
    "build_ask_defect_type_text",
    "build_ask_department_text",
    "build_ask_description_text",
    "build_ask_measurement_text",
    "build_ask_more_photos_text",
    "build_ask_node_text",
    "build_ask_part_number_text",
    "build_ask_photo_text",
    "build_ask_responsible_employee_text",
    "build_ask_severity_text",
    "build_ask_value_text",
    "build_ask_verdict_text",
    "build_ask_wagon_text",
    "build_decommission_alert_text",
    "build_defect_continued_text",
    "build_defect_in_progress_text",
    "build_description_too_long_text",
    "build_edit_defect_type_text",
    "build_edit_description_text",
    "build_edit_node_text",
    "build_edit_part_number_text",
    "build_edit_photos_text",
    "build_edit_severity_text",
    "build_edit_verdict_text",
    "build_edit_wagon_text",
    "build_editing_heading",
    "build_fields",
    "build_measurement_line",
    "build_part_number_too_long_text",
    "build_photo_too_large_text",
    "build_photos_attached_toast",
    "build_recommendation_text",
    "build_responsible_employee_search_text",
    "build_result_messages",
    "build_result_text",
    "build_review_heading",
    "build_save_failed_text",
    "build_save_question_text",
    "build_saving_text",
    "build_screen_text",
    "build_step_heading",
    "build_stray_input_text",
    "build_value_invalid_text",
    "build_wagon_not_found_text",
]
