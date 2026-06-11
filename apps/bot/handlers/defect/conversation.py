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
from .description import receive_description, skip_description
from .measurement import (
    handle_measurement_choice,
    receive_dimension,
    receive_measurement_value,
    receive_norm_value,
    receive_unit,
    skip_norm_value,
    skip_unit,
)
from .node import receive_node
from .part_number import receive_part_number, skip_part_number
from .photo import receive_photo, skip_photo
from .responsible_employee import (
    receive_responsible_employee,
    search_responsible_employee,
)
from .severity import receive_severity
from .start import new_defect_start
from .verdict import receive_employee_verdict
from .wagon import receive_wagon_number


def _match(*types):
    return lambda obj: isinstance(obj, types)


def get_defect_handler() -> ConversationHandler:
    """Build and return the defect registration ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("new_defect", new_defect_start),
            MessageHandler(filters.Text(str(BTN_NEW_DEFECT)), new_defect_start),
        ],
        states={
            WAGON_NUM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_wagon_number)
            ],
            DEPARTMENT: [
                CallbackQueryHandler(receive_department, pattern=_match(DepartmentCB))
            ],
            NODE: [CallbackQueryHandler(receive_node, pattern=_match(NodeCB))],
            PART_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_part_number),
                CallbackQueryHandler(
                    skip_part_number, pattern=_match(PartNumberSkipCB)
                ),
            ],
            DEFECT_TYPE: [
                CallbackQueryHandler(receive_defect_type, pattern=_match(DefectTypeCB))
            ],
            SEVERITY: [
                CallbackQueryHandler(receive_severity, pattern=_match(SeverityCB))
            ],
            PHOTO: [
                MessageHandler(filters.PHOTO, receive_photo),
                CallbackQueryHandler(skip_photo, pattern=_match(PhotoSkipCB)),
            ],
            RESPONSIBLE_EMPLOYEE: [
                CallbackQueryHandler(
                    receive_responsible_employee,
                    pattern=_match(
                        ResponsibleEmployeeCB,
                        ResponsibleEmployeeSkipCB,
                        ResponsibleEmployeePageCB,
                    ),
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, search_responsible_employee
                ),
            ],
            MEASUREMENT_CHOICE: [
                CallbackQueryHandler(
                    handle_measurement_choice,
                    pattern=_match(
                        MeasurementAddCB, MeasurementSkipCB, MeasurementDoneCB
                    ),
                ),
            ],
            MEASUREMENT_DIMENSION: [
                CallbackQueryHandler(receive_dimension, pattern=_match(DimensionCB)),
            ],
            MEASUREMENT_VALUE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receive_measurement_value
                ),
            ],
            MEASUREMENT_NORM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_norm_value),
                CallbackQueryHandler(skip_norm_value, pattern=_match(NormSkipCB)),
            ],
            MEASUREMENT_UNIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_unit),
                CallbackQueryHandler(skip_unit, pattern=_match(UnitSkipCB)),
            ],
            DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description),
                CallbackQueryHandler(skip_description, pattern=_match(DescSkipCB)),
            ],
            CONFIRM: [CallbackQueryHandler(confirm_defect, pattern=_match(ConfirmCB))],
            EMPLOYEE_VERDICT: [
                CallbackQueryHandler(
                    receive_employee_verdict, pattern=_match(VerdictCB)
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
