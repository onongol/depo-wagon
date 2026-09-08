from apps.bot import services


async def get_employee(user_id: int):
    """Return the active employee this Telegram account belongs to, or None.

    Read on every update rather than cached: disconnecting or deactivating
    someone on the web has to reach the bot at once, and a copy held in
    conversation state would outlive that until the process restarts.
    """
    return await services.get_employee_by_telegram_id(user_id)
