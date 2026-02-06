"""
Configuration for the file organizer.

Uses a dataclass to make configuration testable and injectable.
Default values match the original script behavior.
"""

from dataclasses import dataclass, field
from typing import Dict, Set


@dataclass
class Config:
    """
    Configuration for file organization operations.
    
    All settings can be overridden when creating a Config instance,
    making it easy to test with different values.
    
    Example:
        # Use defaults
        config = Config()
        
        # Override for testing
        config = Config(archive_age_days=7, recents_age_hours=1)
    """
    
    # Archive settings
    archive_age_days: int = 30
    archive_folder: str = "_Archive"
    
    # Auto-delete settings (exception to no-delete rule)
    auto_delete_extensions: Set[str] = field(default_factory=lambda: {".ica"})
    auto_delete_age_days: int = 1
    
    # Large file settings
    large_file_threshold_bytes: int = 1 * 1024 * 1024 * 1024  # 1 GB
    large_files_folder: str = "_LargeFiles"
    
    # Recents settings
    recents_age_hours: float = 24.0
    recents_folder: str = "_Recents"
    
    # Duplicate detection settings
    duplicates_folder: str = "_Duplicates"
    hash_buffer_size: int = 8192
    
    # File extension to category mapping
    categories: Dict[str, Set[str]] = field(default_factory=lambda: {
        "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff", ".heic"},
        "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"},
        "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
        "Video": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
        "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
        "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yml", ".yaml", ".md", ".sh", ".c", ".cpp", ".h", ".java", ".go", ".rs"},
        "Executables": {".exe", ".msi", ".dmg", ".app", ".deb", ".rpm"},
        "Fonts": {".ttf", ".otf", ".woff", ".woff2"},
    })
    
    # Default category for unrecognized extensions
    default_category: str = "Other"
    
    # Special folder prefix (folders starting with this are skipped in scans)
    special_folder_prefix: str = "_"
    
    def get_category(self, extension: str) -> str:
        """
        Get the category for a file extension.
        
        Args:
            extension: File extension including dot (e.g., ".jpg")
            
        Returns:
            Category name or default_category if not found
        """
        ext_lower = extension.lower()
        for category, extensions in self.categories.items():
            if ext_lower in extensions:
                return category
        return self.default_category
    
    def is_special_folder(self, name: str) -> bool:
        """Check if a folder name is a special folder (starts with prefix)."""
        return name.startswith(self.special_folder_prefix)
    
    def is_hidden(self, name: str) -> bool:
        """Check if a file/folder name is hidden (starts with dot)."""
        return name.startswith(".")


# Default configuration instance
DEFAULT_CONFIG = Config()
