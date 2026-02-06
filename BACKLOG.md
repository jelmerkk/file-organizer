# File Organizer - Feature Backlog

Inspired by [Sparkle](https://makeitsparkle.co) - features we can implement.

## Currently Implemented
- [x] Organize files by extension into category folders
- [x] Large files (>1GB) to separate `_LargeFiles/` folder
- [x] Archive old files (>30 days) to `_Archive/`
- [x] Auto-delete specific temp files (.ica after 1 day)
- [x] Dry-run mode for safe preview
- [x] Daily scheduled execution via launchd
- [x] Run at login to catch missed runs

## High Priority - Next Up
- [x] **Duplicate Detection** - Find and flag duplicate files (even with different names)
  - Use file hash (MD5) to detect true duplicates
  - Oldest file is kept as original, duplicates moved to `_Duplicates/`
  - Use `--duplicates` or `-d` flag to enable
  - Shows potential space savings

- [x] **Recents Folder** - Keep new files in a "Recents" area before organizing
  - Files newer than 24 hours stay in `_Recents/`
  - Gives user time to work with recent downloads before they're moved
  - Use `--recents` or `-r` flag to enable

## Medium Priority
- [ ] **Multiple Folder Support** - Organize Desktop and Documents too
  - Add support for specifying multiple source folders
  - Each folder can have its own category structure

- [ ] **Cloud Storage Support** - Work with Dropbox, Google Drive, iCloud
  - Detect common cloud folder locations
  - Handle sync conflicts gracefully

- [ ] **Custom Categories** - Let user define their own categories
  - Config file (YAML/JSON) for custom extension mappings
  - User-defined folder names

- [ ] **Exclude Patterns** - Skip certain files/folders
  - Glob patterns for exclusions (e.g., `*.tmp`, `node_modules/`)
  - Config file for persistent exclusions

- [ ] **File Renaming** - Clean up messy filenames
  - Remove `(1)`, `(2)` suffixes from duplicate downloads
  - Standardize date formats in filenames
  - Optional: rename screenshots to more descriptive names

## Lower Priority / Nice to Have
- [ ] **Menu Bar App** - macOS menu bar integration
  - Quick access to organize, view stats
  - Notifications when organization runs

- [ ] **Statistics Dashboard** - Track organization metrics
  - Files organized over time
  - Disk space saved from duplicates
  - Most common file types

- [ ] **Smart Folders** - AI-based categorization (like Sparkle)
  - Use file content/metadata for smarter categorization
  - Project detection (group related files together)
  - Would require more dependencies

- [ ] **Watch Mode** - Real-time organization
  - Monitor folders for new files
  - Organize immediately when files are added
  - Use macOS FSEvents

- [ ] **External Drive Support** - Organize USB drives, external HDDs
  - Detect when drives are mounted
  - Apply organization rules to external storage

## Technical Improvements
- [x] **Unit Tests** - Add test coverage (88 tests, 92% coverage)
- [x] **Refactored Architecture** - Proper Python package structure
  - `file_organizer/config.py` - Dataclass configuration (testable, injectable)
  - `file_organizer/utils.py` - Pure utility functions
  - `file_organizer/operations.py` - Core file operations
  - `file_organizer/cli.py` - CLI argument parsing
- [ ] **Config File** - Move settings to external config (YAML)
- [ ] **Logging** - Better logging with rotation
- [ ] **Error Recovery** - Handle edge cases (locked files, permissions)

---

## Notes
- Sparkle uses AI to create custom folder structures - we use simpler extension-based rules
- Sparkle is a paid app ($10/mo) - our script is free and open source
- Focus on reliability and simplicity over fancy features
