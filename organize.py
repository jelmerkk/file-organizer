#!/usr/bin/env python3
"""
File Organizer - Automatically organize files into categorized folders.

This script scans a directory and moves files into subfolders based on their
file extension. It's useful for cleaning up messy folders like Downloads.

SAFETY POLICY:
    This script NEVER deletes files. It only moves them.
    - Files are moved to category subfolders (Images/, Documents/, etc.)
    - Large files (>1 GB) are moved to _LargeFiles/ for easy review
    - Old files can be moved to an _Archive/ folder
    - If a file already exists at destination, a timestamp is added to the name
    - Use --dry-run to preview changes before applying them
    
    EXCEPTION: .ica files (Citrix session files) are deleted after 1 day.
    These are temporary files that serve no purpose after the session ends.

Usage:
    python organize.py <directory>                    # Organize files
    python organize.py <directory> --dry-run          # Preview changes
    python organize.py <directory> --archive          # Also archive old files
    python organize.py <directory> --duplicates       # Find duplicates
    python organize.py <directory> --recents          # Keep recent files separate

Example:
    python organize.py ~/Downloads --dry-run  # See what would happen
    python organize.py ~/Downloads            # Actually organize the files
    python organize.py ~/Downloads --archive  # Organize and archive old files
"""

import sys

from file_organizer.cli import main

if __name__ == "__main__":
    sys.exit(main())
