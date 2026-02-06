"""
Pytest fixtures for file organizer tests.

Provides reusable test fixtures for creating temporary directories,
test files, and mock configurations.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import os

from file_organizer.config import Config


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def test_config() -> Config:
    """Create a test configuration with shorter thresholds."""
    return Config(
        archive_age_days=7,
        auto_delete_age_days=1,
        large_file_threshold_bytes=1024 * 1024,  # 1 MB for testing
        recents_age_hours=1.0,
    )


@pytest.fixture
def sample_files(temp_dir: Path) -> dict:
    """
    Create sample files of different types for testing.
    
    Each file has UNIQUE content to avoid being detected as duplicates.
    
    Returns a dict mapping category to list of created files.
    """
    files = {
        "Images": [],
        "Documents": [],
        "Audio": [],
        "Code": [],
        "Other": [],
    }
    
    # Create image files - each with unique content
    for i, ext in enumerate([".jpg", ".png", ".gif"]):
        f = temp_dir / f"image{ext}"
        f.write_text(f"fake image content {i} {ext}")  # Unique per file
        files["Images"].append(f)
    
    # Create document files - each with unique content
    for i, ext in enumerate([".pdf", ".txt", ".docx"]):
        f = temp_dir / f"document{ext}"
        f.write_text(f"fake document content {i} {ext}")  # Unique per file
        files["Documents"].append(f)
    
    # Create audio files - each with unique content
    for i, ext in enumerate([".mp3", ".wav"]):
        f = temp_dir / f"audio{ext}"
        f.write_text(f"fake audio content {i} {ext}")  # Unique per file
        files["Audio"].append(f)
    
    # Create code files - each with unique content
    for i, ext in enumerate([".py", ".js"]):
        f = temp_dir / f"code{ext}"
        f.write_text(f"# fake code {i} {ext}")  # Unique per file
        files["Code"].append(f)
    
    # Create unknown extension file
    f = temp_dir / "unknown.xyz"
    f.write_text("unknown content unique")
    files["Other"].append(f)
    
    return files


@pytest.fixture
def old_file(temp_dir: Path) -> Path:
    """Create a file that is 60 days old."""
    f = temp_dir / "old_file.txt"
    f.write_text("old content")
    
    # Set modification time to 60 days ago
    old_time = datetime.now() - timedelta(days=60)
    old_timestamp = old_time.timestamp()
    os.utime(f, (old_timestamp, old_timestamp))
    
    return f


@pytest.fixture
def recent_file(temp_dir: Path) -> Path:
    """Create a file that is only 30 minutes old."""
    f = temp_dir / "recent_file.txt"
    f.write_text("recent content")
    # File is created with current time by default
    return f


@pytest.fixture
def duplicate_files(temp_dir: Path) -> list:
    """Create duplicate files with identical content."""
    content = "This is duplicate content that will produce the same hash."
    
    files = []
    # Create files with staggered times: original is oldest (3h ago), copies are newer
    names_and_hours = [("original.txt", 3), ("copy1.txt", 2), ("copy2.txt", 1)]
    
    for name, hours_ago in names_and_hours:
        f = temp_dir / name
        f.write_text(content)
        
        # Set modification time
        old_time = datetime.now() - timedelta(hours=hours_ago)
        os.utime(f, (old_time.timestamp(), old_time.timestamp()))
        files.append(f)
    
    return files


@pytest.fixture
def hidden_file(temp_dir: Path) -> Path:
    """Create a hidden file (starts with dot)."""
    f = temp_dir / ".hidden_file"
    f.write_text("hidden content")
    return f


@pytest.fixture
def ica_file(temp_dir: Path) -> Path:
    """Create an old .ica file for cleanup testing."""
    f = temp_dir / "session.ica"
    f.write_text("[WFClient]\nVersion=2")
    
    # Set modification time to 3 days ago
    old_time = datetime.now() - timedelta(days=3)
    os.utime(f, (old_time.timestamp(), old_time.timestamp()))
    
    return f


@pytest.fixture
def large_file(temp_dir: Path, test_config: Config) -> Path:
    """Create a file larger than the test threshold."""
    f = temp_dir / "large_file.bin"
    # Write more than 1 MB
    f.write_bytes(b"x" * (test_config.large_file_threshold_bytes + 1000))
    return f


@pytest.fixture
def capture_output() -> list:
    """Create a list to capture output from operations."""
    return []


@pytest.fixture
def output_callback(capture_output: list):
    """Create an output callback that captures messages."""
    def callback(message: str) -> None:
        capture_output.append(message)
    return callback
