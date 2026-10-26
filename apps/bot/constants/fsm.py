import enum


class FSMKey(enum.StrEnum):
    """Keys of the chat's FSM data."""

    DEFECT = "defect"
    RESP_SEARCH = "_resp_search"
    LAST_MEDIA_GROUP = "_last_media_group"
    EDITING = "_editing"
    # [chat_id, message_id] of the defect form's one screen
    SCREEN = "_screen"
    AI_CHAT_HISTORY = "_ai_chat_history"
    AI_CHAT_LAST = "_ai_chat_last"


# Everything the defect form keeps, dropped when it ends
DEFECT_FSM_KEYS = frozenset(
    {
        FSMKey.DEFECT,
        FSMKey.RESP_SEARCH,
        FSMKey.LAST_MEDIA_GROUP,
        FSMKey.EDITING,
        FSMKey.SCREEN,
    }
)
