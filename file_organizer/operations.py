"""
Core file operations for the file organizer.

These functions perform the actual file system operations (move, delete).
They use a callback pattern for output to separate concerns from the CLI.
"""

import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .config import Config, DEFAULT_CONFIG
from .utils import (
    compute_file_hash,
    format_file_size,
    generate_unique_filename,
    get_category,
    get_file_age_days,
    get_file_age_hours,
    get_file_size_bytes,
    is_auto_deletable,
    is_large_file,
    is_recent_file,
    should_skip_file,
    should_skip_for_duplicates,
)


@dataclass
class OperationResult:
    """Result of a file operation with statistics."""
    success_count: int = 0
    skip_count: int = 0
    error_count: int = 0
    actions: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # For duplicate detection
    space_recoverable: int = 0


# Type alias for output callback
OutputCallback = Callable[[str], None]


def _default_output(message: str) -> None:
    """Default output callback that prints to stdout."""
    print(message)


def organize_files(
    directory: Path,
    dry_run: bool = False,
    use_recents: bool = False,
    config: Config = DEFAULT_CONFIG,
    output: OutputCallback = _default_output,
) -> OperationResult:
    """
    Organize files in the given directory into categorized subfolders.
    
    Args:
        directory: Path to the directory to organize
        dry_run: If True, only preview changes without moving files
        use_recents: If True, keep recent files in _Recents/
        config: Configuration to use
        output: Callback for output messages
        
    Returns:
        OperationResult with statistics
        
    Raises:
        ValueError: If directory is not valid
    """
    result = OperationResult()
    
    if not directory.is_dir():
        raise ValueError(f"'{directory}' is not a valid directory")
    
    # Get all files in the directory (top level only)
    files = [f for f in directory.iterdir() if f.is_file()]
    
    if not files:
        output("No files found to organize.")
        return result
    
    prefix = "[DRY RUN] " if dry_run else ""
    output(f"\n{prefix}Organizing {len(files)} files in: {directory}\n")
    output("-" * 60)
    
    for file_path in files:
        # Skip hidden files
        if config.is_hidden(file_path.name):
            result.skip_count += 1
            continue
        
        # Determine target category
        if use_recents and is_recent_file(file_path, config=config):
            age_hours = get_file_age_hours(file_path)
            category = config.recents_folder
            action = f"{file_path.name} ({age_hours:.1f}h old) -> {config.recents_folder}/"
        elif is_large_file(file_path, config=config):
            size_str = format_file_size(get_file_size_bytes(file_path))
            category = config.large_files_folder
            action = f"{file_path.name} ({size_str}) -> {config.large_files_folder}/"
        else:
            category = get_category(file_path, config=config)
            action = f"{file_path.name} -> {category}/"
        
        category_dir = directory / category
        destination = category_dir / file_path.name
        
        result.actions.append(action)
        
        if dry_run:
            output(f"  [WOULD MOVE] {action}")
        else:
            try:
                category_dir.mkdir(exist_ok=True)
                destination = generate_unique_filename(destination)
                shutil.move(str(file_path), str(destination))
                output(f"  [MOVED] {action}")
                result.success_count += 1
            except Exception as e:
                error_msg = f"{file_path.name}: {e}"
                output(f"  [ERROR] {error_msg}")
                result.errors.append(error_msg)
                result.error_count += 1
    
    output("-" * 60)
    
    if dry_run:
        output(f"\n[DRY RUN] Would move {len(result.actions)} files")
        output("Run without --dry-run to apply changes.")
    else:
        output(f"\nSummary: {result.success_count} moved, {result.skip_count} skipped, {result.error_count} errors")
    
    return result


def archive_old_files(
    directory: Path,
    dry_run: bool = False,
    config: Config = DEFAULT_CONFIG,
    output: OutputCallback = _default_output,
) -> OperationResult:
    """
    Move files older than threshold to an archive subfolder.
    
    Args:
        directory: Path to scan for old files
        dry_run: If True, only preview what would be archived
        config: Configuration to use
        output: Callback for output messages
        
    Returns:
        OperationResult with statistics
        
    Raises:
        ValueError: If directory is not valid
    """
    result = OperationResult()
    
    if not directory.is_dir():
        raise ValueError(f"'{directory}' is not a valid directory")
    
    # Get all files in the directory (top level only)
    files = [f for f in directory.iterdir() if f.is_file()]
    
    # Filter to only old, non-hidden files
    from .utils import is_old_file
    old_files = [f for f in files if not config.is_hidden(f.name) and is_old_file(f, config=config)]
    
    if not old_files:
        output(f"No files older than {config.archive_age_days} days found.")
        return result
    
    prefix = "[DRY RUN] " if dry_run else ""
    output(f"\n{prefix}Archiving {len(old_files)} files older than {config.archive_age_days} days\n")
    output("-" * 60)
    
    archive_dir = directory / config.archive_folder
    
    for file_path in old_files:
        category = get_category(file_path, config=config)
        age_days = get_file_age_days(file_path)
        
        dest_dir = archive_dir / category
        destination = dest_dir / file_path.name
        
        action = f"{file_path.name} ({age_days} days old) -> {config.archive_folder}/{category}/"
        result.actions.append(action)
        
        if dry_run:
            output(f"  [WOULD ARCHIVE] {action}")
        else:
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                destination = generate_unique_filename(destination)
                shutil.move(str(file_path), str(destination))
                output(f"  [ARCHIVED] {action}")
                result.success_count += 1
            except Exception as e:
                error_msg = f"{file_path.name}: {e}"
                output(f"  [ERROR] {error_msg}")
                result.errors.append(error_msg)
                result.error_count += 1
    
    output("-" * 60)
    
    if dry_run:
        output(f"\n[DRY RUN] Would archive {len(result.actions)} files")
        output("Run without --dry-run to apply changes.")
    else:
        output(f"\nArchive summary: {result.success_count} archived, {result.error_count} errors")
    
    return result


def cleanup_temp_files(
    directory: Path,
    dry_run: bool = False,
    config: Config = DEFAULT_CONFIG,
    output: OutputCallback = _default_output,
) -> OperationResult:
    """
    Delete temporary files that are older than the threshold.
    
    This is the ONLY function that deletes files. It only affects
    file types in config.auto_delete_extensions.
    
    Args:
        directory: Path to scan for deletable files
        dry_run: If True, only preview what would be deleted
        config: Configuration to use
        output: Callback for output messages
        
    Returns:
        OperationResult with statistics
    """
    result = OperationResult()
    
    if not directory.is_dir():
        return result
    
    # Find all files eligible for deletion
    files_to_delete = [
        f for f in directory.iterdir()
        if f.is_file() and is_auto_deletable(f, config=config)
    ]
    
    if not files_to_delete:
        return result
    
    prefix = "[DRY RUN] " if dry_run else ""
    output(f"\n{prefix}Cleaning up {len(files_to_delete)} temporary files\n")
    output("-" * 60)
    
    for file_path in files_to_delete:
        age_days = get_file_age_days(file_path)
        action = f"{file_path.name} ({age_days} days old)"
        result.actions.append(action)
        
        if dry_run:
            output(f"  [WOULD DELETE] {action}")
        else:
            try:
                file_path.unlink()
                output(f"  [DELETED] {action}")
                result.success_count += 1
            except Exception as e:
                error_msg = f"{file_path.name}: {e}"
                output(f"  [ERROR] {error_msg}")
                result.errors.append(error_msg)
                result.error_count += 1
    
    output("-" * 60)
    
    if dry_run:
        output(f"\n[DRY RUN] Would delete {len(result.actions)} temporary files")
    else:
        output(f"\nCleanup summary: {result.success_count} deleted, {result.error_count} errors")
    
    return result


def find_duplicates(
    directory: Path,
    recursive: bool = True,
    config: Config = DEFAULT_CONFIG,
    output: OutputCallback = _default_output,
) -> Dict[str, List[Path]]:
    """
    Find duplicate files in a directory by comparing file hashes.
    
    Args:
        directory: Path to scan for duplicates
        recursive: If True, scan subdirectories too
        config: Configuration to use
        output: Callback for output messages
        
    Returns:
        Dictionary mapping hash -> list of duplicate file paths
        Only includes hashes with 2+ files (actual duplicates)
    """
    hash_to_files: Dict[str, List[Path]] = defaultdict(list)
    
    # Choose iteration method based on recursive flag
    if recursive:
        files = [f for f in directory.rglob("*") if f.is_file()]
    else:
        files = [f for f in directory.iterdir() if f.is_file()]
    
    # Filter out files that should be skipped
    files = [f for f in files if not should_skip_for_duplicates(f, directory, config)]
    
    output(f"Scanning {len(files)} files for duplicates...")
    
    for file_path in files:
        try:
            file_hash = compute_file_hash(file_path, config.hash_buffer_size)
            hash_to_files[file_hash].append(file_path)
        except (PermissionError, OSError) as e:
            output(f"  [WARNING] Could not read {file_path.name}: {e}")
    
    # Filter to only include actual duplicates (2+ files with same hash)
    return {h: paths for h, paths in hash_to_files.items() if len(paths) > 1}


def handle_duplicates(
    directory: Path,
    dry_run: bool = False,
    config: Config = DEFAULT_CONFIG,
    output: OutputCallback = _default_output,
) -> OperationResult:
    """
    Find and handle duplicate files in a directory.
    
    Moves all but the oldest (original) to a duplicates folder for review.
    
    Args:
        directory: Path to scan for duplicates
        dry_run: If True, only preview what would be done
        config: Configuration to use
        output: Callback for output messages
        
    Returns:
        OperationResult with statistics
    """
    result = OperationResult()
    
    duplicates = find_duplicates(directory, config=config, output=output)
    
    if not duplicates:
        output("No duplicate files found.")
        return result
    
    total_sets = len(duplicates)
    total_extra = sum(len(files) - 1 for files in duplicates.values())
    
    prefix = "[DRY RUN] " if dry_run else ""
    output(f"\n{prefix}Found {total_sets} sets of duplicates ({total_extra} extra files)\n")
    output("-" * 60)
    
    duplicates_dir = directory / config.duplicates_folder
    
    for file_hash, file_list in duplicates.items():
        # Sort by modification time - oldest first (likely the original)
        file_list.sort(key=lambda f: f.stat().st_mtime)
        
        original = file_list[0]
        duplicates_to_move = file_list[1:]
        
        output(f"\n  Original: {original.relative_to(directory)}")
        
        for dup in duplicates_to_move:
            size = get_file_size_bytes(dup)
            size_str = format_file_size(size)
            result.space_recoverable += size
            
            action = f"{dup.relative_to(directory)} ({size_str})"
            result.actions.append(action)
            
            if dry_run:
                output(f"    [WOULD MOVE] {action}")
            else:
                try:
                    duplicates_dir.mkdir(exist_ok=True)
                    
                    # Preserve relative path structure
                    relative_path = dup.relative_to(directory)
                    dest = duplicates_dir / relative_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    
                    dest = generate_unique_filename(dest)
                    shutil.move(str(dup), str(dest))
                    output(f"    [MOVED] {action}")
                    result.success_count += 1
                except Exception as e:
                    error_msg = f"{dup.name}: {e}"
                    output(f"    [ERROR] {error_msg}")
                    result.errors.append(error_msg)
                    result.error_count += 1
    
    output("\n" + "-" * 60)
    
    space_str = format_file_size(result.space_recoverable)
    if dry_run:
        output(f"\n[DRY RUN] Would move {len(result.actions)} duplicate files")
        output(f"Potential space savings: {space_str}")
        output(f"Duplicates would be moved to: {config.duplicates_folder}/")
        output("Run without --dry-run to apply changes.")
    else:
        output(f"\nDuplicate summary: {result.success_count} moved to {config.duplicates_folder}/")
        output(f"Space recoverable (if you delete duplicates): {space_str}")
    
    return result
