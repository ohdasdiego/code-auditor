"""
Language detection and extension mapping.
"""

from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}


def detect_language(file_path: Path) -> str:
    return SUPPORTED_EXTENSIONS.get(file_path.suffix.lower(), "unknown")
