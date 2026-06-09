from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from apps.bot.callbacks import (
    ConfirmCB,
    DefectTypeCB,
    DepartmentCB,
    DescSkipCB,
    DimensionCB,
    MeasurementAddCB,
    MeasurementDoneCB,
    MeasurementSkipCB,
    NodeCB,
    NormSkipCB,
    PartNumberSkipCB,
    PhotoSkipCB,
    ResponsibleEmployeeCB,
    ResponsibleEmployeePageCB,
    ResponsibleEmployeeSkipCB,
    SeverityCB,
    UnitSkipCB,
    VerdictCB,
)
from apps.bot.constants import BTN_NEW_DEFECT
from apps.bot.states import (
    CONFIRM,
    DEFECT_TYPE,
    DEPARTMENT,
    DESC,
    EMPLOYEE_VERDICT,
    MEASUREMENT_CHOICE,
    MEASUREMENT_DIMENSION,
    MEASUREMENT_NORM,
    MEASUREMENT_UNIT,
    MEASUREMENT_VALUE,
    NODE,
    PART_NUMBER,
    PHOTO,
    RESPONSIBLE_EMPLOYEE,
    SEVERITY,
    WAGON_NUM,
)

from .cancel import cancel_defect, stale_callback
from .confirm import confirm_defect
from .defect_type import receive_defect_type
from .department import receive_department
from .description import receive_description
from .measurement import (
    handle_measurement_choice,
    receive_dimension,
    receive_measurement_value,
    receive_norm_value,
    receive_unit,
)
from .node import receive_node
from .part_number import receive_part_number
from .photo import receive_photo
from .responsible_employee import (
    receive_responsible_employee,
    search_responsible_employee,
)
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
                filters.Text(str(BTN_NEW_DEFECT)),
                new_defect_start,
            ),
        ],
        states={
            WAGON_NUM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_wagon_number)
            ],
            DEPARTMENT: [
                CallbackQueryHandler(
                    receive_department, pattern=lambda d: isinstance(d, DepartmentCB)
                )
            ],
            NODE: [
                CallbackQueryHandler(
                    receive_node, pattern=lambda d: isinstance(d, NodeCB)
                )
            ],
            PART_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_part_number),
                CallbackQueryHandler(
                    receive_part_number,
                    pattern=lambda d: isinstance(d, PartNumberSkipCB),
                ),
            ],
            DEFECT_TYPE: [
                CallbackQueryHandler(
                    receive_defect_type, pattern=lambda d: isinstance(d, DefectTypeCB)
                )
            ],
            SEVERITY: [
                CallbackQueryHandler(
                    receive_severity, pattern=lambda d: isinstance(d, SeverityCB)
                )
            ],
            PHOTO: [
                MessageHandler(filters.PHOTO, receive_photo),
                CallbackQueryHandler(
                    receive_photo, pattern=lambda d: isinstance(d, PhotoSkipCB)
                ),
            ],
            RESPONSIBLE_EMPLOYEE: [
                CallbackQueryHandler(
                    receive_responsible_employee,
                    pattern=lambda d: isinstance(
                        d,
                        (
                            ResponsibleEmployeeCB,
                            ResponsibleEmployeeSkipCB,
                            ResponsibleEmployeePageCB,
                        ),
                    ),
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, search_responsible_employee
                ),
            ],
            MEASUREMENT_CHOICE: [
                CallbackQueryHandler(
                    handle_measurement_choice,
                    pattern=lambda d: isinstance(
                        d, (MeasurementAddCB, MeasurementSkipCB, MeasurementDoneCB)
                    ),
                ),
            ],
            MEASUREMENT_DIMENSION: [
                CallbackQueryHandler(
                    receive_dimension, pattern=lambda d: isinstance(d, DimensionCB)
                ),
            ],
            MEASUREMENT_VALUE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receive_measurement_value
                ),
            ],
            MEASUREMENT_NORM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_norm_value),
                CallbackQueryHandler(
                    receive_norm_value, pattern=lambda d: isinstance(d, NormSkipCB)
                ),
            ],
            MEASUREMENT_UNIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_unit),
                CallbackQueryHandler(
                    receive_unit, pattern=lambda d: isinstance(d, UnitSkipCB)
                ),
            ],
            DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description),
                CallbackQueryHandler(
                    receive_description, pattern=lambda d: isinstance(d, DescSkipCB)
                ),
            ],
            CONFIRM: [
                CallbackQueryHandler(
                    confirm_defect, pattern=lambda d: isinstance(d, ConfirmCB)
                )
            ],
            EMPLOYEE_VERDICT: [
                CallbackQueryHandler(
                    receive_employee_verdict, pattern=lambda d: isinstance(d, VerdictCB)
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_defect),
            CallbackQueryHandler(stale_callback),
        ],
        name="defect",
        persistent=False,
    )
