"""
Notepad tool for agent scratchpad and working memory.
Enables the agent to save intermediate findings, keep a research plan,
and retrieve notes across reasoning steps.
"""

from typing import Dict
from aria.tools.base import BaseTool


class NotepadTool(BaseTool):
    name = "notepad"
    description = (
        "Agent's working memory scratchpad. Store key findings, maintain a research checklist, "
        "or retrieve previously saved notes. Actions: 'set' (save note), 'get' (retrieve note), "
        "'list' (show all note keys), 'clear' (empty memory)."
    )
    parameters = {
        "action": {
            "type": "string",
            "description": "One of: 'set', 'get', 'list', 'clear'.",
        },
        "key": {
            "type": "string",
            "description": "Identifier for the note (e.g., 'plan', 'key_findings', 'citations').",
        },
        "value": {
            "type": "string",
            "description": "The content to store when action is 'set'.",
        },
    }

    def __init__(self):
        super().__init__()
        self._memory: Dict[str, str] = {}

    def execute(self, **kwargs) -> str:
        action = kwargs.get("action", "list").lower().strip()
        key = kwargs.get("key", "").strip()
        value = kwargs.get("value", "")

        if action == "set":
            if not key:
                return "Error: 'key' is required to set a note."
            self._memory[key] = str(value)
            return f"Notepad: Saved note under key '{key}' ({len(str(value))} chars)."

        elif action == "get":
            if not key:
                return "Error: 'key' is required to retrieve a note."
            if key not in self._memory:
                available = ", ".join(self._memory.keys()) if self._memory else "none"
                return f"Notepad: Key '{key}' not found. Available keys: {available}."
            return f"=== Notepad [{key}] ===\n{self._memory[key]}"

        elif action == "list":
            if not self._memory:
                return "Notepad is currently empty."
            items = [f"- '{k}': {len(v)} chars" for k, v in self._memory.items()]
            return "=== Notepad Contents ===\n" + "\n".join(items)

        elif action == "clear":
            count = len(self._memory)
            self._memory.clear()
            return f"Notepad: Cleared {count} notes."

        else:
            return f"Error: Unknown action '{action}'. Valid actions are 'set', 'get', 'list', 'clear'."
