"""Structural tests for the message catalogue.

Both guards cover mistakes that reading the code does not reveal. A name
declared by two mixins resolves silently in favour of the leftmost, so the
losing string simply stops being sent. A {placeholder} that no .format() fills
raises KeyError at send time, on whichever branch happens to reach it — and
these strings sit mostly on error paths, which is exactly where coverage is
thinnest.

Both are checked against the source rather than against a hand-kept list, so a
new mixin or a new call site is covered the moment it lands.
"""

import ast
import string
from functools import cache
from importlib import import_module
from pathlib import Path

from apps.bot import messages
from apps.bot.messages import BotMessages

MESSAGES_DIR = Path(messages.__file__).parent
BOT_ROOT = MESSAGES_DIR.parent
REPO_ROOT = BOT_ROOT.parents[1]

CLASSES = [c for c in BotMessages.__mro__ if c is not object]
MIXINS = [c for c in CLASSES if c is not BotMessages]


def _declared_names(cls) -> set[str]:
    return {name for name in vars(cls) if not name.startswith("__")}


def _placeholders(text: str) -> set[str]:
    """The {name}s .format() will demand, stripped of any .attr or [index]."""
    return {
        field.split(".")[0].split("[")[0]
        for _, field, _, _ in string.Formatter().parse(text)
        if field
    }


@cache
def _catalogue() -> dict[str, frozenset[str]]:
    """Every message constant in messages/*.py, mapped to its placeholders."""
    found = {}

    for path in sorted(MESSAGES_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))

        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            for node in cls.body:
                if not isinstance(node, ast.Assign):
                    continue

                target = node.targets[0]
                value = node.value

                # gettext_lazy wraps the literal: _("...")
                if isinstance(value, ast.Call) and value.args:
                    value = value.args[0]

                if (
                    isinstance(target, ast.Name)
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                ):
                    found[target.id] = frozenset(_placeholders(value.value))

    return found


@cache
def _sources() -> list[tuple[Path, ast.Module]]:
    """Application modules under apps/bot — tests excluded.

    A test may legitimately hold a template next to its formatted result, which
    would read as an unformatted send.
    """
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(BOT_ROOT.rglob("*.py"))
        if "tests" not in path.parts
    ]


def _where(path: Path, node: ast.AST) -> str:
    return f"{path.relative_to(REPO_ROOT)}:{node.lineno}"


def _unwrap(node: ast.AST) -> ast.AST:
    """str(M.NAME) -> M.NAME."""
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "str"
        and node.args
    ):
        return node.args[0]
    return node


def _parents(tree: ast.Module) -> dict[ast.AST, ast.AST]:
    return {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }


def _format_calls():
    """Yields (path, call node, constant name) for every M.NAME.format(...)."""
    for path, tree in _sources():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not (
                isinstance(node.func, ast.Attribute) and node.func.attr == "format"
            ):
                continue

            target = _unwrap(node.func.value)

            if isinstance(target, ast.Attribute):
                yield path, node, target.attr


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


class TestPlaceholderContract:
    def test_every_format_call_passes_the_names_the_template_asks_for(self):
        catalogue = _catalogue()
        problems = []

        for path, call, name in _format_calls():
            if name not in catalogue:
                continue
            # Positional args and **unpacking cannot be resolved statically.
            if call.args or any(kw.arg is None for kw in call.keywords):
                continue

            given = {kw.arg for kw in call.keywords}
            expected = set(catalogue[name])

            if missing := expected - given:
                problems.append(
                    f"{_where(path, call)}: {name} needs {sorted(missing)} — KeyError"
                )
            if unused := given - expected:
                problems.append(
                    f"{_where(path, call)}: {name} is passed {sorted(unused)}, "
                    f"which the template does not use"
                )

        assert not problems, "\n".join(problems)

    def test_no_template_with_placeholders_is_sent_unformatted(self):
        catalogue = _catalogue()
        templated = {name for name, fields in catalogue.items() if fields}
        problems = []

        for path, tree in _sources():
            parents = _parents(tree)

            for node in ast.walk(tree):
                if not isinstance(node, ast.Attribute) or node.attr not in templated:
                    continue

                parent = parents.get(node)

                if (
                    isinstance(parent, ast.Call)
                    and parent in parents
                    and _unwrap(parent) is not parent
                ):
                    parent = parents[parent]

                formatted = (
                    isinstance(parent, ast.Attribute) and parent.attr == "format"
                )

                if not formatted:
                    problems.append(
                        f"{_where(path, node)}: {node.attr} carries "
                        f"{sorted(catalogue[node.attr])} but is never formatted"
                    )

        assert not problems, "\n".join(problems)

    def test_the_catalogue_is_actually_populated(self):
        """Guards the two tests above against silently scanning nothing."""
        catalogue = _catalogue()

        assert len(catalogue) > 50
        assert any(fields for fields in catalogue.values())
        assert list(_format_calls())
