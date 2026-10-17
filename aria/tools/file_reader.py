"""
File reader tool for reading local files safely.
Supports plain text, markdown, JSON, CSV, and code files.
"""

from pathlib import Path
from aria.tools.base import BaseTool
from aria.config import BASE_DIR, OUTPUT_DIR


class FileReaderTool(BaseTool):
    name = "read_file"
    description = (
        "Read the contents of a local file. Can be relative to workspace or absolute. "
        "Useful for reviewing source materials, data files, or previous reports."
    )
    parameters = {
        "file_path": {
            "type": "string",
            "description": "Path to the file to read.",
        },
        "max_chars": {
            "type": "integer",
            "description": "Maximum number of characters to read (default: 8000 to prevent context overflow).",
        },
    }

    def execute(self, **kwargs) -> str:
        file_path_str = kwargs.get("file_path")
        if not file_path_str:
            return "Error: 'file_path' parameter is required for read_file."

        max_chars = kwargs.get("max_chars", 8000)
        try:
            max_chars = int(max_chars)
        except (ValueError, TypeError):
            max_chars = 8000

        path = Path(file_path_str)
        if not path.is_absolute():
            # Check BASE_DIR first
            candidate = (BASE_DIR / path).resolve()
            if not candidate.exists() and len(path.parts) == 1:
                # If single filename, also check OUTPUT_DIR
                output_candidate = (OUTPUT_DIR / path).resolve()
                if output_candidate.exists():
                    candidate = output_candidate
            path = candidate

        if not path.exists():
            return f"Error: File not found at '{path}'."

        if not path.is_file():
            return f"Error: Path '{path}' is a directory, not a file."

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            total_len = len(content)
            if total_len > max_chars:
                content = content[:max_chars] + f"\n\n[... Truncated: read {max_chars} of {total_len} total characters ...]"
            return f"=== File: {path.name} ({total_len} chars) ===\n{content}"
        except Exception as e:
            return f"Error reading file '{path}': {str(e)}"
