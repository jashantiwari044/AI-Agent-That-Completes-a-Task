"""
File writer tool for writing or appending contents to files.
Saves generated reports, notes, or data safely.
"""

from pathlib import Path
from aria.tools.base import BaseTool
from aria.config import BASE_DIR, OUTPUT_DIR


class FileWriterTool(BaseTool):
    name = "write_file"
    description = (
        "Write text content to a file on disk. If only a filename is given, saves inside 'output/' directory. "
        "Supports 'write' (overwrite/create) or 'append' mode."
    )
    parameters = {
        "file_path": {
            "type": "string",
            "description": "Path or filename to write to (e.g., 'quantum_report.md' or 'output/summary.txt').",
        },
        "content": {
            "type": "string",
            "description": "The exact text content to write into the file.",
        },
        "mode": {
            "type": "string",
            "description": "'write' to overwrite/create new, or 'append' to add to existing file (default: 'write').",
        },
    }

    def execute(self, **kwargs) -> str:
        file_path_str = kwargs.get("file_path")
        content = kwargs.get("content")
        mode = kwargs.get("mode", "write").lower().strip()

        if not file_path_str:
            return "Error: 'file_path' parameter is required for write_file."
        if content is None:
            return "Error: 'content' parameter is required for write_file."

        path = Path(file_path_str)
        # If relative and doesn't specify directory, place in OUTPUT_DIR
        if not path.is_absolute():
            if len(path.parts) == 1:
                path = OUTPUT_DIR / path
            else:
                path = (BASE_DIR / path).resolve()

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if mode == "append" and path.exists():
                with open(path, "a", encoding="utf-8") as f:
                    f.write("\n" + content)
                return f"Successfully appended {len(content)} characters to '{path.relative_to(BASE_DIR)}'."
            else:
                path.write_text(content, encoding="utf-8")
                return f"Successfully wrote {len(content)} characters to '{path.relative_to(BASE_DIR)}'."
        except Exception as e:
            return f"Error writing to file '{path}': {str(e)}"
