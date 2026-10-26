from aiogram.utils.formatting import Bold, Text
from django.utils.translation import gettext_lazy as _

CONNECT_TELEGRAM = Bold(_("Connect Telegram"))

_LINK_GET_NEW = _("Get a new link in the web app via")
GET_NEW_LINK = Text(_LINK_GET_NEW, " ", CONNECT_TELEGRAM, ".")
