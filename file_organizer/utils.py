"""
Pure utility functions for file organizer.

These functions are stateless and have no side effects (except reading file metadata).
They are easy to unit test in isolation.
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import Config, DEFAULT_CONFIG


def get_file_mtime(file_path: Path) -> datetime:
    """
    Get the modification time of a file as a datetime object.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Datetime of last modification
    """
    return datetime.fromtimestamp(file_path.stat().st_mtime)


def get_file_age_days(file_path: Path, now: Optional[datetime] = None) -> int:
    """
    Get the age of a file in days based on its modification time.
    
    Args:
        file_path: Path to the file
        now: Current time (optional, for testing)
        
    Returns:
        Number of days since the file was last modified
    """
    if now is None:
        now = datetime.now()
    mtime = get_file_mtime(file_path)
    age = now - mtime
    return age.days


def get_file_age_hours(file_path: Path, now: Optional[datetime] = None) -> float:
    """
    Get the age of a file in hours based on its modification time.
    
    Args:
        file_path: Path to the file
        now: Current time (optional, for testing)
        
    Returns:
        Number of hours since the file was last modified
    """
    if now is None:
        now = datetime.now()
    mtime = get_file_mtime(file_path)
    age = now - mtime
    return age.total_seconds() / 3600


def get_file_size_bytes(file_path: Path) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes
    """
    return file_path.stat().st_size


def format_file_size(size_bytes: int) -> str:
    """
    Convert bytes to human-readable format (KB, MB, GB).
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable string like "1.5 GB" or "256 MB"
        
    Example:
        >>> format_file_size(1536000000)
        '1.43 GB'
    """
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}" if unit != 'B' else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def is_old_file(
    file_path: Path, 
    days: Optional[int] = None, 
    config: Config = DEFAULT_CONFIG,
    now: Optional[datetime] = None
) -> bool:
    """
    Check if a file is older than the specified number of days.
    
    Args:
        file_path: Path to the file
        days: Age threshold in days (default: config.archive_age_days)
        config: Configuration to use
        now: Current time (optional, for testing)
        
    Returns:
        True if file is older than the threshold, False otherwise
    """
    if days is None:
        days = config.archive_age_days
    return get_file_age_days(file_path, now=now) > days


def is_recent_file(
    file_path: Path, 
    hours: Optional[float] = None, 
    config: Config = DEFAULT_CONFIG,
    now: Optional[datetime] = None
) -> bool:
    """
    Check if a file is newer than the specified number of hours.
    
    Args:
        file_path: Path to the file
        hours: Age threshold in hours (default: config.recents_age_hours)
        config: Configuration to use
        now: Current time (optional, for testing)
        
    Returns:
        True if file is newer than the threshold, False otherwise
    """
    if hours is None:
        hours = config.recents_age_hours
    return get_file_age_hours(file_path, now=now) < hours


def is_large_file(
    file_path: Path, 
    threshold: Optional[int] = None, 
    config: Config = DEFAULT_CONFIG
) -> bool:
    """
    Check if a file exceeds the large file threshold.
    
    Args:
        file_path: Path to the file
        threshold: Size threshold in bytes (default: config.large_file_threshold_bytes)
        config: Configuration to use
        
    Returns:
        True if file is larger than threshold
    """
    if threshold is None:
        threshold = config.large_file_threshold_bytes
    return get_file_size_bytes(file_path) > threshold


def is_auto_deletable(
    file_path: Path, 
    config: Config = DEFAULT_CONFIG,
    now: Optional[datetime] = None
) -> bool:
    """
    Check if a file is eligible for automatic deletion.
    
    Only specific file types that are older than the threshold qualify.
    
    Args:
        file_path: Path to the file
        config: Configuration to use
        now: Current time (optional, for testing)
        
    Returns:
        True if file should be auto-deleted, False otherwise
    """
    ext = file_path.suffix.lower()
    if ext not in config.auto_delete_extensions:
        return False
    return get_file_age_days(file_path, now=now) > config.auto_delete_age_days


def compute_file_hash(file_path: Path, buffer_size: int = 8192) -> str:
    """
    Compute MD5 hash of a file for duplicate detection.
    
    Reads the file in chunks to handle large files efficiently.
    
    Args:
        file_path: Path to the file to hash
        buffer_size: Size of chunks to read (default: 8192)
        
    Returns:
        MD5 hash as a 32-character hex string
    """
    hasher = hashlib.md5()
    
    with open(file_path, 'rb') as f:
        while chunk := f.read(buffer_size):
            hasher.update(chunk)
    
    return hasher.hexdigest()


def generate_unique_filename(destination: Path) -> Path:
    """
    Generate a unique filename by adding a timestamp if the file exists.
    
    Args:
        destination: Proposed destination path
        
    Returns:
        Original path if it doesn't exist, or path with timestamp suffix
    """
    if not destination.exists():
        return destination
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_name = f"{destination.stem}_{timestamp}{destination.suffix}"
    return destination.parent / new_name


def get_category(file_path: Path, config: Config = DEFAULT_CONFIG) -> str:
    """
    Determine the category for a file based on its extension.
    
    Args:
        file_path: Path to the file
        config: Configuration to use
        
    Returns:
        Category name (e.g., "Images", "Documents", "Other")
    """
    return config.get_category(file_path.suffix)


def should_skip_file(file_path: Path, config: Config = DEFAULT_CONFIG) -> bool:
    """
    Check if a file should be skipped during processing.
    
    Skips hidden files (starting with .) and files in special folders.
    
    Args:
        file_path: Path to the file
        config: Configuration to use
        
    Returns:
        True if file should be skipped
    """
    # Skip hidden files
    if config.is_hidden(file_path.name):
        return True
    
    # Skip files in special folders (check all path components)
    for part in file_path.parts:
        if config.is_special_folder(part) or config.is_hidden(part):
            return True
    
    return False


def should_skip_for_duplicates(file_path: Path, base_dir: Path, config: Config = DEFAULT_CONFIG) -> bool:
    """
    Check if a file should be skipped during duplicate detection.
    
    Skips hidden files, files in special folders, and empty files.
    
    Args:
        file_path: Path to the file
        base_dir: Base directory being scanned
        config: Configuration to use
        
    Returns:
        True if file should be skipped
    """
    # Skip empty files (they all have the same hash)
    if file_path.stat().st_size == 0:
        return True
    
    # Get path relative to base directory and check each component
    try:
        rel_path = file_path.relative_to(base_dir)
        for part in rel_path.parts:
            if config.is_special_folder(part) or config.is_hidden(part):
                return True
    except ValueError:
        # file_path is not relative to base_dir, check absolute parts
        pass
    
    return config.is_hidden(file_path.name)
