#!/usr/bin/env python3
"""
File Organizer - Automatically organize files into categorized folders.

Usage:
    python organize.py <directory>           # Organize files in directory
    python organize.py <directory> --dry-run # Preview changes without moving files
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# File extension to category mapping
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


def get_category(file_path: Path) -> str:
    """Determine the category for a file based on its extension."""
    ext = file_path.suffix.lower()
    for category, extensions in CATEGORIES.items():
        if ext in extensions:
            return category
    return "Other"


def organize_files(directory: Path, dry_run: bool = False) -> dict:
    """
    Organize files in the given directory into categorized subfolders.
    
    Args:
        directory: Path to the directory to organize
        dry_run: If True, only preview changes without moving files
        
    Returns:
        Dictionary with statistics about the operation
    """
    stats = {"moved": 0, "skipped": 0, "errors": 0, "actions": []}
    
    if not directory.is_dir():
        print(f"Error: '{directory}' is not a valid directory")
        sys.exit(1)
    
    # Get all files in the directory (not subdirectories)
    files = [f for f in directory.iterdir() if f.is_file()]
    
    if not files:
        print("No files found to organize.")
        return stats
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Organizing {len(files)} files in: {directory}\n")
    print("-" * 60)
    
    for file_path in files:
        # Skip hidden files
        if file_path.name.startswith("."):
            stats["skipped"] += 1
            continue
            
        category = get_category(file_path)
        category_dir = directory / category
        destination = category_dir / file_path.name
        
        action = f"{file_path.name} -> {category}/"
        stats["actions"].append(action)
        
        if dry_run:
            print(f"  [WOULD MOVE] {action}")
        else:
            try:
                # Create category directory if it doesn't exist
                category_dir.mkdir(exist_ok=True)
                
                # Handle duplicate filenames
                if destination.exists():
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    new_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
                    destination = category_dir / new_name
                
                shutil.move(str(file_path), str(destination))
                print(f"  [MOVED] {action}")
                stats["moved"] += 1
            except Exception as e:
                print(f"  [ERROR] {file_path.name}: {e}")
                stats["errors"] += 1
    
    print("-" * 60)
    
    if dry_run:
        print(f"\n[DRY RUN] Would move {len(stats['actions'])} files")
        print("Run without --dry-run to apply changes.")
    else:
        print(f"\nSummary: {stats['moved']} moved, {stats['skipped']} skipped, {stats['errors']} errors")
    
    return stats


def main():
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
    parser.add_argument("directory", type=str, help="Directory to organize")
    parser.add_argument("--dry-run", "-n", action="store_true", 
                        help="Preview changes without moving files")
    
    args = parser.parse_args()
    directory = Path(args.directory).expanduser().resolve()
    
    organize_files(directory, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
