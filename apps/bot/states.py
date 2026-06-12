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

# Auth conversation states
AUTH_EMAIL = 20  # Step 1: ask for email
AUTH_OTP = 21  # Step 2: enter OTP code received by email

# Support conversation state
SUPPORT_MESSAGE = 40  # Awaiting the user's question to relay to support
