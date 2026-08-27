# Conversation states — defect registration
(
    WAGON_NUM,
    DEPARTMENT,
    NODE,
    PART_NUMBER,
    DEFECT_TYPE,
    SEVERITY,
    MEASUREMENT_CHOICE,
    MEASUREMENT_VALUE,
    PHOTO,
    DESC,
    CONFIRM,
    EMPLOYEE_VERDICT,
    RESPONSIBLE_EMPLOYEE,
) = range(13)

# Measurement sub-steps (separate range to avoid conflicts)
MEASUREMENT_DIMENSION = 30
MEASUREMENT_NORM = 31
MEASUREMENT_UNIT = 32

# No auth states: linking a Telegram account is a single /start carrying a
# deep-link token issued by the web app, so there is nothing to converse about.
# (20 and 21 were the old email/OTP steps — left unused rather than recycled.)

# Support conversation state
SUPPORT_MESSAGE = 40  # Awaiting the user's question to relay to support

# AI chat conversation state
AI_CHAT = 50  # Active AI assistant session
