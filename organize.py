#!/usr/bin/env python3
"""
File Organizer - Automatically organize files into categorized folders.

This script scans a directory and moves files into subfolders based on their
file extension. It's useful for cleaning up messy folders like Downloads.

SAFETY POLICY:
    This script NEVER deletes files. It only moves them.
    - Files are moved to category subfolders (Images/, Documents/, etc.)
    - Old files can be moved to an _Archive/ folder
    - If a file already exists at destination, a timestamp is added to the name
    - Use --dry-run to preview changes before applying them
    
    EXCEPTION: .ica files (Citrix session files) are deleted after 1 day.
    These are temporary files that serve no purpose after the session ends.

Usage:
    python organize.py <directory>           # Organize files in directory
    python organize.py <directory> --dry-run # Preview changes without moving files
    python organize.py <directory> --archive # Also move files older than 30 days to _Archive/

Example:
    python organize.py ~/Downloads --dry-run  # See what would happen
    python organize.py ~/Downloads            # Actually organize the files
    python organize.py ~/Downloads --archive  # Organize and archive old files

Learning Notes:
    - We use `pathlib.Path` instead of `os.path` for cleaner path handling
    - The `argparse` module makes it easy to build CLI tools with help text
    - `shutil.move()` handles moving files across different filesystems
    - Sets (using {}) give O(1) lookup time for checking file extensions
"""

# =============================================================================
# IMPORTS
# =============================================================================
# Standard library imports - these come with Python, no installation needed

import sys          # System-specific functions (like exit codes)
import shutil       # High-level file operations (move only - we NEVER delete!)
import argparse     # Command-line argument parsing
from pathlib import Path      # Object-oriented filesystem paths (modern way)
from datetime import datetime, timedelta  # Date/time handling

# Note: We don't actually use 'os' - pathlib.Path replaces most of its functionality

# =============================================================================
# SAFETY CONFIGURATION
# =============================================================================

# IMPORTANT: This script NEVER deletes files. Only moves.
# This is an intentional design decision for safety.
#
# EXCEPTION: Temporary files listed in AUTO_DELETE_EXTENSIONS are deleted
# after AUTO_DELETE_AGE_DAYS. These are files that serve no purpose after
# a short time (e.g., Citrix session files).

# Number of days after which a file is considered "old" and eligible for archiving
ARCHIVE_AGE_DAYS = 30

# Name of the archive folder (prefixed with _ to sort it separately)
ARCHIVE_FOLDER = "_Archive"

# =============================================================================
# AUTO-DELETE CONFIGURATION (Exception to the no-delete rule)
# =============================================================================

# File extensions that are safe to delete after a certain age
# These are temporary files that have no value after their initial use
AUTO_DELETE_EXTENSIONS = {
    ".ica",  # Citrix ICA session files - temporary, useless after session ends
}

# How old (in days) before auto-deletable files are removed
AUTO_DELETE_AGE_DAYS = 1

# =============================================================================
# CONFIGURATION
# =============================================================================

# File extension to category mapping
# This is a dictionary where:
#   - Keys are folder names (strings)
#   - Values are sets of file extensions (sets give fast lookup)
#
# Why sets instead of lists?
#   - Checking "is .jpg in this set?" is O(1) constant time with sets
#   - With lists it would be O(n) - slower as the list grows
#
# To add new categories or extensions, just edit this dictionary!
CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff", ".heic"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
    "Video": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yml", ".yaml", ".md", ".sh", ".c", ".cpp", ".h", ".java", ".go", ".rs"},
    "Executables": {".exe", ".msi", ".dmg", ".app", ".deb", ".rpm"},
    "Fonts": {".ttf", ".otf", ".woff", ".woff2"},
}

# =============================================================================
# FUNCTIONS
# =============================================================================


def get_file_age_days(file_path: Path) -> int:
    """
    Get the age of a file in days based on its modification time.
    
    Why modification time (mtime) instead of creation time?
        - mtime is more reliable across different filesystems
        - It reflects when the file was last changed, which is usually more relevant
        - Creation time (ctime) behaves differently on Unix vs Windows
    
    Args:
        file_path: Path to the file
        
    Returns:
        Number of days since the file was last modified
        
    Example:
        >>> get_file_age_days(Path("old_file.txt"))
        45  # File was modified 45 days ago
    """
    # .stat() returns file metadata (size, timestamps, permissions, etc.)
    # .st_mtime = modification time as Unix timestamp (seconds since 1970)
    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
    
    # Calculate the difference between now and the modification time
    age = datetime.now() - mtime
    
    # .days gives us just the day component of the timedelta
    return age.days


def is_old_file(file_path: Path, days: int = ARCHIVE_AGE_DAYS) -> bool:
    """
    Check if a file is older than the specified number of days.
    
    Args:
        file_path: Path to the file
        days: Age threshold in days (default: ARCHIVE_AGE_DAYS = 30)
        
    Returns:
        True if file is older than the threshold, False otherwise
    """
    return get_file_age_days(file_path) > days


def is_auto_deletable(file_path: Path) -> bool:
    """
    Check if a file is eligible for automatic deletion.
    
    Only specific file types (defined in AUTO_DELETE_EXTENSIONS) that are
    older than AUTO_DELETE_AGE_DAYS qualify for deletion. This is a narrow
    exception to our "never delete" policy for truly temporary files.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if file should be auto-deleted, False otherwise
    """
    ext = file_path.suffix.lower()
    return ext in AUTO_DELETE_EXTENSIONS and get_file_age_days(file_path) > AUTO_DELETE_AGE_DAYS


def cleanup_temp_files(directory: Path, dry_run: bool = False) -> dict:
    """
    Delete temporary files that are older than AUTO_DELETE_AGE_DAYS.
    
    This is the ONLY function in this script that deletes files.
    It only affects files with extensions in AUTO_DELETE_EXTENSIONS
    (currently just .ica Citrix session files).
    
    Why delete these?
        - .ica files are Citrix session launchers
        - They're downloaded every time you start a Citrix session
        - They contain session-specific data that's useless after the session
        - They pile up quickly in Downloads folders
    
    Args:
        directory: Path to scan for deletable files
        dry_run: If True, only preview what would be deleted
        
    Returns:
        Dictionary with statistics
    """
    stats = {"deleted": 0, "errors": 0, "actions": []}
    
    if not directory.is_dir():
        return stats
    
    # Find all files eligible for deletion
    files_to_delete = [
        f for f in directory.iterdir() 
        if f.is_file() and is_auto_deletable(f)
    ]
    
    if not files_to_delete:
        return stats
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Cleaning up {len(files_to_delete)} temporary files\n")
    print("-" * 60)
    
    for file_path in files_to_delete:
        age_days = get_file_age_days(file_path)
        action = f"{file_path.name} ({age_days} days old)"
        stats["actions"].append(action)
        
        if dry_run:
            print(f"  [WOULD DELETE] {action}")
        else:
            try:
                # This is the ONLY place we delete files!
                file_path.unlink()
                print(f"  [DELETED] {action}")
                stats["deleted"] += 1
            except Exception as e:
                print(f"  [ERROR] {file_path.name}: {e}")
                stats["errors"] += 1
    
    print("-" * 60)
    
    if dry_run:
        print(f"\n[DRY RUN] Would delete {len(stats['actions'])} temporary files")
    else:
        print(f"\nCleanup summary: {stats['deleted']} deleted, {stats['errors']} errors")
    
    return stats


def get_category(file_path: Path) -> str:
    """
    Determine the category for a file based on its extension.
    
    How it works:
        1. Extract the file extension (e.g., ".jpg" from "photo.jpg")
        2. Convert to lowercase for case-insensitive matching (.JPG == .jpg)
        3. Loop through each category and check if extension is in its set
        4. Return "Other" if no match found (fallback category)
    
    Args:
        file_path: A Path object representing the file
                   (Path objects have useful properties like .suffix, .stem, .name)
    
    Returns:
        Category name as a string (e.g., "Images", "Documents", "Other")
    
    Example:
        >>> get_category(Path("photo.jpg"))
        'Images'
        >>> get_category(Path("mystery.xyz"))
        'Other'
    """
    # .suffix returns the file extension including the dot: "file.txt" -> ".txt"
    # .lower() ensures "FILE.TXT" and "file.txt" are treated the same
    ext = file_path.suffix.lower()
    
    # .items() returns key-value pairs: ("Images", {".jpg", ".png", ...})
    for category, extensions in CATEGORIES.items():
        # Set lookup: "is ext in this set?" - very fast O(1) operation
        if ext in extensions:
            return category
    
    # If we get here, no category matched - use fallback
    return "Other"


def archive_old_files(directory: Path, dry_run: bool = False) -> dict:
    """
    Move files older than ARCHIVE_AGE_DAYS to an _Archive subfolder.
    
    This helps keep your main folder clean by moving files you haven't
    touched in a while to a separate location. Files are NOT deleted,
    just moved to _Archive/ where you can review them later.
    
    The archive preserves the category structure:
        _Archive/
        ├── Images/
        │   └── old_photo.jpg
        ├── Documents/
        │   └── old_report.pdf
        └── Other/
            └── random_old_file.xyz
    
    Args:
        directory: Path to the directory to scan for old files
        dry_run: If True, only preview what would be archived
        
    Returns:
        Dictionary with statistics about the operation
    """
    stats = {"archived": 0, "skipped": 0, "errors": 0, "actions": []}
    
    if not directory.is_dir():
        print(f"Error: '{directory}' is not a valid directory")
        sys.exit(1)
    
    # Get all files in the directory (top level only)
    files = [f for f in directory.iterdir() if f.is_file()]
    
    # Filter to only old files
    old_files = [f for f in files if not f.name.startswith(".") and is_old_file(f)]
    
    if not old_files:
        print(f"No files older than {ARCHIVE_AGE_DAYS} days found.")
        return stats
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Archiving {len(old_files)} files older than {ARCHIVE_AGE_DAYS} days\n")
    print("-" * 60)
    
    archive_dir = directory / ARCHIVE_FOLDER
    
    for file_path in old_files:
        # Determine category for subfolder structure in archive
        category = get_category(file_path)
        age_days = get_file_age_days(file_path)
        
        # Create path: _Archive/Category/filename
        dest_dir = archive_dir / category
        destination = dest_dir / file_path.name
        
        action = f"{file_path.name} ({age_days} days old) -> {ARCHIVE_FOLDER}/{category}/"
        stats["actions"].append(action)
        
        if dry_run:
            print(f"  [WOULD ARCHIVE] {action}")
        else:
            try:
                # Create nested directories if they don't exist
                dest_dir.mkdir(parents=True, exist_ok=True)
                
                # Handle duplicates with timestamp
                if destination.exists():
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    new_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
                    destination = dest_dir / new_name
                
                # Move (not delete!) the file to archive
                shutil.move(str(file_path), str(destination))
                print(f"  [ARCHIVED] {action}")
                stats["archived"] += 1
                
            except Exception as e:
                print(f"  [ERROR] {file_path.name}: {e}")
                stats["errors"] += 1
    
    print("-" * 60)
    
    if dry_run:
        print(f"\n[DRY RUN] Would archive {len(stats['actions'])} files")
        print("Run without --dry-run to apply changes.")
    else:
        print(f"\nArchive summary: {stats['archived']} archived, {stats['errors']} errors")
    
    return stats


def organize_files(directory: Path, dry_run: bool = False) -> dict:
    """
    Organize files in the given directory into categorized subfolders.
    
    This is the main workhorse function. It:
        1. Validates the directory exists
        2. Lists all files (not folders) in the directory
        3. For each file, determines its category and moves it
        4. Tracks statistics for the summary
    
    Args:
        directory: Path to the directory to organize
        dry_run: If True, only preview changes without moving files
                 (This is a safety feature - always preview first!)
        
    Returns:
        Dictionary with statistics about the operation:
        {
            "moved": int,      # Number of files successfully moved
            "skipped": int,    # Number of files skipped (e.g., hidden files)
            "errors": int,     # Number of files that failed to move
            "actions": list,   # List of action descriptions
        }
    
    Design Pattern:
        This function uses the "dry run" pattern - common in CLI tools.
        It lets users preview destructive operations before committing.
        Examples: git diff (before commit), rm -i, rsync --dry-run
    """
    # Initialize statistics dictionary to track our progress
    stats = {"moved": 0, "skipped": 0, "errors": 0, "actions": []}
    
    # Validate input: make sure we got a real directory
    # .is_dir() returns True only if path exists AND is a directory
    if not directory.is_dir():
        print(f"Error: '{directory}' is not a valid directory")
        sys.exit(1)  # Exit with error code 1 (convention: 0 = success, non-zero = error)
    
    # List comprehension: a compact way to filter items
    # This is equivalent to:
    #   files = []
    #   for f in directory.iterdir():
    #       if f.is_file():
    #           files.append(f)
    #
    # .iterdir() yields all items in directory (files AND folders)
    # .is_file() returns True only for files (not directories)
    files = [f for f in directory.iterdir() if f.is_file()]
    
    # Early return pattern: handle edge case up front
    if not files:
        print("No files found to organize.")
        return stats
    
    # f-string with conditional expression (ternary operator)
    # Format: value_if_true if condition else value_if_false
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Organizing {len(files)} files in: {directory}\n")
    print("-" * 60)  # String multiplication: "-" * 3 = "---"
    
    # Main loop: process each file
    for file_path in files:
        # Skip hidden files (Unix convention: files starting with . are hidden)
        # .name gives just the filename: "/path/to/.hidden" -> ".hidden"
        if file_path.name.startswith("."):
            stats["skipped"] += 1
            continue  # Skip to next iteration of the loop
        
        # Determine where this file should go
        category = get_category(file_path)
        
        # Path objects support / operator for joining paths!
        # This is cleaner than os.path.join(directory, category)
        category_dir = directory / category          # e.g., ~/Downloads/Images
        destination = category_dir / file_path.name  # e.g., ~/Downloads/Images/photo.jpg
        
        # Build a human-readable description of the action
        action = f"{file_path.name} -> {category}/"
        stats["actions"].append(action)
        
        if dry_run:
            # Just show what WOULD happen, don't actually move
            print(f"  [WOULD MOVE] {action}")
        else:
            # Actually move the file
            # Using try/except to handle errors gracefully (file in use, permissions, etc.)
            try:
                # Create category directory if it doesn't exist
                # exist_ok=True means "don't error if it already exists"
                category_dir.mkdir(exist_ok=True)
                
                # Handle duplicate filenames by adding a timestamp
                # .exists() returns True if a file/folder already exists at that path
                if destination.exists():
                    # strftime = "string format time" - converts datetime to string
                    # %Y=year, %m=month, %d=day, %H=hour, %M=minute, %S=second
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    # .stem = filename without extension: "photo.jpg" -> "photo"
                    # .suffix = just the extension: "photo.jpg" -> ".jpg"
                    new_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
                    destination = category_dir / new_name
                
                # shutil.move() handles moving files, even across different drives
                # We convert Path to str for compatibility with older Python versions
                shutil.move(str(file_path), str(destination))
                print(f"  [MOVED] {action}")
                stats["moved"] += 1
                
            except Exception as e:
                # Catch any error and report it, but keep processing other files
                # In production code, you might want to catch specific exceptions
                print(f"  [ERROR] {file_path.name}: {e}")
                stats["errors"] += 1
    
    print("-" * 60)
    
    # Print summary based on mode
    if dry_run:
        print(f"\n[DRY RUN] Would move {len(stats['actions'])} files")
        print("Run without --dry-run to apply changes.")
    else:
        print(f"\nSummary: {stats['moved']} moved, {stats['skipped']} skipped, {stats['errors']} errors")
    
    return stats


def main():
    """
    Entry point for the script - handles command-line argument parsing.
    
    This function uses argparse, Python's built-in CLI argument parser.
    argparse automatically:
        - Generates --help text
        - Validates required arguments
        - Parses flags like --dry-run
        - Shows error messages for invalid usage
    
    Run `python organize.py --help` to see the generated help text!
    """
    # Create the argument parser
    # - description: shown at top of --help output
    # - formatter_class: RawDescriptionHelpFormatter preserves our epilog formatting
    # - epilog: shown at bottom of --help output (our category list)
    parser = argparse.ArgumentParser(
        description="Organize files into categorized folders",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Categories:
  Images      - jpg, png, gif, svg, webp, etc.
  Documents   - pdf, doc, txt, xlsx, etc.
  Audio       - mp3, wav, flac, etc.
  Video       - mp4, avi, mkv, mov, etc.
  Archives    - zip, rar, 7z, tar, etc.
  Code        - py, js, html, css, json, etc.
  Executables - exe, dmg, app, etc.
  Fonts       - ttf, otf, woff, etc.
  Other       - everything else

Safety:
  This script NEVER deletes files - it only moves them.
  Exception: --cleanup deletes .ica files older than 1 day.
  Use --dry-run to preview changes before applying.
        """
    )
    
    # Add positional argument (required, no -- prefix)
    # "directory" will be available as args.directory
    parser.add_argument("directory", type=str, help="Directory to organize")
    
    # Add optional flag argument
    # --dry-run or -n (short version)
    # action="store_true" means: if flag is present, set to True; otherwise False
    parser.add_argument("--dry-run", "-n", action="store_true", 
                        help="Preview changes without moving files")
    
    # Add archive flag for moving old files
    parser.add_argument("--archive", "-a", action="store_true",
                        help=f"Move files older than {ARCHIVE_AGE_DAYS} days to {ARCHIVE_FOLDER}/")
    
    # Add cleanup flag for deleting temporary files
    parser.add_argument("--cleanup", "-c", action="store_true",
                        help=f"Delete temporary files (.ica) older than {AUTO_DELETE_AGE_DAYS} day(s)")
    
    # Parse the command-line arguments
    # This reads sys.argv (the command line) and returns a namespace object
    args = parser.parse_args()
    
    # Convert the string path to a Path object and resolve it:
    # - expanduser(): converts ~ to /Users/jelmer (your home directory)
    # - resolve(): converts to absolute path and resolves symlinks
    # Example: "~/Downloads" -> "/Users/jelmer/Downloads"
    directory = Path(args.directory).expanduser().resolve()
    
    # Run the requested operations in logical order:
    # 1. Cleanup temp files first (so they don't get organized into Other/)
    # 2. Organize remaining files into categories
    # 3. Archive old files last
    
    # Step 1: Delete temporary files if --cleanup flag is set
    if args.cleanup:
        print("=" * 60)
        print("CLEANING UP TEMPORARY FILES")
        print("=" * 60)
        cleanup_temp_files(directory, dry_run=args.dry_run)
    
    # Step 2: Organize files into category folders
    organize_files(directory, dry_run=args.dry_run)
    
    # Step 3: Archive old files if --archive flag is set
    if args.archive:
        print("\n" + "=" * 60)
        print("ARCHIVING OLD FILES")
        print("=" * 60)
        archive_old_files(directory, dry_run=args.dry_run)


# =============================================================================
# SCRIPT ENTRY POINT
# =============================================================================

# This is the Python idiom for "run this code only if this file is executed directly"
# If this file is imported as a module, this block won't run
#
# Why? It allows you to:
#   1. Run as script:  python organize.py ~/Downloads
#   2. Import as module: from organize import get_category (for testing/reuse)
#
# __name__ is a special variable:
#   - When run directly: __name__ == "__main__"
#   - When imported: __name__ == "organize" (the module name)
if __name__ == "__main__":
    main()
