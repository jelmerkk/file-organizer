#!/usr/bin/env python3
"""
File Organizer - Automatically organize files into categorized folders.

This script scans a directory and moves files into subfolders based on their
file extension. It's useful for cleaning up messy folders like Downloads.

Usage:
    python organize.py <directory>           # Organize files in directory
    python organize.py <directory> --dry-run # Preview changes without moving files

Example:
    python organize.py ~/Downloads --dry-run  # See what would happen
    python organize.py ~/Downloads            # Actually organize the files

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
import shutil       # High-level file operations (copy, move, delete)
import argparse     # Command-line argument parsing
from pathlib import Path      # Object-oriented filesystem paths (modern way)
from datetime import datetime # Date/time handling (for duplicate file renaming)

# Note: We don't actually use 'os' - pathlib.Path replaces most of its functionality

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
    
    # Parse the command-line arguments
    # This reads sys.argv (the command line) and returns a namespace object
    args = parser.parse_args()
    
    # Convert the string path to a Path object and resolve it:
    # - expanduser(): converts ~ to /Users/jelmer (your home directory)
    # - resolve(): converts to absolute path and resolves symlinks
    # Example: "~/Downloads" -> "/Users/jelmer/Downloads"
    directory = Path(args.directory).expanduser().resolve()
    
    # Call our main logic function
    organize_files(directory, dry_run=args.dry_run)


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
