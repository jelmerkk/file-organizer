"""
Command-line interface for the file organizer.

Handles argument parsing and orchestrates operations.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .config import Config, DEFAULT_CONFIG
from .operations import (
    archive_old_files,
    cleanup_temp_files,
    handle_duplicates,
    organize_files,
)


def create_parser(config: Config = DEFAULT_CONFIG) -> argparse.ArgumentParser:
    """
    Create the argument parser for the CLI.
    
    Args:
        config: Configuration to use for default values in help text
        
    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Organize files into categorized folders",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
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

Special folders:
  {config.large_files_folder}  - files larger than 1 GB (for easy review)
  {config.archive_folder}     - files older than {config.archive_age_days} days (with --archive)
  {config.recents_folder}     - files newer than {int(config.recents_age_hours)} hours (with --recents)
  {config.duplicates_folder}  - duplicate files found (with --duplicates)

Safety:
  This script NEVER deletes files - it only moves them.
  Exception: --cleanup deletes {', '.join(config.auto_delete_extensions)} files older than {config.auto_delete_age_days} day(s).
  Use --dry-run to preview changes before applying.
        """
    )
    
    parser.add_argument(
        "directory",
        type=str,
        help="Directory to organize"
    )
    
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview changes without moving files"
    )
    
    parser.add_argument(
        "--archive", "-a",
        action="store_true",
        help=f"Move files older than {config.archive_age_days} days to {config.archive_folder}/"
    )
    
    parser.add_argument(
        "--cleanup", "-c",
        action="store_true",
        help=f"Delete temporary files ({', '.join(config.auto_delete_extensions)}) older than {config.auto_delete_age_days} day(s)"
    )
    
    parser.add_argument(
        "--duplicates", "-d",
        action="store_true",
        help=f"Find duplicate files and move extras to {config.duplicates_folder}/"
    )
    
    parser.add_argument(
        "--recents", "-r",
        action="store_true",
        help=f"Keep files newer than {int(config.recents_age_hours)} hours in {config.recents_folder}/"
    )
    
    return parser


def run(
    args: argparse.Namespace,
    config: Config = DEFAULT_CONFIG,
) -> int:
    """
    Run the file organizer with the given arguments.
    
    Args:
        args: Parsed command-line arguments
        config: Configuration to use
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    directory = Path(args.directory).expanduser().resolve()
    
    if not directory.is_dir():
        print(f"Error: '{directory}' is not a valid directory", file=sys.stderr)
        return 1
    
    try:
        # Run operations in logical order:
        # 1. Cleanup temp files first (so they don't get organized)
        # 2. Find and handle duplicates (before organizing moves files around)
        # 3. Organize remaining files into categories
        # 4. Archive old files last
        
        if args.cleanup:
            print("=" * 60)
            print("CLEANING UP TEMPORARY FILES")
            print("=" * 60)
            cleanup_temp_files(directory, dry_run=args.dry_run, config=config)
        
        if args.duplicates:
            print("\n" + "=" * 60)
            print("FINDING DUPLICATE FILES")
            print("=" * 60)
            handle_duplicates(directory, dry_run=args.dry_run, config=config)
        
        organize_files(
            directory,
            dry_run=args.dry_run,
            use_recents=args.recents,
            config=config
        )
        
        if args.archive:
            print("\n" + "=" * 60)
            print("ARCHIVING OLD FILES")
            print("=" * 60)
            archive_old_files(directory, dry_run=args.dry_run, config=config)
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI.
    
    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])
        
    Returns:
        Exit code
    """
    config = DEFAULT_CONFIG
    parser = create_parser(config)
    args = parser.parse_args(argv)
    return run(args, config)


if __name__ == "__main__":
    sys.exit(main())
