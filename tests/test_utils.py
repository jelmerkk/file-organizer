"""
Unit tests for file_organizer.utils module.

Tests pure utility functions in isolation.
"""

import os
import pytest
from datetime import datetime, timedelta
from pathlib import Path

from file_organizer.config import Config
from file_organizer.utils import (
    compute_file_hash,
    format_file_size,
    generate_unique_filename,
    get_category,
    get_file_age_days,
    get_file_age_hours,
    get_file_size_bytes,
    is_auto_deletable,
    is_large_file,
    is_old_file,
    is_recent_file,
    should_skip_file,
    should_skip_for_duplicates,
)


class TestFormatFileSize:
    """Tests for format_file_size function."""
    
    def test_bytes(self):
        assert format_file_size(0) == "0 B"
        assert format_file_size(100) == "100 B"
        assert format_file_size(1023) == "1023 B"
    
    def test_kilobytes(self):
        assert format_file_size(1024) == "1.00 KB"
        assert format_file_size(1536) == "1.50 KB"
        assert format_file_size(1024 * 500) == "500.00 KB"
    
    def test_megabytes(self):
        assert format_file_size(1024 * 1024) == "1.00 MB"
        assert format_file_size(1024 * 1024 * 5) == "5.00 MB"
    
    def test_gigabytes(self):
        assert format_file_size(1024 * 1024 * 1024) == "1.00 GB"
        assert format_file_size(1024 * 1024 * 1024 * 2) == "2.00 GB"
    
    def test_terabytes(self):
        assert format_file_size(1024 ** 4) == "1.00 TB"


class TestGetCategory:
    """Tests for get_category function."""
    
    def test_image_extensions(self):
        config = Config()
        assert get_category(Path("photo.jpg"), config) == "Images"
        assert get_category(Path("photo.jpeg"), config) == "Images"
        assert get_category(Path("image.PNG"), config) == "Images"
        assert get_category(Path("icon.gif"), config) == "Images"
    
    def test_document_extensions(self):
        config = Config()
        assert get_category(Path("doc.pdf"), config) == "Documents"
        assert get_category(Path("doc.docx"), config) == "Documents"
        assert get_category(Path("data.csv"), config) == "Documents"
    
    def test_audio_extensions(self):
        config = Config()
        assert get_category(Path("song.mp3"), config) == "Audio"
        assert get_category(Path("sound.wav"), config) == "Audio"
    
    def test_video_extensions(self):
        config = Config()
        assert get_category(Path("movie.mp4"), config) == "Video"
        assert get_category(Path("clip.mov"), config) == "Video"
    
    def test_code_extensions(self):
        config = Config()
        assert get_category(Path("script.py"), config) == "Code"
        assert get_category(Path("app.js"), config) == "Code"
    
    def test_unknown_extension(self):
        config = Config()
        assert get_category(Path("file.xyz"), config) == "Other"
        assert get_category(Path("file.unknown"), config) == "Other"
    
    def test_case_insensitive(self):
        config = Config()
        assert get_category(Path("photo.JPG"), config) == "Images"
        assert get_category(Path("photo.Jpg"), config) == "Images"
        assert get_category(Path("doc.PDF"), config) == "Documents"


class TestGetFileAgeDays:
    """Tests for get_file_age_days function."""
    
    def test_new_file(self, temp_dir: Path):
        f = temp_dir / "new.txt"
        f.write_text("content")
        
        assert get_file_age_days(f) == 0
    
    def test_old_file(self, old_file: Path):
        # old_file fixture creates a file 60 days old
        assert get_file_age_days(old_file) == 60
    
    def test_with_custom_now(self, temp_dir: Path):
        f = temp_dir / "test.txt"
        f.write_text("content")
        
        # Pretend it's 10 days in the future
        future = datetime.now() + timedelta(days=10)
        assert get_file_age_days(f, now=future) == 10


class TestGetFileAgeHours:
    """Tests for get_file_age_hours function."""
    
    def test_new_file(self, temp_dir: Path):
        f = temp_dir / "new.txt"
        f.write_text("content")
        
        # Should be very close to 0 hours old
        assert get_file_age_hours(f) < 0.01
    
    def test_with_custom_now(self, temp_dir: Path):
        f = temp_dir / "test.txt"
        f.write_text("content")
        
        # Pretend it's 5 hours in the future
        future = datetime.now() + timedelta(hours=5)
        assert abs(get_file_age_hours(f, now=future) - 5.0) < 0.01


class TestIsOldFile:
    """Tests for is_old_file function."""
    
    def test_new_file_not_old(self, temp_dir: Path):
        f = temp_dir / "new.txt"
        f.write_text("content")
        
        assert is_old_file(f) is False
    
    def test_old_file_is_old(self, old_file: Path):
        assert is_old_file(old_file) is True
    
    def test_custom_threshold(self, temp_dir: Path):
        f = temp_dir / "test.txt"
        f.write_text("content")
        
        # Set to 5 days ago
        old_time = datetime.now() - timedelta(days=5)
        os.utime(f, (old_time.timestamp(), old_time.timestamp()))
        
        # With default 30 days, not old
        assert is_old_file(f, days=30) is False
        # With 3 day threshold, is old
        assert is_old_file(f, days=3) is True


class TestIsRecentFile:
    """Tests for is_recent_file function."""
    
    def test_new_file_is_recent(self, recent_file: Path):
        assert is_recent_file(recent_file) is True
    
    def test_old_file_not_recent(self, old_file: Path):
        assert is_recent_file(old_file) is False
    
    def test_custom_threshold(self, temp_dir: Path, test_config: Config):
        f = temp_dir / "test.txt"
        f.write_text("content")
        
        # Set to 30 minutes ago
        old_time = datetime.now() - timedelta(minutes=30)
        os.utime(f, (old_time.timestamp(), old_time.timestamp()))
        
        # With 1 hour threshold (test_config), still recent
        assert is_recent_file(f, config=test_config) is True
        
        # With 0.25 hour (15 min) threshold, not recent
        assert is_recent_file(f, hours=0.25) is False


class TestIsLargeFile:
    """Tests for is_large_file function."""
    
    def test_small_file_not_large(self, temp_dir: Path, test_config: Config):
        f = temp_dir / "small.txt"
        f.write_text("small content")
        
        assert is_large_file(f, config=test_config) is False
    
    def test_large_file_is_large(self, large_file: Path, test_config: Config):
        assert is_large_file(large_file, config=test_config) is True


class TestIsAutoDeletable:
    """Tests for is_auto_deletable function."""
    
    def test_old_ica_is_deletable(self, ica_file: Path):
        assert is_auto_deletable(ica_file) is True
    
    def test_new_ica_not_deletable(self, temp_dir: Path):
        f = temp_dir / "new.ica"
        f.write_text("content")
        # File is new (just created), so not deletable
        assert is_auto_deletable(f) is False
    
    def test_other_extension_not_deletable(self, old_file: Path):
        # old_file is a .txt file, not in auto_delete_extensions
        assert is_auto_deletable(old_file) is False


class TestComputeFileHash:
    """Tests for compute_file_hash function."""
    
    def test_same_content_same_hash(self, temp_dir: Path):
        f1 = temp_dir / "file1.txt"
        f2 = temp_dir / "file2.txt"
        
        content = "identical content"
        f1.write_text(content)
        f2.write_text(content)
        
        assert compute_file_hash(f1) == compute_file_hash(f2)
    
    def test_different_content_different_hash(self, temp_dir: Path):
        f1 = temp_dir / "file1.txt"
        f2 = temp_dir / "file2.txt"
        
        f1.write_text("content one")
        f2.write_text("content two")
        
        assert compute_file_hash(f1) != compute_file_hash(f2)
    
    def test_hash_format(self, temp_dir: Path):
        f = temp_dir / "file.txt"
        f.write_text("content")
        
        hash_value = compute_file_hash(f)
        
        # MD5 produces 32 hex characters
        assert len(hash_value) == 32
        assert all(c in "0123456789abcdef" for c in hash_value)


class TestGenerateUniqueFilename:
    """Tests for generate_unique_filename function."""
    
    def test_non_existing_file_unchanged(self, temp_dir: Path):
        dest = temp_dir / "new_file.txt"
        
        result = generate_unique_filename(dest)
        
        assert result == dest
    
    def test_existing_file_gets_timestamp(self, temp_dir: Path):
        dest = temp_dir / "existing.txt"
        dest.write_text("content")
        
        result = generate_unique_filename(dest)
        
        assert result != dest
        assert result.parent == dest.parent
        assert "existing_" in result.name
        assert result.suffix == ".txt"


class TestShouldSkipFile:
    """Tests for should_skip_file function."""
    
    def test_hidden_file_skipped(self, hidden_file: Path):
        assert should_skip_file(hidden_file) is True
    
    def test_regular_file_not_skipped(self, temp_dir: Path):
        f = temp_dir / "regular.txt"
        f.write_text("content")
        
        assert should_skip_file(f) is False
    
    def test_file_in_special_folder_skipped(self, temp_dir: Path):
        special_dir = temp_dir / "_Archive"
        special_dir.mkdir()
        f = special_dir / "file.txt"
        f.write_text("content")
        
        assert should_skip_file(f) is True


class TestShouldSkipForDuplicates:
    """Tests for should_skip_for_duplicates function."""
    
    def test_empty_file_skipped(self, temp_dir: Path):
        f = temp_dir / "empty.txt"
        f.write_text("")
        
        assert should_skip_for_duplicates(f, temp_dir) is True
    
    def test_hidden_file_skipped(self, temp_dir: Path, hidden_file: Path):
        assert should_skip_for_duplicates(hidden_file, temp_dir) is True
    
    def test_file_in_special_folder_skipped(self, temp_dir: Path):
        special_dir = temp_dir / "_Duplicates"
        special_dir.mkdir()
        f = special_dir / "file.txt"
        f.write_text("content")
        
        assert should_skip_for_duplicates(f, temp_dir) is True
    
    def test_regular_file_not_skipped(self, temp_dir: Path):
        f = temp_dir / "regular.txt"
        f.write_text("content")
        
        assert should_skip_for_duplicates(f, temp_dir) is False
