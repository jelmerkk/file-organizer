"""
Core file operations for the file organizer.

These functions perform the actual file system operations (move, delete).
They use a callback pattern for output to separate concerns from the CLI.
"""

import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .config import Config, DEFAULT_CONFIG
from .utils import (
    compute_file_hash,
    format_file_size,
    generate_unique_filename,
    get_category,
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


def cleanup_empty_folders(
    directory: Path,
    dry_run: bool = False,
    config: Config = DEFAULT_CONFIG,
    output: OutputCallback = print,
) -> int:
    """
    Remove empty category folders from the directory.
    
    Only removes folders that match known categories or special folders.
    Does not remove user-created folders.
    
    Returns:
        Number of folders removed
    """
    removed = 0
    category_names = set(config.categories.keys()) | {config.default_category}
    special_folders = {
        config.large_files_folder,
        config.recents_folder,
        config.archive_folder,
        config.duplicates_folder,
    }
    removable = category_names | special_folders
    
    for folder in directory.iterdir():
        if not folder.is_dir():
            continue
        if folder.name not in removable:
            continue
        if any(folder.iterdir()):
            continue
        
        if dry_run:
            output(f"  [WOULD REMOVE] Empty folder: {folder.name}/")
        else:
            try:
                folder.rmdir()
                output(f"  [REMOVED] Empty folder: {folder.name}/")
                removed += 1
            except OSError:
                pass
    
    return removed


def organize_files(
    directory: Path,
    dry_run: bool = False,
    use_recents: bool = False,
    config: Config = DEFAULT_CONFIG,
    output: OutputCallback = print,
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
    now_ts = datetime.now().timestamp()
    
    for file_path in files:
        # Skip hidden files
        if config.is_hidden(file_path.name):
            result.skip_count += 1
            continue
        try:
            stat = file_path.stat()
        except (PermissionError, OSError) as e:
            error_msg = f"{file_path.name}: {e}"
            output(f"  [ERROR] {error_msg}")
            result.errors.append(error_msg)
            result.error_count += 1
            continue
        
        # Determine target category
        age_hours = (now_ts - stat.st_mtime) / 3600
        if use_recents and age_hours < config.recents_age_hours:
            category = config.recents_folder
            action = f"{file_path.name} ({age_hours:.1f}h old) -> {config.recents_folder}/"
        elif stat.st_size > config.large_file_threshold_bytes:
            size_str = format_file_size(stat.st_size)
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
    
    cleanup_empty_folders(directory, dry_run=dry_run, config=config, output=output)
    
    return result


def archive_old_files(
    directory: Path,
    dry_run: bool = False,
    config: Config = DEFAULT_CONFIG,
    output: OutputCallback = print,
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
    
    # Filter to only old, non-hidden files and cache age for later output.
    now_ts = datetime.now().timestamp()
    old_files = []
    for f in files:
        if config.is_hidden(f.name):
            continue
        try:
            age_days = int((now_ts - f.stat().st_mtime) // 86400)
        except (PermissionError, OSError) as e:
            output(f"  [WARNING] Could not inspect {f.name}: {e}")
            continue
        if age_days > config.archive_age_days:
            old_files.append((f, age_days))
    
    if not old_files:
        output(f"No files older than {config.archive_age_days} days found.")
        return result
    
    prefix = "[DRY RUN] " if dry_run else ""
    output(f"\n{prefix}Archiving {len(old_files)} files older than {config.archive_age_days} days\n")
    output("-" * 60)
    
    archive_dir = directory / config.archive_folder
    
    for file_path, age_days in old_files:
        category = get_category(file_path, config=config)
        
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
    output: OutputCallback = print,
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
    
    # Find all files eligible for deletion and cache age for output.
    now_ts = datetime.now().timestamp()
    files_to_delete = []
    for f in directory.iterdir():
        if not f.is_file():
            continue
        if f.suffix.lower() not in config.auto_delete_extensions:
            continue
        try:
            age_days = int((now_ts - f.stat().st_mtime) // 86400)
        except (PermissionError, OSError) as e:
            output(f"  [WARNING] Could not inspect {f.name}: {e}")
            continue
        if age_days > config.auto_delete_age_days:
            files_to_delete.append((f, age_days))
    
    if not files_to_delete:
        return result
    
    prefix = "[DRY RUN] " if dry_run else ""
    output(f"\n{prefix}Cleaning up {len(files_to_delete)} temporary files\n")
    output("-" * 60)
    
    for file_path, age_days in files_to_delete:
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
    output: OutputCallback = print,
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
    size_to_files: Dict[int, List[Path]] = defaultdict(list)
    scanned = 0
    
    files_iter = directory.rglob("*") if recursive else directory.iterdir()
    for file_path in files_iter:
        if not file_path.is_file():
            continue
        if should_skip_for_duplicates(file_path, directory, config):
            continue
        try:
            stat = file_path.stat()
        except (PermissionError, OSError) as e:
            output(f"  [WARNING] Could not inspect {file_path.name}: {e}")
            continue
        
        size_to_files[stat.st_size].append(file_path)
        scanned += 1
    
    output(f"Scanning {scanned} files for duplicates...")
    
    for same_size_files in size_to_files.values():
        if len(same_size_files) < 2:
            continue
        for file_path in same_size_files:
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
    output: OutputCallback = print,
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
        file_stats = {}
        for file_path in file_list:
            try:
                file_stats[file_path] = file_path.stat()
            except (PermissionError, OSError) as e:
                output(f"  [WARNING] Could not inspect {file_path.name}: {e}")
        
        file_list = [file_path for file_path in file_list if file_path in file_stats]
        if len(file_list) < 2:
            continue
        
        # Sort by modification time - oldest first (likely the original)
        file_list.sort(key=lambda f: file_stats[f].st_mtime)
        
        original = file_list[0]
        duplicates_to_move = file_list[1:]
        
        output(f"\n  Original: {original.relative_to(directory)}")
        
        for dup in duplicates_to_move:
            size = file_stats[dup].st_size
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
