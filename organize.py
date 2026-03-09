#!/usr/bin/env python3
"""
Convenience entry point — delegates to the file_organizer package CLI.

Prefer the installed command: file-organizer <directory> [options]

Usage:
    python organize.py <directory>             # Organize files
    python organize.py <directory> --dry-run   # Preview changes
    python organize.py <directory> --archive   # Also archive old files
    python organize.py <directory> --duplicates  # Find duplicates
    python organize.py <directory> --recents   # Keep recent files separate
"""

import sys

from file_organizer.cli import main

if __name__ == "__main__":
    sys.exit(main())
