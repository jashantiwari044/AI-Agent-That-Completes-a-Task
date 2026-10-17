"""
Base class for ARIA tools.
Every tool inherits from BaseTool and implements execute(**kwargs).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """
        Execute the tool action with the given arguments.
        Must return a string observation suitable for the agent's context.
        """
        pass

    def to_schema_doc(self) -> str:
        """Return a formatted string describing the tool for system prompts."""
        params_str = ", ".join(
            f"{k}: {v.get('type', 'any')} ({v.get('description', '')})"
            for k, v in self.parameters.items()
        )
        return f"- **{self.name}**({params_str}): {self.description}"
