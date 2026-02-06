"""
File Organizer - Automatically organize files into categorized folders.

This package provides tools to organize files by extension, detect duplicates,
archive old files, and more.
"""

from .config import Config
from .operations import (
    organize_files,
    archive_old_files,
    cleanup_temp_files,
    find_duplicates,
    handle_duplicates,
)

__version__ = "1.0.0"
__all__ = [
    "Config",
    "organize_files",
    "archive_old_files", 
    "cleanup_temp_files",
    "find_duplicates",
    "handle_duplicates",
]
