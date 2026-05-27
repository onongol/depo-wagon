from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from apps.bot.constants import BTN_NEW_DEFECT

from apps.bot.states import (
    CONFIRM,
    DEFECT_TYPE,
    DESC,
    EMPLOYEE_VERDICT,
    MEASUREMENT_CHOICE,
    MEASUREMENT_DIMENSION,
    MEASUREMENT_NORM,
    MEASUREMENT_UNIT,
    MEASUREMENT_VALUE,
    NODE,
    PHOTO,
    SEVERITY,
    WAGON_NUM,
)

from .cancel import cancel_defect
from .confirm import confirm_defect
from .defect_type import receive_defect_type
from .description import receive_description
from .measurement import (
    handle_measurement_choice,
    receive_dimension,
    receive_measurement_value,
    receive_norm_value,
    receive_unit,
)
from .node import receive_node
from .photo import receive_photo
from .severity import receive_severity
from .start import new_defect_start
from .verdict import receive_employee_verdict
from .wagon import receive_wagon_number


def get_defect_handler() -> ConversationHandler:
    """Build and return the defect registration ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("new_defect", new_defect_start),
            MessageHandler(
                filters.TEXT & filters.Regex(f"^{str(BTN_NEW_DEFECT)}$"),
                new_defect_start,
            ),
        ],
        states={
            WAGON_NUM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_wagon_number)
            ],
            NODE: [CallbackQueryHandler(receive_node, pattern=r"^node:")],
            DEFECT_TYPE: [
                CallbackQueryHandler(receive_defect_type, pattern=r"^dtype:")
            ],
            SEVERITY: [CallbackQueryHandler(receive_severity, pattern=r"^sev:")],
            PHOTO: [
                MessageHandler(filters.PHOTO, receive_photo),
                CallbackQueryHandler(receive_photo, pattern=r"^photo:skip$"),
            ],
            MEASUREMENT_CHOICE: [
                CallbackQueryHandler(handle_measurement_choice, pattern=r"^meas:"),
            ],
            MEASUREMENT_DIMENSION: [
                CallbackQueryHandler(receive_dimension, pattern=r"^dim:"),
            ],
            MEASUREMENT_VALUE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receive_measurement_value
                ),
            ],
            MEASUREMENT_NORM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_norm_value),
                CallbackQueryHandler(receive_norm_value, pattern=r"^norm:skip$"),
            ],
            MEASUREMENT_UNIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_unit),
                CallbackQueryHandler(receive_unit, pattern=r"^unit:skip$"),
            ],
            DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description),
                CallbackQueryHandler(receive_description, pattern=r"^desc:skip$"),
            ],
            CONFIRM: [CallbackQueryHandler(confirm_defect, pattern=r"^confirm:")],
            EMPLOYEE_VERDICT: [
                CallbackQueryHandler(receive_employee_verdict, pattern=r"^verdict:")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_defect)],
        name="defect",
        persistent=False,
    )
