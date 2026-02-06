"""
Unit tests for file_organizer.operations module.

Tests file operations with actual file system interactions.
"""

import os
import pytest
from datetime import datetime, timedelta
from pathlib import Path

from file_organizer.config import Config
from file_organizer.operations import (
    OperationResult,
    archive_old_files,
    cleanup_temp_files,
    find_duplicates,
    handle_duplicates,
    organize_files,
)


class TestOrganizeFiles:
    """Tests for organize_files function."""
    
    def test_organizes_files_by_category(self, temp_dir: Path, sample_files: dict, capture_output: list, output_callback):
        """Test that files are moved to correct category folders."""
        result = organize_files(temp_dir, output=output_callback)
        
        assert result.success_count > 0
        assert result.error_count == 0
        
        # Check that category folders were created
        assert (temp_dir / "Images").is_dir()
        assert (temp_dir / "Documents").is_dir()
        assert (temp_dir / "Audio").is_dir()
        assert (temp_dir / "Code").is_dir()
        assert (temp_dir / "Other").is_dir()
        
        # Check that files were moved
        assert (temp_dir / "Images" / "image.jpg").exists()
        assert (temp_dir / "Documents" / "document.pdf").exists()
    
    def test_dry_run_does_not_move_files(self, temp_dir: Path, sample_files: dict, capture_output: list, output_callback):
        """Test that dry run only previews changes."""
        original_files = list(temp_dir.iterdir())
        
        result = organize_files(temp_dir, dry_run=True, output=output_callback)
        
        # Files should not have moved
        current_files = [f for f in temp_dir.iterdir() if f.is_file()]
        assert len(current_files) == len([f for f in original_files if f.is_file()])
        
        # But actions should be recorded
        assert len(result.actions) > 0
        
        # Output should indicate dry run
        assert any("[DRY RUN]" in msg for msg in capture_output)
    
    def test_skips_hidden_files(self, temp_dir: Path, hidden_file: Path, capture_output: list, output_callback):
        """Test that hidden files are skipped."""
        # Create a regular file too
        regular = temp_dir / "regular.txt"
        regular.write_text("content")
        
        result = organize_files(temp_dir, output=output_callback)
        
        assert result.skip_count >= 1
        # Hidden file should still be in root
        assert hidden_file.exists()
    
    def test_recents_mode_keeps_new_files_separate(self, temp_dir: Path, test_config: Config, capture_output: list, output_callback):
        """Test that recent files go to _Recents folder."""
        # Create a new file
        new_file = temp_dir / "new.txt"
        new_file.write_text("content")
        
        result = organize_files(
            temp_dir,
            use_recents=True,
            config=test_config,
            output=output_callback
        )
        
        assert result.success_count == 1
        assert (temp_dir / test_config.recents_folder / "new.txt").exists()
    
    def test_large_files_go_to_large_folder(self, temp_dir: Path, large_file: Path, test_config: Config, capture_output: list, output_callback):
        """Test that large files go to _LargeFiles folder."""
        result = organize_files(temp_dir, config=test_config, output=output_callback)
        
        assert result.success_count >= 1
        assert (temp_dir / test_config.large_files_folder / "large_file.bin").exists()
    
    def test_handles_duplicate_filenames(self, temp_dir: Path, capture_output: list, output_callback):
        """Test that duplicate filenames get timestamps."""
        # Create file and its destination
        docs_dir = temp_dir / "Documents"
        docs_dir.mkdir()
        
        existing = docs_dir / "file.txt"
        existing.write_text("existing")
        
        new_file = temp_dir / "file.txt"
        new_file.write_text("new content")
        
        result = organize_files(temp_dir, output=output_callback)
        
        # Should have moved successfully with timestamp
        assert result.success_count == 1
        assert result.error_count == 0
        
        # Both files should exist in Documents
        docs_files = list(docs_dir.iterdir())
        assert len(docs_files) == 2
    
    def test_invalid_directory_raises_error(self, temp_dir: Path):
        """Test that invalid directory raises ValueError."""
        with pytest.raises(ValueError, match="not a valid directory"):
            organize_files(temp_dir / "nonexistent")
    
    def test_empty_directory(self, temp_dir: Path, capture_output: list, output_callback):
        """Test handling of empty directory."""
        result = organize_files(temp_dir, output=output_callback)
        
        assert result.success_count == 0
        assert any("No files found" in msg for msg in capture_output)


class TestArchiveOldFiles:
    """Tests for archive_old_files function."""
    
    def test_archives_old_files(self, temp_dir: Path, old_file: Path, test_config: Config, capture_output: list, output_callback):
        """Test that old files are moved to archive."""
        result = archive_old_files(temp_dir, config=test_config, output=output_callback)
        
        assert result.success_count == 1
        
        # File should be in _Archive/Documents (since it's a .txt file)
        archive_path = temp_dir / test_config.archive_folder / "Documents" / old_file.name
        assert archive_path.exists()
        assert not old_file.exists()
    
    def test_does_not_archive_recent_files(self, temp_dir: Path, recent_file: Path, test_config: Config, capture_output: list, output_callback):
        """Test that recent files are not archived."""
        result = archive_old_files(temp_dir, config=test_config, output=output_callback)
        
        assert result.success_count == 0
        assert recent_file.exists()
    
    def test_dry_run_does_not_move(self, temp_dir: Path, old_file: Path, test_config: Config, capture_output: list, output_callback):
        """Test that dry run only previews."""
        result = archive_old_files(temp_dir, dry_run=True, config=test_config, output=output_callback)
        
        assert len(result.actions) == 1
        assert old_file.exists()  # File should still be in original location
    
    def test_preserves_category_structure(self, temp_dir: Path, test_config: Config, capture_output: list, output_callback):
        """Test that archive preserves category folders."""
        # Create old files of different types
        for ext, category in [(".pdf", "Documents"), (".jpg", "Images")]:
            f = temp_dir / f"old{ext}"
            f.write_text("content")
            old_time = datetime.now() - timedelta(days=60)
            os.utime(f, (old_time.timestamp(), old_time.timestamp()))
        
        result = archive_old_files(temp_dir, config=test_config, output=output_callback)
        
        assert result.success_count == 2
        assert (temp_dir / test_config.archive_folder / "Documents" / "old.pdf").exists()
        assert (temp_dir / test_config.archive_folder / "Images" / "old.jpg").exists()


class TestCleanupTempFiles:
    """Tests for cleanup_temp_files function."""
    
    def test_deletes_old_ica_files(self, temp_dir: Path, ica_file: Path, capture_output: list, output_callback):
        """Test that old .ica files are deleted."""
        result = cleanup_temp_files(temp_dir, output=output_callback)
        
        assert result.success_count == 1
        assert not ica_file.exists()
    
    def test_does_not_delete_new_ica_files(self, temp_dir: Path, capture_output: list, output_callback):
        """Test that new .ica files are not deleted."""
        new_ica = temp_dir / "new.ica"
        new_ica.write_text("content")
        
        result = cleanup_temp_files(temp_dir, output=output_callback)
        
        assert result.success_count == 0
        assert new_ica.exists()
    
    def test_does_not_delete_other_extensions(self, temp_dir: Path, old_file: Path, capture_output: list, output_callback):
        """Test that other file types are not deleted."""
        result = cleanup_temp_files(temp_dir, output=output_callback)
        
        assert result.success_count == 0
        assert old_file.exists()
    
    def test_dry_run_does_not_delete(self, temp_dir: Path, ica_file: Path, capture_output: list, output_callback):
        """Test that dry run only previews deletion."""
        result = cleanup_temp_files(temp_dir, dry_run=True, output=output_callback)
        
        assert len(result.actions) == 1
        assert ica_file.exists()


class TestFindDuplicates:
    """Tests for find_duplicates function."""
    
    def test_finds_duplicate_files(self, temp_dir: Path, duplicate_files: list, capture_output: list, output_callback):
        """Test that duplicate files are detected."""
        duplicates = find_duplicates(temp_dir, output=output_callback)
        
        assert len(duplicates) == 1
        
        # Get the list of duplicate files
        dup_list = list(duplicates.values())[0]
        assert len(dup_list) == 3
    
    def test_no_duplicates_when_unique(self, temp_dir: Path, sample_files: dict, capture_output: list, output_callback):
        """Test that unique files are not reported as duplicates."""
        duplicates = find_duplicates(temp_dir, output=output_callback)
        
        # sample_files creates files with unique content
        assert len(duplicates) == 0
    
    def test_skips_special_folders(self, temp_dir: Path, capture_output: list, output_callback):
        """Test that files in special folders are skipped."""
        # Create duplicate in special folder
        content = "duplicate content"
        
        regular = temp_dir / "file.txt"
        regular.write_text(content)
        
        special_dir = temp_dir / "_Archive"
        special_dir.mkdir()
        special = special_dir / "file.txt"
        special.write_text(content)
        
        duplicates = find_duplicates(temp_dir, output=output_callback)
        
        # Should not find duplicates (special folder is skipped)
        assert len(duplicates) == 0
    
    def test_recursive_scanning(self, temp_dir: Path, capture_output: list, output_callback):
        """Test that subdirectories are scanned."""
        content = "duplicate content"
        
        # Create duplicate in subdirectory
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        
        f1 = temp_dir / "file.txt"
        f1.write_text(content)
        
        f2 = subdir / "copy.txt"
        f2.write_text(content)
        
        duplicates = find_duplicates(temp_dir, recursive=True, output=output_callback)
        
        assert len(duplicates) == 1


class TestHandleDuplicates:
    """Tests for handle_duplicates function."""
    
    def test_moves_duplicates_to_folder(self, temp_dir: Path, duplicate_files: list, test_config: Config, capture_output: list, output_callback):
        """Test that duplicates are moved to _Duplicates folder."""
        result = handle_duplicates(temp_dir, config=test_config, output=output_callback)
        
        # Should have moved 2 duplicates (keeping the oldest)
        assert result.success_count == 2
        
        # Original (oldest) should still be in place
        original = duplicate_files[0]  # First file is oldest
        assert original.exists()
        
        # Duplicates folder should exist with copies
        dup_dir = temp_dir / test_config.duplicates_folder
        assert dup_dir.is_dir()
        assert len(list(dup_dir.iterdir())) == 2
    
    def test_keeps_oldest_as_original(self, temp_dir: Path, duplicate_files: list, capture_output: list, output_callback):
        """Test that the oldest file is kept as original."""
        # The duplicate_files fixture creates files with staggered times
        # First file is oldest
        oldest = duplicate_files[0]
        
        handle_duplicates(temp_dir, output=output_callback)
        
        # Oldest should still exist in original location
        assert oldest.exists()
    
    def test_dry_run_does_not_move(self, temp_dir: Path, duplicate_files: list, capture_output: list, output_callback):
        """Test that dry run only previews."""
        result = handle_duplicates(temp_dir, dry_run=True, output=output_callback)
        
        assert len(result.actions) == 2
        
        # All files should still exist in original location
        for f in duplicate_files:
            assert f.exists()
    
    def test_calculates_space_recoverable(self, temp_dir: Path, duplicate_files: list, capture_output: list, output_callback):
        """Test that space recoverable is calculated."""
        result = handle_duplicates(temp_dir, output=output_callback)
        
        assert result.space_recoverable > 0
    
    def test_no_action_when_no_duplicates(self, temp_dir: Path, sample_files: dict, capture_output: list, output_callback):
        """Test behavior when no duplicates exist."""
        result = handle_duplicates(temp_dir, output=output_callback)
        
        assert result.success_count == 0
        assert any("No duplicate files found" in msg for msg in capture_output)


class TestOperationResult:
    """Tests for OperationResult dataclass."""
    
    def test_default_values(self):
        result = OperationResult()
        
        assert result.success_count == 0
        assert result.skip_count == 0
        assert result.error_count == 0
        assert result.actions == []
        assert result.errors == []
        assert result.space_recoverable == 0
    
    def test_can_track_values(self):
        result = OperationResult()
        
        result.success_count += 1
        result.actions.append("test action")
        result.space_recoverable = 1024
        
        assert result.success_count == 1
        assert result.actions == ["test action"]
        assert result.space_recoverable == 1024
