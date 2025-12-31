# Quick Start: Clone C: Drive to E: Drive (New SSD)

## ⚠️ CRITICAL INFORMATION - READ FIRST!

### The Problem with Cloning C: While Windows is Running

**You CANNOT safely clone your system drive (C:) to another drive (E:) while Windows is running from C:!**

Here's why:
- Windows locks system files that are currently in use
- Boot files, registry, and system processes cannot be copied while active
- The clone will be incomplete and **will NOT boot**
- You may corrupt your running system

### The Solution

You have **TWO options**:

---

## 🎯 Option 1: Create a Backup Image (Recommended for This Tool)

**What this does:** Creates a complete backup of C: stored on E: as files
**When to use:** For backup/restore purposes, not direct cloning

### Steps:

#### 1. Build the Tool
```bash
cd "F:\2026 PROJECT\clonezilla-master\windows-disk-cloner"
build_exe.bat
```

#### 2. Run the GUI (Easiest Method)
```bash
# Right-click and "Run as Administrator"
dist\DiskClonerGUI.exe
```

#### 3. Create Backup Image
1. Go to **"Clone Drive to Image"** tab
2. **Source Drive:** Select `C: - Windows (XXX GB, NTFS)`
3. **Output Directory:** `E:\C_Drive_Backup`
4. **Enable:**
   - ✅ Generate MD5 checksums
   - ✅ Verify backup after completion
5. Click **"Start Backup"**

#### 4. Wait for Completion
- This may take 30 minutes to several hours depending on data size
- Monitor the log panel for progress
- Do NOT interrupt the process

#### 5. Verify the Backup
Check `E:\C_Drive_Backup\drive_C_YYYYMMDD_HHMMSS\` for:
- All your files from C:
- `checksums.md5` file
- `clone.log` file

### ⚠️ Important Notes:
- This creates a **FILE COPY**, not a bootable clone
- To restore, you need Windows Recovery Environment or Clonezilla Live
- This is best for **data backup**, not for making E: bootable

---

## 🎯 Option 2: True Disk Clone Using Clonezilla Live (Recommended for Bootable Clone)

**What this does:** Creates an exact bootable copy of C: on your new SSD
**When to use:** When you want to migrate Windows to a new SSD and boot from it

### Steps:

#### 1. Download Clonezilla Live
- Go to https://clonezilla.org/downloads.php
- Download the **ISO** file (clonezilla-live-X.X.X-amd64.iso)

#### 2. Create Bootable USB
```bash
# Option A: Use Rufus (https://rufus.ie/)
# 1. Download Rufus
# 2. Insert USB drive (8GB+ recommended)
# 3. Select Clonezilla ISO
# 4. Click "Start"

# Option B: Use Ventoy (https://www.ventoy.net/)
# 1. Install Ventoy to USB drive
# 2. Copy Clonezilla ISO to USB drive
```

#### 3. Prepare Your System
1. **Connect your new SSD (E:)** to your computer
   - If it's an external drive, ensure it's connected via USB 3.0+
   - If it's an internal drive, ensure it's properly installed
2. **Identify both drives** in Disk Management:
   - Press `Win + X` → Disk Management
   - Note which is Disk 0 (usually C:) and which is your new SSD
3. **Backup important data** (just in case!)

#### 4. Boot into Clonezilla Live
1. **Restart your computer**
2. **Enter BIOS/UEFI** (usually press F2, F12, Del, or Esc during boot)
3. **Change boot order** to boot from USB first
4. **Save and exit**
5. Your computer will boot into Clonezilla

#### 5. Clone in Clonezilla
1. Select **"Clonezilla live"** (default)
2. Choose language and keyboard layout
3. Select **"Start Clonezilla"**
4. Choose **"device-device"** (disk to disk clone)
5. Select **"Beginner mode"**
6. Choose **"disk_to_local_disk"**
7. **Source disk:** Select your current C: drive (usually /dev/sda or similar)
8. **Target disk:** Select your new SSD (E: drive)
9. Confirm the operation ⚠️ **THIS WILL ERASE E: DRIVE!**
10. Wait for cloning to complete (may take 1-3 hours)

#### 6. After Cloning
1. **Shutdown the computer**
2. **Disconnect the old C: drive** (if you want to use the new SSD as primary)
3. **Boot from the new SSD**
4. Verify Windows boots correctly
5. Check all data is present

#### 7. Optional: Expand Partition
If your new SSD is larger than the old drive:
1. Boot into Windows from new SSD
2. Open Disk Management (diskmgmt.msc)
3. Right-click the C: partition
4. Select "Extend Volume"
5. Use all available space

---

## 🤔 Which Option Should You Choose?

### Choose **Option 1** (This Tool - Backup Image) if:
- ✅ You want to **backup your data** for safety
- ✅ You're **keeping C: as your main drive**
- ✅ You want quick access to backup files on E:
- ✅ You plan to restore using Windows recovery tools
- ✅ You want to **practice** before doing a real clone

### Choose **Option 2** (Clonezilla Live - Bootable Clone) if:
- ✅ You want to **replace C: with a new SSD**
- ✅ You want the new drive to be **bootable**
- ✅ You're **migrating to a new drive**
- ✅ You want an **exact 1:1 copy** including boot sectors
- ✅ You want to **retire the old drive**

---

## 📊 Comparison Table

| Feature | Option 1: This Tool (Image) | Option 2: Clonezilla Live (Clone) |
|---------|----------------------------|-----------------------------------|
| **Boots from new drive** | ❌ No | ✅ Yes |
| **Running Windows** | ✅ Yes | ❌ No (must boot from USB) |
| **Speed** | Fast (file copy) | Slower (sector copy) |
| **Ease of use** | ⭐⭐⭐⭐⭐ Easy GUI | ⭐⭐⭐ Text interface |
| **Backup type** | File-based | Sector-based |
| **Compression** | No | Yes (optional) |
| **Restore process** | Manual / Windows tools | Clonezilla restore |
| **Best for** | Backups | Migrations |

---

## 🎬 Recommended Workflow

### Safest Approach: Do Both!

```
Step 1: Create backup with this tool
↓
Step 2: Verify backup is complete
↓
Step 3: Boot from Clonezilla Live USB
↓
Step 4: Clone C: → New SSD using Clonezilla
↓
Step 5: Test boot from new SSD
↓
Step 6: Keep the backup on E: for safety
```

---

## 🆘 Troubleshooting

### "Why can't I just run the .exe and clone C: to E:?"
Because Windows locks files on C: while it's running. It's like trying to move a house while you're still living in it!

### "What if I only want to backup my files, not the whole system?"
Then use Windows built-in tools:
- **File History** (Settings → Update & Security → Backup)
- **Robocopy** command: `robocopy C:\Users E:\Backup /MIR /COPYALL`
- Or use this tool to create an image backup

### "Can I restore the backup created by this tool?"
Yes, but you'll need:
- Windows Recovery Environment (WinRE)
- Or boot from Clonezilla and use "restoreparts" mode
- Or manually copy files back (tedious, not recommended for system files)

### "My new SSD is E:, how do I make it C:?"
After cloning with Clonezilla Live:
1. Shutdown
2. Disconnect the old C: drive
3. The new SSD will automatically become C: on next boot

### "How much space do I need on E: for the backup?"
At least as much as the **used space** on C: (not total size). Check in File Explorer → This PC → C: properties.

---

## 📞 Quick Reference Commands

### List all disks:
```bash
# CLI
python disk_cloner.py --list-disks

# Or in GUI: Go to "Disk Information" tab
```

### Create backup image:
```bash
# CLI (if you insist on command line)
python disk_cloner.py --clone-drive C: --output E:\Backups

# GUI: Use "Clone Drive to Image" tab (RECOMMENDED)
```

---

## ✅ Final Checklist Before Cloning

- [ ] I have backed up important data separately
- [ ] I have at least 20% free space on the target drive
- [ ] I am running as Administrator
- [ ] I understand the difference between backup and clone
- [ ] I have chosen the right option for my needs
- [ ] I have read the warnings about system drive cloning
- [ ] I have verified the source and target drives are correct
- [ ] I have time to wait for the operation to complete (don't interrupt!)

---

## 🎉 You're Ready!

Choose your option and follow the steps carefully. Good luck with your disk cloning!

**Remember:** When in doubt, create a backup first using this tool, then do the actual clone using Clonezilla Live bootable USB.

---

**Need help?** Review the main README.md or check Clonezilla documentation at https://clonezilla.org/
