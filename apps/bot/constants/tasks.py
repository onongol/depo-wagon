from apps.defects.constants import DefectStatus

TASKS_PAGE_SIZE = 5

STATUS_TRANSITIONS = {
    DefectStatus.OPEN: (DefectStatus.IN_PROGRESS, DefectStatus.CLOSED),
    DefectStatus.IN_PROGRESS: (DefectStatus.OPEN, DefectStatus.CLOSED),
    DefectStatus.CLOSED: (),
}
