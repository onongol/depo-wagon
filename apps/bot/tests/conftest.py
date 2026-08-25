from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_update():
    """Fixture to create a mock update object."""
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    update.effective_user.id = 12345
    return update


@pytest.fixture
def mock_context():
    """Fixture to create a mock context object."""
    context = MagicMock()
    context.user_data = {}
    return context
