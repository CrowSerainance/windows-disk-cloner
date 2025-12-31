# Windows Disk Cloner - Architecture & Design

## 🏛️ System Architecture

This document explains how the Windows Disk Cloner implements Clonezilla's methodology using Windows-native tools.

---

## 📐 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACES                          │
├─────────────────┬─────────────────┬─────────────────────────┤
│   CLI (Python)  │  GUI (Python)   │   CLI (C#)              │
│  disk_cloner.py │ disk_cloner_    │  DiskCloner.cs          │
│                 │    gui.py       │                         │
└────────┬────────┴────────┬────────┴─────────┬───────────────┘
         │                 │                  │
         └────────┬────────┴──────────────────┘
                  ▼
         ┌────────────────────────────┐
         │    CORE CLONING ENGINE     │
         │  (DiskCloner class)        │
         │                            │
         │  • Disk scanning           │
         │  • Partition detection     │
         │  • Metadata extraction     │
         │  • Cloning operations      │
         │  • Verification            │
         └────────┬───────────────────┘
                  │
         ┌────────┴───────────────────────────────────┐
         │                                            │
         ▼                                            ▼
┌────────────────────┐                    ┌──────────────────────┐
│  WINDOWS APIs      │                    │  EXTERNAL TOOLS      │
│                    │                    │                      │
│  • WMI             │                    │  • robocopy.exe      │
│  • pywin32         │                    │  • PowerShell        │
│  • System.Mgmt     │                    │  • diskpart (future) │
└────────┬───────────┘                    └──────────┬───────────┘
         │                                           │
         └───────────────────┬───────────────────────┘
                             ▼
                ┌────────────────────────────┐
                │   PHYSICAL DISKS/SSDs      │
                │                            │
                │  Disk 0: C: (Source)       │
                │  Disk 1: E: (Target)       │
                └────────────────────────────┘
```

---

## 🔄 Clonezilla Workflow Mapping

### Clonezilla's Approach → Our Implementation

| Clonezilla Component | Windows Implementation | File/Function |
|---------------------|------------------------|---------------|
| **ocs-sr** (main script) | `DiskCloner` class | `disk_cloner.py:DiskCloner` |
| **ocs-scan-disk** | `scan_disks()` | Uses WMI `Win32_DiskDrive` |
| **partclone** | `clone_partition_filesystem()` | Uses `robocopy.exe` |
| **dd** (raw copy) | `clone_partition_raw()` | Uses PowerShell streams |
| **sfdisk/sgdisk** (partition table) | `save_disk_metadata()` | WMI → JSON export |
| **md5sum/sha256sum** | `calculate_hash()` | Python `hashlib` / C# `MD5` |
| **ocs-functions** (utilities) | Various helper methods | Logging, verification |
| **TUI interface** | tkinter GUI | `disk_cloner_gui.py` |

---

## 🧩 Component Breakdown

### 1. Disk Detection Layer

**Purpose:** Identify all physical disks and partitions

**Clonezilla uses:**
- `lsblk` - List block devices
- `blkid` - Block device attributes
- `parted` - Partition information

**We use:**
```python
# Python/WMI
wmi_client = wmi.WMI()
disks = wmi_client.Win32_DiskDrive()
partitions = wmi_client.Win32_DiskPartition()
```

```csharp
// C#/.NET
ManagementObjectSearcher searcher =
    new ManagementObjectSearcher("SELECT * FROM Win32_DiskDrive");
```

**Data Flow:**
```
WMI Query → DiskDrive objects → DiskInfo structures → UI display
```

---

### 2. Metadata Extraction Layer

**Purpose:** Save partition tables, boot sectors, filesystem info

**Clonezilla uses:**
- `sfdisk -d` - Dump partition table
- `sgdisk -b` - Backup GPT
- `dd` - Backup MBR/boot sectors

**We use:**
```python
def save_disk_metadata(disk_index, output_dir):
    metadata = {
        'disk': get_disk_info(),
        'partitions': get_disk_partitions(),
        'timestamp': datetime.now()
    }
    json.dump(metadata, file)
```

**Output Format:**
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "disk": {
    "index": 0,
    "model": "Samsung SSD 970 EVO",
    "size": 512000000000,
    "interface": "SCSI"
  },
  "partitions": [...]
}
```

---

### 3. Cloning Engine Layer

**Purpose:** Copy disk/partition data reliably

#### Mode 1: Filesystem-Aware Copy (Default)

**Clonezilla uses:**
- `partclone.ntfs` - Clone NTFS
- `partclone.ext4` - Clone ext4
- Filesystem-aware = only copy used blocks

**We use:**
```python
def clone_partition_filesystem(source_drive, target_path):
    # Robocopy mirrors directory structure
    subprocess.run([
        'robocopy',
        f'{source_drive}\\',
        target_path,
        '/MIR',      # Mirror (includes deletes)
        '/COPYALL',  # All attributes/ACLs/timestamps
        '/MT:8',     # Multi-threaded
    ])
```

**Advantages:**
- ✅ Fast (only copies files, not free space)
- ✅ Native Windows tool (robust)
- ✅ Multi-threaded (8 threads default)
- ✅ Preserves ACLs, timestamps, attributes

**Limitations:**
- ❌ Requires mounted filesystem
- ❌ Cannot clone raw partitions
- ❌ No compression (yet)

#### Mode 2: Raw Block Copy (Alternative)

**Clonezilla uses:**
- `dd` - Raw disk copy
- `ddrescue` - Copy with error recovery

**We use:**
```python
def clone_partition_raw(source_partition, target_file):
    # PowerShell byte-level copy
    ps_script = """
    $source = [System.IO.File]::OpenRead($source_device)
    $target = [System.IO.File]::Create($target_file)
    # Copy in 4MB chunks
    """
    subprocess.run(['powershell', '-Command', ps_script])
```

**Use cases:**
- Raw partitions (no drive letter)
- Exact sector-by-sector copy
- Recovery scenarios

---

### 4. Verification Layer

**Purpose:** Ensure data integrity

**Clonezilla uses:**
- MD5/SHA1/SHA256 checksums
- CRC checks in partclone
- File count verification

**We use:**
```python
def calculate_hash(file_path, algorithm='md5'):
    hash_obj = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096*1024), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

# Create checksums file
for file in all_files:
    hash = calculate_hash(file)
    write_to_checksums_file(f"{hash}  {file}")
```

**Output:** `checksums.md5`
```
a1b2c3d4...  file1.txt
e5f6g7h8...  file2.dat
```

---

### 5. User Interface Layer

#### CLI Interface (Python)

```python
# Command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--list-disks')
parser.add_argument('--clone-drive', metavar='DRIVE')
parser.add_argument('--output', metavar='DIR')
```

**Usage:**
```bash
disk_cloner.py --list-disks
disk_cloner.py --clone-drive C: --output E:\Backup
```

#### GUI Interface (Python/tkinter)

```python
class DiskClonerGUI:
    def __init__(self):
        # Notebook with tabs
        self.tab_drive_to_image = ...
        self.tab_disk_to_disk = ...
        self.tab_disk_info = ...

    def start_drive_clone(self):
        # Run in background thread
        thread = threading.Thread(target=clone_thread)
        thread.start()
```

**Features:**
- Real-time log display
- Progress indicators
- Drive/disk selection dropdowns
- Confirmation dialogs

---

## 🔐 Security & Safety Features

### 1. Administrator Check
```python
def check_admin():
    return ctypes.windll.shell32.IsUserAnAdmin()
```

**Why:** Disk operations require elevated privileges

### 2. System Disk Protection
```python
def verify_disk_writable(disk_index):
    # Check if disk contains C: drive
    system_drive = os.environ.get('SystemDrive', 'C:')
    # Warn user if trying to overwrite system disk
```

**Why:** Prevent accidental system disk erasure

### 3. Multiple Confirmations
```python
# First confirmation
response = messagebox.askyesno("Confirm", "This will erase...")

# Second confirmation for destructive operations
response2 = messagebox.askyesno("Final Confirmation", "Last chance...")
```

**Why:** Disk cloning is destructive and irreversible

### 4. Logging
```python
def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [{level}] {message}"
    # Write to console and log file
```

**Why:** Audit trail and troubleshooting

---

## 📊 Data Structures

### DiskInfo
```python
{
    'index': 0,
    'device_id': '\\\\.\\PhysicalDrive0',
    'model': 'Samsung SSD 970 EVO',
    'size': 512110190592,
    'size_gb': 476.94,
    'interface': 'SCSI',
    'partitions': 3,
    'status': 'OK'
}
```

### PartitionInfo
```python
{
    'index': 0,
    'device_id': 'Disk #0, Partition #0',
    'size': 104857600,
    'size_gb': 0.10,
    'type': 'EFI System Partition',
    'bootable': True,
    'primary': True,
    'drive_letter': None,  # EFI has no letter
    'file_system': 'FAT32',
    'label': 'EFI',
    'free_space': 52428800
}
```

---

## 🔄 Operation Workflows

### Workflow 1: Clone Drive to Image

```
User Input (C:, E:\Backup)
    ↓
Check admin privileges
    ↓
Scan source drive (C:)
    ↓
Get partition information
    ↓
Create timestamped directory
    ↓
Save metadata JSON
    ↓
Launch robocopy
    ↓
Monitor progress
    ↓
Generate checksums
    ↓
Verify file counts
    ↓
Complete / Log results
```

### Workflow 2: Clone Disk to Disk

```
User Input (Disk 0 → Disk 1)
    ↓
Check admin privileges
    ↓
Verify target not system disk
    ↓
Double confirmation
    ↓
Scan source disk partitions
    ↓
For each partition:
    ├─ Get drive letter
    ├─ Create target directory
    ├─ Clone filesystem
    └─ Verify
    ↓
Save metadata
    ↓
Complete / Log results
```

---

## 🛠️ Technology Stack

### Python Implementation
- **Core:** Python 3.8+
- **Windows API:** `pywin32`
- **WMI:** `wmi` library
- **GUI:** `tkinter` (built-in)
- **Hashing:** `hashlib` (built-in)
- **Process mgmt:** `subprocess` (built-in)

### C# Implementation
- **Framework:** .NET 6.0+
- **WMI:** `System.Management`
- **Serialization:** `System.Text.Json`
- **Hashing:** `System.Security.Cryptography`
- **Process mgmt:** `System.Diagnostics.Process`

### External Tools
- **File copying:** `robocopy.exe` (Windows built-in)
- **Scripting:** `PowerShell` (for raw disk access)
- **Future:** `diskpart.exe` (partition management)

---

## 🚀 Performance Considerations

### Multi-threading
```python
# Robocopy with 8 threads
'/MT:8'

# GUI operations in background
thread = threading.Thread(target=clone_operation)
thread.start()
```

### Chunked Reading
```python
# Read in 4MB chunks for hashing
for chunk in iter(lambda: f.read(4096 * 1024), b''):
    hash_obj.update(chunk)
```

### Efficient Disk Queries
```python
# Query WMI once, cache results
self.disks = self.scan_disks()  # Cache
# Reuse cached data instead of re-querying
```

---

## 🔮 Future Enhancements

### Planned Features:
1. **Volume Shadow Copy (VSS)**
   - Clone running system using VSS snapshots
   - Requires `win32com` and VSS COM interfaces

2. **Compression**
   - Integrate `gzip`, `zstd` compression
   - Similar to Clonezilla's `-z` option

3. **Network Cloning**
   - Send images over network
   - Similar to Clonezilla SE

4. **Restore Functionality**
   - Restore from saved images
   - Automated partition recreation

5. **Differential Backups**
   - Only backup changed files
   - Save time and space

---

## 📝 Code Organization

```
windows-disk-cloner/
│
├── disk_cloner.py              # Core DiskCloner class + CLI
│   ├── class DiskCloner
│   │   ├── scan_disks()
│   │   ├── get_disk_partitions()
│   │   ├── clone_partition_filesystem()
│   │   ├── clone_partition_raw()
│   │   ├── save_disk_metadata()
│   │   ├── calculate_hash()
│   │   └── clone_disk_to_disk()
│   └── main() - CLI interface
│
├── disk_cloner_gui.py          # GUI wrapper
│   └── class DiskClonerGUI
│       ├── create_widgets()
│       ├── create_drive_to_image_tab()
│       ├── create_disk_to_disk_tab()
│       ├── start_drive_clone()
│       └── start_disk_clone()
│
└── DiskCloner.cs               # C# implementation
    ├── class DiskInfo
    ├── class PartitionInfo
    └── class DiskCloner
        ├── ScanDisks()
        ├── GetDiskPartitions()
        ├── ClonePartitionFilesystem()
        └── SaveDiskMetadata()
```

---

## 🎯 Design Principles

### 1. Clonezilla-Inspired
Every component maps to a Clonezilla equivalent, ensuring proven methodology.

### 2. Windows-Native
Use built-in Windows tools where possible (robocopy, WMI, PowerShell).

### 3. Safety First
Multiple checks, confirmations, and validations before destructive operations.

### 4. Transparency
Comprehensive logging shows exactly what the tool is doing.

### 5. Modularity
Each function has a single responsibility, making testing and maintenance easier.

---

**This architecture ensures reliability, safety, and Clonezilla-quality results on Windows!**
