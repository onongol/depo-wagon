from apps.defects.constants import DefectSeverity, DefectStatus, DefectVerdict

# Labels come from the TextChoices; apps.bot.utils.choices puts the two together
SEVERITY_EMOJI = {
    DefectSeverity.LOW: "🟢",
    DefectSeverity.MEDIUM: "🟡",
    DefectSeverity.HIGH: "🟠",
    DefectSeverity.CRITICAL: "🔴",
}

VERDICT_EMOJI = {
    DefectVerdict.OK: "✅",
    DefectVerdict.REPAIR_SOON: "🟡",
    DefectVerdict.REPAIR_NOW: "🟠",
    DefectVerdict.DECOMMISSION: "🔴",
}

STATUS_EMOJI = {
    DefectStatus.OPEN: "🔵",
    DefectStatus.IN_PROGRESS: "🟡",
    DefectStatus.CLOSED: "🟢",
}
