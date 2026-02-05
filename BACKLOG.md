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
- [ ] **Duplicate Detection** - Find and flag duplicate files (even with different names)
  - Use file hash (MD5/SHA) to detect true duplicates
  - Show duplicates and let user decide which to keep
  - Could save significant disk space

- [ ] **Recents Folder** - Keep new files in a "Recents" area before organizing
  - Files stay in Recents for X hours/days before being sorted
  - Gives user time to work with recent downloads before they're moved

- [ ] **Undo/History** - Track moves and allow reverting
  - Log all file moves to a history file
  - Add `--undo` flag to reverse last operation
  - Important for user confidence

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
- [ ] **Unit Tests** - Add test coverage
- [ ] **Config File** - Move settings to external config (YAML)
- [ ] **Logging** - Better logging with rotation
- [ ] **Error Recovery** - Handle edge cases (locked files, permissions)

---

## Notes
- Sparkle uses AI to create custom folder structures - we use simpler extension-based rules
- Sparkle is a paid app ($10/mo) - our script is free and open source
- Focus on reliability and simplicity over fancy features
