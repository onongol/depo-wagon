from aiogram import F
from aiogram.enums import ChatType

# Anywhere else, a defect list, a name or an AI answer is read by the whole group
PRIVATE_CHAT = F.chat.type == ChatType.PRIVATE

# A callback has no chat of its own; the message under the button does
PRIVATE_CALLBACK = F.message.chat.type == ChatType.PRIVATE
