"""Structural tests for the message catalogue.

Both guards cover mistakes that reading the code does not reveal. A name
declared by two mixins resolves silently in favour of the leftmost, so the
losing string simply stops being sent. A mixin left out of BotMessages fails
only where one of its strings is read.

Both are checked against the source rather than against a hand-kept list, so a
new mixin is covered the moment it lands.
"""

from importlib import import_module
from pathlib import Path

from apps.bot import messages
from apps.bot.messages import BotMessages

MESSAGES_DIR = Path(messages.__file__).parent

CLASSES = [c for c in BotMessages.__mro__ if c is not object]
MIXINS = [c for c in CLASSES if c is not BotMessages]


def _declared_names(cls) -> set[str]:
    return {name for name in vars(cls) if not name.startswith("__")}


class TestMixinNamespaces:
    def test_no_name_is_declared_twice_in_the_mro(self):
        owner: dict[str, str] = {}
        clashes = []

        for cls in CLASSES:
            for name in sorted(_declared_names(cls)):
                if name in owner:
                    clashes.append(f"{name}: {owner[name]} and {cls.__name__}")
                else:
                    owner[name] = cls.__name__

        assert not clashes, "shadowed by MRO order:\n" + "\n".join(clashes)

    def test_every_message_module_is_composed_in(self):
        """A module left out of the bases fails only where its strings are read."""
        declared = {}

        for path in sorted(MESSAGES_DIR.glob("*.py")):
            if path.stem in {"__init__", "composed"}:
                continue

            module = import_module(f"apps.bot.messages.{path.stem}")
            declared.update(
                {
                    name: path.name
                    for name, obj in vars(module).items()
                    if isinstance(obj, type)
                    and name.endswith("Messages")
                    and obj.__module__ == module.__name__
                }
            )

        composed = {cls.__name__ for cls in MIXINS}
        missing = {name: f for name, f in declared.items() if name not in composed}

        assert not missing, f"declared but not in BotMessages: {missing}"
