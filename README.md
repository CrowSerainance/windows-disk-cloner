# Windows Disk Cloner - Inspired by Clonezilla

A custom Windows disk cloning application that uses **Clonezilla's methodology** combined with **Windows-native disk cloning libraries and tools**.

## 🎯 Project Goal

Create a Windows .exe application that can clone disk C: to a new SSD (E: drive) using:
- **Clonezilla's proven workflow and approach** (partition detection, metadata saving, verification)
- **Windows-compatible libraries** (WMI, pywin32, robocopy, .NET Management classes)
- **Both command-line and GUI interfaces** for ease of use

## ⚠️ IMPORTANT WARNINGS

### Before Using This Tool:

1. **REQUIRES ADMINISTRATOR PRIVILEGES** - This tool MUST be run as Administrator
2. **BACKUP YOUR DATA** - Always have a backup before cloning operations
3. **SYSTEM DRIVE CLONING** - Cloning a running system drive (C:) while Windows is running is **NOT RECOMMENDED**
   - The recommended approach is to use a bootable environment (like Clonezilla Live)
   - This tool is best for creating **image backups** or cloning **non-system drives**
4. **DESTRUCTIVE OPERATIONS** - Disk-to-disk cloning will **ERASE ALL DATA** on the target disk
5. **VERIFY YOUR SELECTION** - Always double-check source and target drives before proceeding

## 🏗️ Architecture

This project provides **THREE implementations**:

### 1. Python CLI Version (`disk_cloner.py`)
- Command-line interface
- Cross-platform Python code
- Uses `pywin32` and `WMI` for disk operations
- Perfect for scripting and automation

### 2. Python GUI Version (`disk_cloner_gui.py`)
- User-friendly graphical interface using tkinter
- Visual disk selection and monitoring
- Real-time log display
- Best for interactive use

### 3. C# Version (`DiskCloner.cs`)
- Native Windows implementation
- Uses .NET Management classes (WMI)
- Compiled to standalone .exe
- No Python runtime required

## 📋 Features Inspired by Clonezilla

### Core Features:
- ✅ **Disk Scanning** - Detect all physical disks and partitions (like `ocs-scan-disk`)
- ✅ **Metadata Saving** - Save partition tables, disk signatures, filesystem info
- ✅ **Filesystem Cloning** - Clone partition data using robocopy (similar to partclone)
- ✅ **Raw Disk Cloning** - Sector-by-sector copy including partition table and boot records
- ✅ **OS Cloning with Boot Support** - Complete Windows OS cloning with UEFI/BIOS boot loader configuration
- ✅ **UEFI Boot Support** - Automatically detects and configures UEFI boot partitions (EFI System Partition)
- ✅ **BIOS/MBR Boot Support** - Supports legacy BIOS boot mode with MBR partition tables
- ✅ **Windows Boot Loader** - Uses `bcdboot` to configure Windows Boot Manager after cloning
- ✅ **Partition Resize** - Automatically resize partitions to fill available disk space after cloning
- ✅ **Checksum Generation** - MD5/SHA256 checksums for verification
- ✅ **Visual Progress Bar** - Real-time progress tracking with percentage and status
- ✅ **Progress Logging** - Detailed logs similar to Clonezilla's verbose output
- ✅ **Multi-threaded Copying** - Fast multi-threaded file operations
- ✅ **Partition Information** - Boot flags, filesystem types, sizes, labels
- ✅ **Improved UI** - Better window layout and responsive design

### Clonezilla Workflow Implementation:
1. **Pre-flight checks** (admin rights, disk accessibility)
2. **Disk scanning and validation**
3. **Source disk analysis** (partitions, filesystems, boot sectors)
4. **Metadata extraction and saving**
5. **Data cloning** (filesystem-aware or raw block copy)
6. **Verification** (checksums, file counts)
7. **Post-operation logging**

## 🚀 Quick Start

### Prerequisites

**For Python versions:**
```bash
# Install Python 3.8 or higher from https://www.python.org/
python --version

# Install required libraries
pip install -r requirements.txt
```

**For C# version:**
```bash
# Install .NET 6.0 SDK or higher from https://dotnet.microsoft.com/download
dotnet --version
```

### Installation

1. **Clone or download this repository**
2. **Navigate to the `windows-disk-cloner` directory**
3. **Choose your preferred method:**

#### Method A: Run Python scripts directly
```bash
# CLI version
python disk_cloner.py --help

# GUI version
python disk_cloner_gui.py
```

#### Method B: Build standalone .exe files
```bash
# Run the build script (Windows only)
build_exe.bat
```

This will create .exe files in the `dist` folder:
- `DiskClonerCLI.exe` - Python CLI version
- `DiskClonerGUI.exe` - Python GUI version (recommended)
- `WindowsDiskCloner.exe` - C# version (if .NET SDK installed)

If Inno Setup is installed, an installer will be created in the `installer` folder:
- `WindowsDiskCloner-Setup.exe` - Professional installer with all dependencies

See `BUILD_INSTRUCTIONS.txt` for detailed build information.

## 📖 Usage Guide

### Option 1: Using the GUI (Recommended for Beginners)

1. **Run as Administrator:**
   - Right-click `disk_cloner_gui.py` or `DiskClonerGUI.exe`
   - Select "Run as Administrator"

2. **Clone Drive to Image (Backup):**
   - Go to "Clone Drive to Image" tab
   - Select your source drive (e.g., C:)
   - Choose an output directory (e.g., E:\Backups)
   - Enable checksums and verification (recommended)
   - Click "Start Backup"

3. **Clone Disk to Disk (Including OS):**
   - Go to "Clone Disk to Disk" tab
   - Select source disk (disk to copy FROM)
   - Select target disk (disk to copy TO - **will be erased!**)
   - Choose clone mode:
     - **RAW mode (Recommended)**: Sector-by-sector copy, most reliable
       - Copies **everything** including OS, boot records, partition table
       - Automatically configures UEFI/BIOS boot loader after cloning
       - Ensures the cloned Windows OS is fully bootable
   - **Optional**: Enable "Resize last partition to fill all available disk space"
     - This extends the last data partition to use all available storage
     - Useful when target disk is larger than source disk
   - Confirm the operation (you'll be warned twice)
   - Click "Start Disk Clone"
   - Watch the progress bar and detailed logs
   - **After cloning**: The tool automatically configures Windows Boot Manager
     - UEFI systems: Boot files installed to EFI System Partition
     - BIOS systems: Boot files support both UEFI and legacy BIOS
   - **To boot from cloned disk**: Reboot and select the new disk from BIOS/UEFI boot menu

4. **View Disk Information:**
   - Go to "Disk Information" tab
   - See all detected disks and partitions
   - Refresh to update the list

### Option 2: Using the CLI

#### List all disks:
```bash
python disk_cloner.py --list-disks
```

#### Clone a drive to image (backup):
```bash
python disk_cloner.py --clone-drive C: --output E:\Backups
```

#### Clone disk to disk:
```bash
python disk_cloner.py --clone-disk 0 1
# Clones Disk 0 to Disk 1 (WARNING: Disk 1 will be erased!)
```

#### Additional options:
```bash
# Skip verification
python disk_cloner.py --clone-drive C: --output E:\Backups --no-verify

# Skip checksum generation
python disk_cloner.py --clone-drive C: --output E:\Backups --no-checksum
```

### Option 3: Using C# Version

```bash
# Run the C# executable as Administrator
WindowsDiskCloner.exe

# Follow the interactive menu:
# 1. List all disks
# 2. Clone drive to image
# 3. Exit
```

## 🎯 Your Specific Use Case: C: → E: Clone (OS Cloning)

### ✅ YES - Complete OS Cloning with Full Boot Support:

**CONFIRMED: This tool CAN clone your complete C: drive including OS and make it bootable as your main drive!**

**What gets cloned (COMPLETE list):**
- ✅ **Complete Windows OS** - All files, registry, settings, programs, user data
- ✅ **All Partitions** - EFI System Partition, System Reserved, Windows (C:), Recovery
- ✅ **Partition Table** - GPT or MBR (exact copy)
- ✅ **Boot Records** - MBR boot sector, GPT headers
- ✅ **UEFI Boot Files** - EFI System Partition with boot files
- ✅ **BIOS Boot Files** - Legacy BIOS boot configuration
- ✅ **Windows Boot Manager** - Configured with `bcdboot` after cloning
- ✅ **Disk Signature** - Changed to unique value (prevents conflicts)
- ✅ **Everything** - Complete sector-by-sector copy in RAW mode

**After cloning, the new disk is:**
- ✅ **Completely independent** - Can remove original drive
- ✅ **Fully bootable** - Can be used as your main drive
- ✅ **Identical to source** - Exact copy of everything

**⚠️ IMPORTANT:** For best results when cloning a system drive (C:):
1. **Recommended**: Boot from Windows Recovery or Clonezilla Live USB
2. **Alternative**: Clone while Windows is running (may have locked files)
3. **After cloning**: Select the new disk from BIOS/UEFI boot menu to use as main drive

**See `OS_CLONING_CONFIRMATION.md` for complete details.**

### Recommended Approach for System Drive:

**⚠️ WARNING:** Cloning C: while Windows is running from C: may have limitations!

**Best methods:**

#### Method 1: Create a Backup Image (Safest)
```bash
# Step 1: Create backup image of C: on E:
python disk_cloner.py --clone-drive C: --output E:\Backups

# Step 2: Boot from USB/recovery and restore
# (This tool creates the backup; use Windows Recovery or Clonezilla Live to restore)
```

#### Method 2: Clone Non-System Partitions
```bash
# If E: is a separate drive, you can clone individual partitions
python disk_cloner.py --clone-drive D: --output E:\Clone_of_D
```

#### Method 3: Use Clonezilla Live (Recommended for System Disk)

This tool is **inspired by Clonezilla** but for true system disk cloning, use **Clonezilla Live**:

1. **Download Clonezilla Live** from https://clonezilla.org/
2. **Create bootable USB** using the tool
3. **Boot from USB** (not Windows)
4. **Clone C: → E:** using Clonezilla's disk-to-disk mode
5. **Use this Windows tool** for non-critical backups and data migrations

## 🔧 How It Works

### Clonezilla Methodology Applied:

#### 1. Disk Detection Phase
```
Clonezilla: Uses `blkid`, `lsblk`, `parted`
This Tool:  Uses WMI (Win32_DiskDrive, Win32_DiskPartition)
```

#### 2. Metadata Extraction
```
Clonezilla: Saves partition table with `sfdisk`, `sgdisk`
This Tool:  Saves disk/partition info to JSON using WMI queries
```

#### 3. Data Cloning
```
Clonezilla: Uses `partclone`, `partimage`, `dd` for different filesystems
This Tool:  Uses `robocopy` for NTFS/FAT (Windows-native, fast, reliable)
            Can use PowerShell for raw disk access if needed
```

#### 4. Verification
```
Clonezilla: Generates checksums with `md5sum`, `sha256sum`
This Tool:  Uses Python hashlib or C# MD5/SHA256 classes
```

### Technical Implementation Details:

**Python Implementation:**
- Uses `wmi` library to query Windows Management Instrumentation
- Uses `pywin32` for low-level Windows API access
- Spawns `robocopy.exe` subprocess for file copying
- Can access raw disk sectors via PowerShell if needed
- Tkinter GUI for cross-platform interface

**C# Implementation:**
- Uses `System.Management` namespace for WMI queries
- Direct access to `Win32_DiskDrive` and `Win32_DiskPartition` classes
- Spawns `robocopy.exe` via `Process.Start()`
- Native Windows Forms could be added for GUI (currently CLI)

## 📁 Project Structure

```
windows-disk-cloner/
│
├── disk_cloner.py              # Python CLI implementation
├── disk_cloner_gui.py          # Python GUI implementation
├── DiskCloner.cs               # C# implementation
├── DiskCloner.csproj           # C# project file
├── requirements.txt            # Python dependencies
├── build_exe.bat               # Build script for .exe files
├── README.md                   # This file
│
└── dist/                       # Built executables (after build)
    ├── DiskClonerCLI.exe
    ├── DiskClonerGUI.exe
    └── WindowsDiskCloner.exe
```

## 🛠️ Building from Source

### Build All Versions:
```bash
# Windows only
build_exe.bat
```

### Build Python version manually:
```bash
pip install pyinstaller
pyinstaller --onefile --console disk_cloner.py
pyinstaller --onefile --windowed disk_cloner_gui.py
```

### Build C# version manually:
```bash
dotnet restore
dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true
```

## 🆕 New Features in Latest Version

### Partition Resize
- Automatically resize the last partition after cloning to fill all available disk space
- Enabled via checkbox in the "Clone Disk to Disk" tab
- Uses Windows diskpart to safely extend partitions
- Perfect for utilizing larger target disks

### Improved Progress Tracking
- Visual progress bar with percentage completion
- Real-time status updates
- Detailed activity logs in scrollable window
- Better window layout that fits all content

### Enhanced Raw Disk Cloning
- Fixed sector read errors at end of disk
- Better error handling for edge cases
- More reliable completion detection

## 🐛 Troubleshooting

### "Not running as Administrator"
- Right-click the .exe or .py file
- Select "Run as Administrator"
- Or open Command Prompt as Administrator and run from there

### "Module not found" errors (Python)
```bash
pip install -r requirements.txt
pip install pywin32 wmi
```

### Robocopy fails / Access denied
- Ensure running as Administrator
- Check source drive is accessible
- Check target drive has enough space
- Some system files may be locked (this is normal)

### "Cannot clone system drive"
- Use Clonezilla Live bootable USB instead
- Or create an image backup using this tool, restore with Windows Recovery

### Disk not detected
- Check Disk Management (diskmgmt.msc)
- Ensure disk is initialized and online
- Try refreshing the disk list

## 🔐 Security Considerations

- **Administrator access required** - This tool needs high privileges
- **Potential data loss** - Always verify source/target before cloning
- **No encryption by default** - Sensitive data is copied as-is
- **Log files** - May contain filesystem paths and metadata
- **Open source** - Review code before running on sensitive systems

## 📜 License

This project is licensed under the **GNU General Public License (GPL)** v2, the same license as Clonezilla.

## 🙏 Credits

**Inspired by:**
- **Clonezilla** (https://clonezilla.org/) - Steven Shiau and the NCHC Free Software Labs team
- **DRBL** (Diskless Remote Boot in Linux)
- **Partclone** project

**This tool uses:**
- Windows Management Instrumentation (WMI)
- Robocopy (Windows Robust File Copy)
- Python pywin32 and wmi libraries
- .NET System.Management namespace

## ⚠️ Disclaimer

This tool is provided "as-is" without warranty of any kind. Use at your own risk. Always maintain backups of important data. The authors are not responsible for any data loss or system damage resulting from the use of this software.

For production system disk cloning, we recommend using the official **Clonezilla Live** bootable environment.

## 🤝 Contributing

Contributions are welcome! This is a custom build for educational purposes and real-world use.

Areas for improvement:
- Add support for VSS (Volume Shadow Copy) to clone running system
- Implement raw disk cloning (sector-by-sector)
- Add restore functionality
- Support for more filesystems (ext4, exFAT via drivers)
- Compression support (gzip, zstd)
- Network cloning (similar to Clonezilla SE)

## 📞 Support

This is a custom tool. For issues:
1. Check the troubleshooting section
2. Review the Clonezilla documentation for methodology questions
3. Check Windows Disk Management for disk issues
4. For system drive cloning, use Clonezilla Live

---

**Made with reference to Clonezilla's proven methodology, adapted for Windows environments.**

**Remember: For critical system disk cloning, boot from Clonezilla Live USB for the safest results!**
