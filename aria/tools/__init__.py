"""
Tools package for ARIA agent.
Exposes all available tools and a tool registry helper.
"""

from typing import Dict
from aria.tools.base import BaseTool
from aria.tools.web_search import WebSearchTool
from aria.tools.file_reader import FileReaderTool
from aria.tools.file_writer import FileWriterTool
from aria.tools.notepad import NotepadTool
from aria.tools.text_analyzer import TextAnalyzerTool


def get_default_tools() -> Dict[str, BaseTool]:
    """Instantiate and return the standard tool suite for ARIA."""
    tools = [
        WebSearchTool(),
        FileReaderTool(),
        FileWriterTool(),
        NotepadTool(),
        TextAnalyzerTool(),
    ]
    return {tool.name: tool for tool in tools}


__all__ = [
    "BaseTool",
    "WebSearchTool",
    "FileReaderTool",
    "FileWriterTool",
    "NotepadTool",
    "TextAnalyzerTool",
    "get_default_tools",
]
