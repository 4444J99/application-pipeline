#!/usr/bin/env python3
"""Round-trip YAML mutation using ruamel.yaml.

Replaces regex-based YAML mutations with structure-preserving edits
that maintain comments, key ordering, and quoting style.

Usage:
    from yaml_mutation import YAMLEditor

    editor = YAMLEditor(content)
    editor.set("submission", "materials_attached", ["resume.pdf"])
    editor.set("last_touched", editor.quoted("2026-03-05"))
    editor.append_to_list("follow_up", {"date": "2026-03-05", "channel": "email"})
    new_content = editor.dump()
"""

from datetime import date
from io import StringIO

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import DoubleQuotedScalarString


def _represent_none(representer, data):
    """Always represent None as explicit 'null' (not empty)."""
    return representer.represent_scalar("tag:yaml.org,2002:null", "null")


def _make_yaml() -> YAML:
    """Create a configured round-trip YAML instance."""
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096  # prevent line wrapping
    # Ensure None always dumps as 'null' — empty representation breaks
    # regex-based update_yaml_field which expects 'field: value' format.
    y.representer.add_representer(type(None), _represent_none)
    return y


class YAMLEditor:
    """Round-trip YAML editor preserving comments, key order, and quoting.

    Wraps ruamel.yaml's round-trip loader/dumper for safe structural
    edits (list appending, empty-collection replacement, field insertion)
    that are brittle with regex.
    """

    def __init__(self, content: str):
        self._yaml = _make_yaml()
        self._data = self._yaml.load(content)
        if self._data is None:
            self._data = CommentedMap()

    @property
    def data(self):
        """Access the underlying CommentedMap."""
        return self._data

    def get(self, *keys, default=None):
        """Get a value at a nested key path.

        Returns *default* if any key in the path is missing.
        """
        node = self._data
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node

    def set(self, *keys_and_value):
        """Set a value at a nested key path.

        Last argument is the value; preceding arguments are keys.
        Creates intermediate CommentedMaps as needed.

        Example: editor.set("fit", "composite", 9.2)
        """
        *keys, value = keys_and_value
        if not keys:
            raise ValueError("Need at least one key and a value")
        node = self._data
        for k in keys[:-1]:
            if k not in node or not isinstance(node.get(k), dict):
                node[k] = CommentedMap()
            node = node[k]
        node[keys[-1]] = value

    def setdefault(self, *keys_and_value):
        """Set value only if the field is missing, None, or empty ([] / {}).

        Returns True if the value was set, False if already populated.
        """
        *keys, value = keys_and_value
        current = self.get(*keys)
        if current is None or current == [] or current == {}:
            self.set(*keys_and_value)
            return True
        return False

    def append_to_list(self, *keys_and_item):
        """Append an item to a list field.

        Last argument is the item; preceding arguments are the key path.
        Creates the list if the field is None or empty.
        """
        *keys, item = keys_and_item
        node = self._data
        for k in keys[:-1]:
            if k not in node or not isinstance(node.get(k), dict):
                node[k] = CommentedMap()
            node = node[k]
        field = keys[-1]
        current = node.get(field)
        if current is None or (isinstance(current, list) and len(current) == 0):
            node[field] = CommentedSeq([item])
        elif isinstance(current, list):
            current.append(item)
        else:
            raise ValueError(
                f"Field '{'.'.join(str(k) for k in keys)}' is "
                f"{type(current).__name__}, not list"
            )

    def touch(self):
        """Set last_touched to today's date (double-quoted ISO string)."""
        self._data["last_touched"] = DoubleQuotedScalarString(
            date.today().isoformat()
        )

    @staticmethod
    def quoted(s: str) -> DoubleQuotedScalarString:
        """Wrap a string in double quotes for YAML output."""
        return DoubleQuotedScalarString(s)

    def dump(self) -> str:
        """Dump modified YAML to string, preserving formatting.

        Validates the result with yaml.safe_load to catch corruption.
        """
        stream = StringIO()
        self._yaml.dump(self._data, stream)
        result = stream.getvalue()
        # Validate with PyYAML as safety net
        import yaml

        try:
            yaml.safe_load(result)
        except yaml.YAMLError as e:
            raise ValueError(f"Round-trip YAML dump produced invalid output: {e}")
        return result
