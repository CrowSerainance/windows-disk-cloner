# Changelog - Windows Disk Cloner

## Version 1.1.0 - Latest Updates

### 🐛 Bug Fixes
- **Fixed raw disk clone error**: Resolved "The drive cannot find the sector requested" error that occurred at the end of cloning
  - Now properly handles sector read errors when reaching the end of the source disk
  - Only copies up to the source disk size, preventing read errors
  - Better error handling for edge cases

### ✨ New Features

#### 1. Partition Resize Option
- Added checkbox to automatically resize the last partition after cloning
- Extends the partition to fill all available disk space on the target disk
- Perfect for utilizing larger target disks (e.g., cloning 223GB to 500GB disk)
- Uses Windows diskpart to safely extend partitions
- Available in the "Clone Disk to Disk" tab under "Post-Clone Options"

#### 2. Visual Progress Bar
- Replaced indeterminate progress bar with determinate progress bar
- Shows actual percentage completion (0-100%)
- Real-time progress updates during cloning operations
- Status label showing current operation
- Progress updates for both disk-to-disk and drive-to-image operations

#### 3. Improved UI Layout
- Increased default window size to 1000x800 (from 900x700)
- Added minimum window size constraints
- Better organized progress section with labels
- Improved log panel height (12 lines instead of 10)
- More responsive layout that fits all content without manual resizing
- Better spacing and organization of UI elements

### 🛠️ Build & Distribution

#### Enhanced Build Script
- Improved `build_exe.bat` with better error handling
- Automatic detection of required tools (Python, .NET SDK, Inno Setup)
- Cleaner build process with progress indicators
- Better handling of missing dependencies

#### Installer Creation
- Added Inno Setup script (`create_installer.iss`) for professional installer
- Creates Windows installer with:
  - Start menu shortcuts
  - Desktop icon option
  - Uninstaller
  - Proper file associations
- Installer includes all dependencies and documentation

#### Documentation
- Updated README.md with new features
- Added BUILD_INSTRUCTIONS.txt for detailed build steps
- Added INSTALLER_README.txt for installer information
- Created CHANGELOG.md (this file)

### 📝 Technical Improvements

#### Raw Disk Cloning
- Improved PowerShell script for raw disk copy
- Better handling of disk size differences
- More accurate progress reporting
- Safer error recovery

#### Partition Management
- New `resize_partition_to_fill_disk()` function
- Automatic detection of last data partition
- Safe partition extension using diskpart
- Verification of resize operation

#### GUI Enhancements
- Progress bar updates from log messages
- Better thread-safe GUI updates
- Improved error display
- More informative status messages

### 🔧 How to Use New Features

#### Using Partition Resize:
1. Open "Clone Disk to Disk" tab
2. Select source and target disks
3. Check "Resize last partition to fill all available disk space after cloning"
4. Start the clone operation
5. After cloning completes, the last partition will automatically be extended

#### Building the Installer:
1. Install Inno Setup from https://jrsoftware.org/isdl.php
2. Run `build_exe.bat`
3. The installer will be created in the `installer` folder
4. Distribute `WindowsDiskCloner-Setup.exe` to users

### ⚠️ Important Notes

- All features require Administrator privileges
- Partition resize only works on the last data partition
- System partitions (EFI, MSR, Recovery) are not resized
- Always verify disk selections before cloning
- Backup important data before using partition resize

### 🙏 Credits

Inspired by Clonezilla (https://clonezilla.org/)
Built with Python, tkinter, PyInstaller, and Inno Setup

---

## Version 1.0.0 - Initial Release

- Basic disk-to-disk cloning
- Drive-to-image backup
- Disk information display
- CLI and GUI interfaces
- Raw and filesystem cloning modes

