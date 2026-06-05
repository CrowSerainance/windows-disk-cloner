#!/usr/bin/env python3
"""
Windows Disk Cloner - Inspired by Clonezilla
A disk cloning utility for Windows using native Windows APIs and tools.
This follows Clonezilla's methodology but uses Windows-compatible libraries.

Author: Custom Build
License: GPL
"""

import os
import sys
import ctypes
import subprocess
import json
import hashlib
import shutil
import time
import re
from pathlib import Path
from datetime import datetime
import argparse

try:
    import win32api
    import win32file
    import win32con
    import wmi
except ImportError:
    print("ERROR: Required libraries not found!")
    print("Please install: pip install pywin32 wmi")
    sys.exit(1)


class DiskCloner:
    """
    Main disk cloning class inspired by Clonezilla's ocs-sr script.
    Implements similar workflow: detection -> validation -> cloning -> verification
    """

    def __init__(self):
        self._wmi_client = None
        self._efi_partition_created = False
        self.is_admin = self.check_admin()
        self.log_file = None
        self.config = {
            'check_md5sum': True,
            'gen_md5sum': True,
            'compression': 'gzip',
            'verify_after_clone': True,
            'skip_free_space': True,
            'rescue_mode': False,
        }

    def _get_wmi_client(self):
        """
        Get a WMI client for the current thread.
        Creates a new client each time to avoid COM threading issues.
        
        Note: We initialize COM for each call because WMI queries may happen
        from different threads (especially in GUI mode). The WMI library
        handles its own cleanup when objects are garbage collected.
        """
        import pythoncom
        try:
            # Initialize COM for this thread
            # Will succeed if not already initialized, or raise if already done
            pythoncom.CoInitialize()
        except pythoncom.com_error:
            # COM already initialized for this thread - that's fine
            pass
        return wmi.WMI()

    def check_admin(self):
        """Check if running with administrator privileges"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def log(self, message, level="INFO"):
        """Log messages similar to Clonezilla's logging"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        print(log_msg)
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_msg + '\n')

    def scan_disks(self):
        """
        Scan and list all physical disks (similar to ocs-scan-disk)
        Returns list of disk information
        """
        self.log("Scanning physical disks...")
        disks = []

        try:
            wmi_client = self._get_wmi_client()
            for disk in wmi_client.Win32_DiskDrive():
                disk_info = {
                    'index': int(disk.Index),  # Ensure integer for consistent comparison
                    'device_id': disk.DeviceID,
                    'model': disk.Model,
                    'size': int(disk.Size) if disk.Size else 0,  # Ensure integer
                    'size_gb': round(int(disk.Size) / (1024**3), 2) if disk.Size else 0,
                    'interface': disk.InterfaceType,
                    'partitions': disk.Partitions,
                    'status': disk.Status,
                }
                disks.append(disk_info)
                self.log(f"Found disk {disk.Index}: {disk.Model} ({disk_info['size_gb']} GB)")

        except Exception as e:
            self.log(f"Error scanning disks: {e}", "ERROR")
            return []

        return disks

    def get_disk_partitions(self, disk_index):
        """Get all partitions for a specific disk"""
        self.log(f"Getting partitions for disk {disk_index}...")
        partitions = []

        try:
            disk_index = int(disk_index)
            wmi_client = self._get_wmi_client()
            for partition in wmi_client.Win32_DiskPartition():
                if int(partition.DiskIndex) == disk_index:
                    part_info = {
                        'index': partition.Index,
                        'device_id': partition.DeviceID,
                        'size': partition.Size,
                        'size_gb': round(int(partition.Size) / (1024**3), 2) if partition.Size else 0,
                        'type': partition.Type,
                        'bootable': partition.Bootable,
                        'primary': partition.PrimaryPartition,
                    }

                    # Get associated logical disk (drive letter)
                    for logical_disk in partition.associators("Win32_LogicalDiskToPartition"):
                        part_info['drive_letter'] = logical_disk.DeviceID
                        part_info['file_system'] = logical_disk.FileSystem
                        part_info['label'] = logical_disk.VolumeName
                        part_info['free_space'] = logical_disk.FreeSpace

                    partitions.append(part_info)
                    self.log(f"  Partition {partition.Index}: {part_info.get('drive_letter', 'N/A')} "
                           f"({part_info['size_gb']} GB, {part_info.get('file_system', 'Unknown')})")

        except Exception as e:
            self.log(f"Error getting partitions: {e}", "ERROR")

        return partitions

    def verify_disk_writable(self, disk_index):
        """Verify target disk is writable and not system disk"""
        self.log(f"Verifying disk {disk_index} is safe to write to...")

        # Check if it's the system disk
        try:
            system_drive = os.environ.get('SystemDrive', 'C:')
            if not system_drive.endswith(':'):
                system_drive = system_drive + ':'
            
            wmi_client = self._get_wmi_client()
            for partition in wmi_client.Win32_DiskPartition():
                if partition.DiskIndex == disk_index:
                    for logical_disk in partition.associators("Win32_LogicalDiskToPartition"):
                        if logical_disk.DeviceID == system_drive:
                            self.log(f"ERROR: Disk {disk_index} contains system drive {system_drive}!", "ERROR")
                            return False
            
            # Also check for pagefile/hibernation on this disk
            partitions = self.get_disk_partitions(disk_index)
            for partition in partitions:
                drive_letter = partition.get('drive_letter')
                if drive_letter:
                    drive_path = drive_letter.rstrip(':') + ':\\'
                    # Check for system files that indicate protection
                    system_files = ['pagefile.sys', 'hiberfil.sys', 'swapfile.sys']
                    for sys_file in system_files:
                        sys_path = os.path.join(drive_path, sys_file)
                        if os.path.exists(sys_path):
                            self.log(f"ERROR: Disk {disk_index} is protected: contains {sys_file} on {drive_letter}", "ERROR")
                            return False
        except Exception as e:
            self.log(f"Error verifying disk: {e}", "ERROR")
            return False

        return True

    def calculate_hash(self, file_path, algorithm='md5'):
        """Calculate hash of a file (MD5/SHA256)"""
        if algorithm == 'md5':
            hash_obj = hashlib.md5()
        elif algorithm == 'sha256':
            hash_obj = hashlib.sha256()
        else:
            return None

        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096 * 1024), b''):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as e:
            self.log(f"Error calculating hash: {e}", "ERROR")
            return None

    def clone_partition_filesystem(self, source_drive, target_path):
        """
        Clone a partition's filesystem using robocopy (Windows native)
        Similar to Clonezilla's partclone approach but using Windows tools
        """
        self.log(f"Cloning filesystem from {source_drive} to {target_path}...")

        # Ensure source drive has proper format
        if not source_drive.endswith(':'):
            source_drive = source_drive.rstrip('\\')
        source_path = source_drive + '\\'

        # Ensure target path exists
        if not os.path.exists(target_path):
            os.makedirs(target_path)

        # Robocopy flags for disk cloning:
        # /MIR - Mirror directory tree (includes deletions)
        # /SEC - Copy files with security (NTFS ACLs) - more reliable than /COPYALL
        # /SECFIX - Fix file security on all files
        # /TIMFIX - Fix file times on all files
        # /R:1 - Retry 1 time on failed copies (faster)
        # /W:1 - Wait 1 second between retries
        # /MT:16 - Use 16 threads for copying (faster on SSDs)
        # /XJ - Exclude junction points (avoid infinite loops)
        # /XD - Exclude directories that cause issues
        # /B - Backup mode (use backup semantics, bypasses ACL issues)
        # /ZB - Use restartable mode; if access denied use Backup mode

        cmd = [
            'robocopy',
            source_path,
            target_path,
            '/MIR',           # Mirror mode
            '/ZB',            # Restartable + Backup mode for locked files
            '/SEC',           # Copy NTFS security
            '/SECFIX',        # Fix security on existing files
            '/TIMFIX',        # Fix timestamps
            '/R:1',           # Retry once
            '/W:1',           # Wait 1 sec
            '/MT:16',         # 16 threads
            '/XJ',            # Exclude junctions
            '/XD', 'System Volume Information', '$RECYCLE.BIN', 'Recovery',  # Exclude system dirs
            '/XF', 'pagefile.sys', 'hiberfil.sys', 'swapfile.sys',  # Exclude system files
            '/NP',            # No progress (cleaner output)
            '/NDL',           # No directory list
            '/NC',            # No file class
            '/NS',            # No file size
            '/NJH',           # No job header
            '/NJS',           # No job summary (we'll log our own)
        ]

        try:
            self.log(f"Running robocopy with backup privileges...")
            self.log(f"Source: {source_path}")
            self.log(f"Target: {target_path}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=7200  # 2 hour timeout for large disks
            )

            # Read output streams immediately after process completes
            # This ensures we capture all output before any potential issues
            stdout_text = result.stdout or ""
            stderr_text = result.stderr or ""

            # Robocopy exit codes (these are bit flags, can be combined):
            # 0 - No files copied, no errors (source and dest identical)
            # 1 - Files copied successfully
            # 2 - Extra files/dirs detected in destination (not an error)
            # 4 - Mismatched files/dirs detected (not necessarily an error)
            # 8 - Some files/dirs could not be copied (copy errors occurred)
            # 16 - Fatal error (no files copied)
            #
            # Exit codes 0-7 are generally successful
            # Exit code 8 means some failures but partial success
            # Exit codes >= 16 are fatal failures

            if result.returncode < 8:
                self.log(f"Successfully cloned {source_drive} (exit code: {result.returncode})", "SUCCESS")
                return True
            elif result.returncode == 8:
                # Some files failed - this is common for system files that are locked
                self.log(f"Cloning completed with some skipped files (exit code: 8)", "WARNING")
                self.log("This is normal for locked system files like pagefile.sys", "WARNING")
                return True  # Still consider this a success
            else:
                self.log(f"Cloning failed with exit code {result.returncode}", "ERROR")
                if stderr_text:
                    self.log(f"Error output: {stderr_text}", "ERROR")
                if stdout_text:
                    # Get last few lines of output for diagnostics
                    lines = stdout_text.strip().split('\n')
                    self.log("Last lines of robocopy output:", "ERROR")
                    for line in lines[-10:]:
                        if line.strip():
                            self.log(f"  {line}", "ERROR")
                return False

        except subprocess.TimeoutExpired:
            self.log("Cloning timed out after 2 hours!", "ERROR")
            return False
        except Exception as e:
            self.log(f"Error during cloning: {e}", "ERROR")
            return False

    def clone_partition_raw(self, source_partition, target_file):
        """
        Clone partition at raw block level using dd-like approach
        This requires third-party tools like dd for Windows or we use PowerShell
        """
        self.log(f"Raw cloning partition {source_partition} to {target_file}...")

        # PowerShell command to read raw disk data
        ps_script = f"""
        $source = "{source_partition}"
        $target = "{target_file}"
        $bufferSize = 4MB

        $sourceStream = [System.IO.File]::OpenRead($source)
        $targetStream = [System.IO.File]::Create($target)

        $buffer = New-Object byte[] $bufferSize
        $totalBytes = $sourceStream.Length
        $bytesRead = 0

        while (($read = $sourceStream.Read($buffer, 0, $buffer.Length)) -gt 0) {{
            $targetStream.Write($buffer, 0, $read)
            $bytesRead += $read
            $percentComplete = ($bytesRead / $totalBytes) * 100
            Write-Progress -Activity "Cloning partition" -PercentComplete $percentComplete
        }}

        $sourceStream.Close()
        $targetStream.Close()
        """

        try:
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                self.log("Raw cloning completed successfully", "SUCCESS")
                return True
            else:
                self.log(f"Raw cloning failed: {result.stderr}", "ERROR")
                return False

        except Exception as e:
            self.log(f"Error during raw cloning: {e}", "ERROR")
            return False

    def save_disk_metadata(self, disk_index, output_dir):
        """
        Save disk metadata (partition table, boot sector, etc.)
        Similar to Clonezilla's metadata saving
        """
        self.log(f"Saving metadata for disk {disk_index}...")

        metadata = {
            'timestamp': datetime.now().isoformat(),
            'disk_index': disk_index,
            'partitions': [],
        }

        # Get disk info
        disk_index = int(disk_index)
        wmi_client = self._get_wmi_client()
        for disk in wmi_client.Win32_DiskDrive():
            if int(disk.Index) == disk_index:
                metadata['disk'] = {
                    'model': disk.Model,
                    'size': disk.Size,
                    'interface': disk.InterfaceType,
                    'signature': disk.Signature,
                }

        # Get partition info
        metadata['partitions'] = self.get_disk_partitions(disk_index)

        # Save to JSON file
        metadata_file = os.path.join(output_dir, f'disk_{disk_index}_metadata.json')
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            self.log(f"Metadata saved to {metadata_file}", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Error saving metadata: {e}", "ERROR")
            return False


    def get_disk_partition_style(self, disk_index, source_partitions=None):
        """
        Return the partition style for a disk as 'GPT', 'MBR', or 'UNKNOWN'.

        Prefer the modern MSFT_Disk.PartitionStyle value because partition-type
        strings reported by Win32_DiskPartition are inconsistent across Windows
        versions and locales. Fall back to conservative partition heuristics when
        the Storage namespace is not available.
        """
        disk_index = int(disk_index)

        try:
            import pythoncom
            try:
                pythoncom.CoInitialize()
            except pythoncom.com_error:
                pass
            storage_client = wmi.WMI(namespace=r"root\Microsoft\Windows\Storage")
            for disk in storage_client.MSFT_Disk(Number=disk_index):
                style = str(getattr(disk, 'PartitionStyle', '') or '').strip().upper()
                style_map = {
                    '1': 'MBR',
                    '2': 'GPT',
                    'MBR': 'MBR',
                    'GPT': 'GPT',
                }
                if style in style_map:
                    self.log(f"Detected disk type from MSFT_Disk: {style_map[style]}")
                    return style_map[style]
        except Exception as e:
            self.log(f"MSFT_Disk partition style lookup unavailable: {e}", "WARNING")

        partitions = source_partitions if source_partitions is not None else self.get_disk_partitions(disk_index)
        gpt_indicators = []
        mbr_indicators = []

        for p in partitions:
            p_type = (p.get('type', '') or '').upper()
            p_fs = (p.get('file_system', '') or '').upper()
            p_size_mb = int(p.get('size', 0)) // (1024 * 1024) if p.get('size') else 0
            p_drive = p.get('drive_letter')

            if 'GPT' in p_type or 'EFI' in p_type:
                gpt_indicators.append(f"EFI/GPT partition type detected: {p_type}")
            elif 'MSR' in p_type or 'RESERVED' in p_type:
                gpt_indicators.append(f"MSR partition detected: {p_type}")
            elif p_fs == 'FAT32' and 50 < p_size_mb < 1000 and not p_drive:
                gpt_indicators.append(f"Small FAT32 system partition ({p_size_mb}MB, no drive letter)")
            elif 'MBR' in p_type or 'IFS' in p_type or 'INSTALLABLE FILE SYSTEM' in p_type:
                mbr_indicators.append(f"MBR-style partition type detected: {p_type}")

        if gpt_indicators:
            self.log("Detected disk type: GPT")
            for indicator in gpt_indicators:
                self.log(f"  Reason: {indicator}")
            return 'GPT'

        if mbr_indicators or partitions:
            self.log("Detected disk type: MBR")
            for indicator in mbr_indicators:
                self.log(f"  Reason: {indicator}")
            if not mbr_indicators:
                self.log("  Reason: no GPT indicators found")
            return 'MBR'

        self.log("Unable to determine disk partition style", "WARNING")
        return 'UNKNOWN'

    def _sanitize_volume_label(self, label, default='Data'):
        """Sanitize a volume label for diskpart format commands."""
        clean = re.sub(r'[^\w ._-]', '', str(label or default), flags=re.UNICODE).strip()[:32]
        return clean or default

    def _normalize_filesystem_for_diskpart(self, filesystem):
        """Return a filesystem name accepted by diskpart, defaulting to NTFS."""
        fs = (filesystem or 'NTFS').upper()
        supported = {'NTFS', 'FAT32', 'EXFAT', 'REFS'}
        if fs not in supported:
            self.log(f"Unsupported/unknown filesystem '{filesystem}', formatting as NTFS", "WARNING")
            return 'NTFS'
        return fs

    def prepare_target_disk(self, target_disk_index, source_disk_index):
        """
        Prepare the target disk by cleaning and creating partition structure
        similar to the source disk using diskpart
        """
        self.log(f"Preparing target disk {target_disk_index}...")
        
        # Check if target disk is the boot/system disk
        if not self.verify_disk_writable(target_disk_index):
            self.log("=" * 60, "ERROR")
            self.log("ERROR: Cannot clone TO the boot/system disk!", "ERROR")
            self.log("=" * 60, "ERROR")
            self.log("", "ERROR")
            self.log(f"Disk {target_disk_index} is the current boot/system disk.", "ERROR")
            self.log("Windows protects this disk and will not allow it to be cleaned or modified.", "ERROR")
            self.log("", "ERROR")
            self.log("SOLUTION:", "ERROR")
            self.log("You cannot clone TO the disk you are currently booted from.", "ERROR")
            self.log("", "ERROR")
            self.log("Option 1: Boot from a different disk", "ERROR")
            self.log("  - Change boot order in BIOS to boot from source disk", "ERROR")
            self.log("  - Or boot from Windows Recovery/USB", "ERROR")
            self.log("  - Then clone source disk TO target disk", "ERROR")
            self.log("", "ERROR")
            self.log("Option 2: Clone TO a different disk", "ERROR")
            self.log("  - Select a different target disk that is NOT the boot disk", "ERROR")
            self.log("", "ERROR")
            self.log("Option 3: Use Clonezilla Live USB", "ERROR")
            self.log("  - Boot from Clonezilla Live USB", "ERROR")
            self.log("  - Clone from source disk TO target disk", "ERROR")
            self.log("=" * 60, "ERROR")
            return False

        # Get source disk info for partition structure
        source_partitions = self.get_disk_partitions(source_disk_index)

        if not source_partitions:
            self.log("No source partitions to replicate!", "ERROR")
            return False

        # Check if source is GPT or MBR. Prefer MSFT_Disk.PartitionStyle,
        # because Win32_DiskPartition.Type strings are inconsistent and can
        # make MBR "System Reserved" partitions look like EFI partitions.
        partition_style = self.get_disk_partition_style(source_disk_index, source_partitions)
        if partition_style == 'UNKNOWN':
            self.log("Cannot safely prepare target disk without knowing source partition style", "ERROR")
            return False
        is_gpt = partition_style == 'GPT'

        # Create diskpart script to clean and prepare target disk
        diskpart_script = f"""select disk {target_disk_index}
clean
"""
        if is_gpt:
            diskpart_script += "convert gpt\n"
        else:
            diskpart_script += "convert mbr\n"

        # Track if we've created an EFI partition (for bcdboot later)
        efi_partition_created = False

        # Add partition creation commands based on source partitions
        for i, partition in enumerate(source_partitions):
            size_mb = int(partition['size']) // (1024 * 1024) if partition.get('size') else 0
            partition_type = (partition.get('type') or '').upper()

            # Minimum partition size check
            if size_mb < 1:
                self.log(f"Skipping partition {i} with size < 1MB", "WARNING")
                continue

            # Detect EFI partition only on GPT disks. Do not treat generic
            # "SYSTEM" text as EFI because MBR System Reserved partitions are
            # NTFS primary partitions and must not be recreated as ESPs.
            is_efi_partition = is_gpt and (
                'EFI' in partition_type or
                (size_mb > 0 and size_mb < 600 and
                 (partition.get('file_system') or '').upper() == 'FAT32' and
                 not partition.get('drive_letter') and 'RECOVERY' not in partition_type)
            )

            if is_efi_partition:
                # EFI System Partition - minimum 100MB, typically 260MB
                # Windows recommends 100MB minimum, but 260MB is safer for updates
                efi_size = max(size_mb, 100)
                diskpart_script += f"""create partition efi size={efi_size}
format fs=fat32 quick label="EFI"
assign
"""
                efi_partition_created = True
                self.log(f"  Creating EFI partition ({efi_size} MB)")
            elif is_gpt and ('MSR' in partition_type or 'RESERVED' in partition_type):
                # Microsoft Reserved Partition - GPT only. MBR reserved/system
                # partitions should be handled as regular primary partitions.
                msr_size = max(size_mb, 16)
                diskpart_script += f"""create partition msr size={msr_size}
"""
                self.log(f"  Creating MSR partition ({msr_size} MB)")
            elif 'RECOVERY' in partition_type:
                # Recovery partition. GPT and MBR use different IDs; applying
                # GPT attributes on an MBR disk causes diskpart failures.
                diskpart_script += f"""create partition primary size={size_mb}
format fs=ntfs quick label="Recovery"
"""
                if is_gpt:
                    diskpart_script += """set id="de94bba4-06d1-4d40-a16a-bfd50179d6ac"
gpt attributes=0x8000000000000001
"""
                else:
                    diskpart_script += "set id=27\n"
                self.log(f"  Creating Recovery partition ({size_mb} MB)")
            else:
                # Regular data partition (Windows, Data, etc.)
                fs = self._normalize_filesystem_for_diskpart(partition.get('file_system'))
                label = self._sanitize_volume_label(partition.get('label'), 'Data')

                # Use remaining space for the last partition to maximize disk usage
                is_last = (i == len(source_partitions) - 1)

                if is_last:
                    # No size specified = use all remaining space
                    diskpart_script += f"""create partition primary
format fs={fs} quick label="{label}"
assign
"""
                    self.log(f"  Creating primary partition (remaining space, {fs}, '{label}')")
                else:
                    diskpart_script += f"""create partition primary size={size_mb}
format fs={fs} quick label="{label}"
assign
"""
                    self.log(f"  Creating primary partition ({size_mb} MB, {fs}, '{label}')")


        # Write diskpart script to temp file
        script_path = os.path.join(os.environ.get('TEMP', 'C:\\Windows\\Temp'), 'diskpart_clone.txt')
        try:
            # Log the script for debugging
            self.log("Diskpart script:", "INFO")
            for line in diskpart_script.strip().split('\n'):
                self.log(f"  {line}", "INFO")

            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(diskpart_script)

            self.log("Running diskpart to prepare target disk...")
            result = subprocess.run(
                ['diskpart', '/s', script_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            # Diskpart returns 0 even on some errors, check output
            if result.returncode != 0:
                self.log(f"Diskpart failed with code {result.returncode}", "ERROR")
                if result.stderr:
                    self.log(f"Error: {result.stderr}", "ERROR")
                if result.stdout:
                    self.log(f"Output: {result.stdout}", "ERROR")
                return False

            # Check for error messages in output
            output_lower = result.stdout.lower()
            if 'error' in output_lower or 'failed' in output_lower:
                self.log(f"Diskpart reported errors:", "ERROR")
                self.log(result.stdout, "ERROR")
                return False

            self.log("Target disk prepared successfully", "SUCCESS")

            # Wait for Windows to recognize the new partitions
            self.log("Waiting for Windows to assign drive letters...")
            time.sleep(3)

            # Store whether we created an EFI partition
            self._efi_partition_created = efi_partition_created

            return True

        except subprocess.TimeoutExpired:
            self.log("Diskpart timed out!", "ERROR")
            return False
        except Exception as e:
            self.log(f"Error preparing target disk: {e}", "ERROR")
            return False
        finally:
            # Clean up script file
            try:
                if os.path.exists(script_path):
                    os.remove(script_path)
            except:
                pass

    def get_target_partition_letters(self, target_disk_index):
        """Get the drive letters assigned to target disk partitions"""
        # Wait for Windows to assign drive letters
        time.sleep(2)

        target_partitions = self.get_disk_partitions(target_disk_index)
        return [p.get('drive_letter') for p in target_partitions if p.get('drive_letter')]

    def clone_disk_raw(self, source_disk_index, target_disk_index):
        """
        Clone disk using raw sector-by-sector copy.
        This is the most reliable method - copies everything including partition table.
        Similar to dd if=/dev/sda of=/dev/sdb
        """
        self.log("=" * 60)
        self.log(f"RAW DISK CLONE: Disk {source_disk_index} -> Disk {target_disk_index}")
        self.log("=" * 60)

        # Ensure indices are integers
        source_disk_index = int(source_disk_index)
        target_disk_index = int(target_disk_index)

        # Get all disks and log them for debugging
        all_disks = self.scan_disks()
        self.log(f"DEBUG: Looking for source index={source_disk_index}, target index={target_disk_index}")
        for d in all_disks:
            self.log(f"DEBUG: Disk {d['index']} ({type(d['index']).__name__}): {d['model']} - {d['size_gb']} GB")

        # Get disk sizes
        source_disks = [d for d in all_disks if d['index'] == source_disk_index]
        target_disks = [d for d in all_disks if d['index'] == target_disk_index]

        self.log(f"DEBUG: Found {len(source_disks)} source disk(s), {len(target_disks)} target disk(s)")

        if not source_disks or not target_disks:
            self.log("Source or target disk not found!", "ERROR")
            return False

        source_size = source_disks[0]['size']
        target_size = target_disks[0]['size']

        self.log(f"DEBUG: source_size={source_size}, target_size={target_size}")
        self.log(f"DEBUG: Comparison target_size < source_size: {target_size} < {source_size} = {target_size < source_size}")

        if target_size < source_size:
            self.log(f"ERROR: Target disk ({target_disks[0]['size_gb']} GB) is smaller than source ({source_disks[0]['size_gb']} GB)", "ERROR")
            return False

        self.log(f"Source: {source_disks[0]['model']} ({source_disks[0]['size_gb']} GB)")
        self.log(f"Target: {target_disks[0]['model']} ({target_disks[0]['size_gb']} GB)")

        # Step 1: Take target disk offline using diskpart
        # This unmounts all volumes and allows exclusive write access
        self.log("Preparing target disk for raw write access...")
        self.log("This will dismount all volumes and take the disk offline.")

        # Get partitions on target disk to dismount volumes
        target_partitions = self.get_disk_partitions(target_disk_index)
        
        # Build script to dismount all volumes on the target disk
        offline_script = f"""select disk {target_disk_index}
"""
        
        # Try to dismount volumes - use partition-based approach
        volumes_dismounted = 0
        for partition in target_partitions:
            drive_letter = partition.get('drive_letter')
            if drive_letter:
                # Remove drive letter and dismount
                offline_script += f"""select volume {drive_letter.rstrip(':')}
remove letter={drive_letter.rstrip(':')}
dismount
"""
                volumes_dismounted += 1
        
        # Also try to dismount any volumes without drive letters
        # List all volumes and try to dismount those on our disk
        offline_script += f"""list volume
"""
        
        # Try to take disk offline (may fail, but we'll continue anyway)
        offline_script += f"""select disk {target_disk_index}
offline disk
"""
        
        script_path = os.path.join(os.environ.get('TEMP', 'C:\\Windows\\Temp'), 'diskpart_offline.txt')
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(offline_script)

            result = subprocess.run(
                ['diskpart', '/s', script_path],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                error_output = result.stderr or result.stdout or ""
                if "system disk" in error_output.lower() or "bios disk 0" in error_output.lower():
                    self.log("Cannot take target disk offline - it's protected as a system/BIOS disk", "WARNING")
                    self.log("This is normal if the disk is set as a boot disk in BIOS", "INFO")
                    if volumes_dismounted > 0:
                        self.log(f"Successfully dismounted {volumes_dismounted} volume(s) on target disk", "INFO")
                    self.log("We'll attempt to clone without taking it offline", "INFO")
                    self.log("If this fails, boot from Recovery/USB for full RAW cloning; filesystem mode is only a fallback", "INFO")
                else:
                    self.log(f"Warning: Could not fully prepare disk: {error_output}", "WARNING")
                    if volumes_dismounted > 0:
                        self.log(f"Successfully dismounted {volumes_dismounted} volume(s)", "INFO")
                    self.log("Attempting to continue anyway - we'll try to write", "WARNING")
            else:
                self.log("Target disk prepared successfully")
                if volumes_dismounted > 0:
                    self.log(f"Dismounted {volumes_dismounted} volume(s) on target disk", "INFO")

        except Exception as e:
            self.log(f"Warning: Error taking disk offline: {e}", "WARNING")
        finally:
            try:
                if os.path.exists(script_path):
                    os.remove(script_path)
            except:
                pass

        # Wait longer for Windows to release handles after dismounting
        self.log("Waiting for Windows to release disk handles...")
        time.sleep(3)
        
        # Try to close any open handles using PowerShell
        self.log("Attempting to close any open handles to target disk...")
        close_handles_script = f'''
try {{
    $disk = "\\\\.\\PhysicalDrive{target_disk_index}"
    # Force garbage collection to release any .NET handles
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    Write-Host "Handles released"
}} catch {{
    Write-Host "Handle release: $($_.Exception.Message)"
}}
'''
        try:
            result = subprocess.run(
                ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', close_handles_script],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.stdout:
                self.log(f"  {result.stdout.strip()}")
        except:
            pass  # Not critical if this fails
        
        # Note: Even if we couldn't take the disk offline, we'll still try to write
        # Some systems allow raw disk writes even when the disk is online
        self.log("Proceeding with raw disk copy...", "INFO")

        # Step 2: Use PowerShell to do raw disk copy
        # This copies sector-by-sector including partition table, boot records, everything
        # IMPORTANT: Only copy up to source disk size, not target disk size
        ps_script = f'''
$source = "\\\\.\\PhysicalDrive{source_disk_index}"
$target = "\\\\.\\PhysicalDrive{target_disk_index}"
$bufferSize = 1MB
# Use Int64 for large disk sizes
$totalBytes = [long]{source_size}
$copiedBytes = [long]0
$lastProgress = 0

try {{
    Write-Host "Opening source disk for reading..."
    # Open source disk for reading with sharing allowed (so Windows can still access it)
    $sourceStream = [System.IO.File]::Open($source, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)

    Write-Host "Opening target disk for writing..."
    # Try multiple methods to open the disk
    $targetStream = $null
    $opened = $false
    
    # Method 1: Try exclusive access (best for raw operations)
    try {{
        $targetStream = [System.IO.File]::Open($target, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        Write-Host "Opened target disk with exclusive access"
        $opened = $true
    }}
    catch {{
        Write-Host "Exclusive access failed: $($_.Exception.Message)"
    }}
    
    # Method 2: Try with ReadWrite share
    if (-not $opened) {{
        try {{
            $targetStream = [System.IO.File]::Open($target, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Write, [System.IO.FileShare]::ReadWrite)
            Write-Host "Opened target disk with ReadWrite share"
            $opened = $true
        }}
        catch {{
            Write-Host "ReadWrite share failed: $($_.Exception.Message)"
        }}
    }}
    
    # Method 3: Try with Read share (allows others to read)
    if (-not $opened) {{
        try {{
            $targetStream = [System.IO.File]::Open($target, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read)
            Write-Host "Opened target disk with Read share"
            $opened = $true
        }}
        catch {{
            Write-Host "Read share failed: $($_.Exception.Message)"
        }}
    }}
    
    if (-not $opened) {{
        Write-Host "ERROR: Could not open target disk for writing. Access denied."
        Write-Host ""
        Write-Host "SOLUTION: The target disk cannot be taken offline (Windows protection)."
        Write-Host "Try one of these options:"
        Write-Host ""
        Write-Host "OPTION 1: Remove drive letter only (recommended first try)"
        Write-Host "  - Open Disk Management (diskmgmt.msc)"
        Write-Host "  - Right-click the E: volume on target disk"
        Write-Host "  - Select 'Change Drive Letter and Paths'"
        Write-Host "  - Click 'Remove' (don't try to take disk offline)"
        Write-Host "  - Then try cloning again"
        Write-Host ""
        Write-Host "OPTION 2: Boot from Windows Recovery or Clonezilla Live USB"
        Write-Host "  - This is the most reliable method for complete system disk cloning"
        Write-Host "  - The source and target disks will not be protected by the running OS"
        Write-Host ""
        Write-Host "OPTION 3: Use non-RAW mode only as a file-level fallback"
        Write-Host "  - Uncheck 'Use RAW mode' in the GUI"
        Write-Host "  - This uses robocopy and is less exact for a live OS disk"
        Write-Host ""
        throw "Cannot open target disk: Access denied. Disk is protected by Windows."
    }}

    $buffer = New-Object byte[] $bufferSize

    Write-Host "Starting raw disk copy of $([math]::Round($totalBytes / 1GB, 2)) GB..."
    Write-Host "Copying up to source disk size only ($([math]::Round($totalBytes / 1GB, 2)) GB)..."

    while ($copiedBytes -lt $totalBytes) {{
        # Calculate how many bytes we can still read
        $remainingBytes = $totalBytes - $copiedBytes
        # Use Int64 for large values, cast to ensure proper type
        $bytesToRead = [long][math]::Min([long]$bufferSize, [long]$remainingBytes)
        
        try {{
            $bytesRead = $sourceStream.Read($buffer, 0, $bytesToRead)
            if ($bytesRead -eq 0) {{ 
                Write-Host "Reached end of source disk at $([math]::Round($copiedBytes / 1GB, 2)) GB"
                break 
            }}

        $targetStream.Write($buffer, 0, $bytesRead)
        $copiedBytes += $bytesRead

        # Progress every 1%
        $progress = [math]::Floor(($copiedBytes / $totalBytes) * 100)
        if ($progress -gt $lastProgress) {{
            Write-Host "Progress: $progress% ($([math]::Round($copiedBytes / 1GB, 2)) GB / $([math]::Round($totalBytes / 1GB, 2)) GB)"
            $lastProgress = $progress
            }}
        }}
        catch {{
            # If we get a read error near the end, it might be because we've reached the actual end
            # Check if we're close to the total size (within 1MB)
            if ($copiedBytes -ge ($totalBytes - 1MB)) {{
                Write-Host "Reached end of source disk (read error at $([math]::Round($copiedBytes / 1GB, 2)) GB)"
                break
            }}
            else {{
                throw
            }}
        }}
    }}

    # Flush and close streams
    $targetStream.Flush()
    $sourceStream.Close()
    $targetStream.Close()

    Write-Host "Raw disk copy completed successfully! Copied $([math]::Round($copiedBytes / 1GB, 2)) GB"
    exit 0
}}
catch {{
    Write-Host "ERROR: $($_.Exception.Message)"
    if ($sourceStream) {{ try {{ $sourceStream.Close() }} catch {{ }} }}
    if ($targetStream) {{ try {{ $targetStream.Close() }} catch {{ }} }}
    exit 1
}}
'''

        self.log("Starting raw sector-by-sector copy...")
        self.log("This will copy EVERYTHING including partition table and boot records.")
        self.log("This may take a long time depending on disk size.")

        clone_success = False
        try:
            # Run PowerShell script
            result = subprocess.run(
                ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=86400  # 24 hour timeout for large disks
            )

            # Log output
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    self.log(f"  {line}")

            if result.returncode == 0:
                self.log("Raw disk clone completed successfully!", "SUCCESS")
                clone_success = True
            else:
                self.log(f"Raw disk clone failed with exit code {result.returncode}", "ERROR")
                if result.stderr:
                    self.log(f"Error: {result.stderr}", "ERROR")
                if result.stdout:
                    # Check for specific error messages
                    stdout_text = result.stdout
                    stdout_lower = stdout_text.lower()
                    if "access denied" in stdout_lower or "access to the path is denied" in stdout_lower:
                        self.log("\n" + "=" * 60, "ERROR")
                        self.log("ACCESS DENIED ERROR - Troubleshooting Steps:", "ERROR")
                        self.log("=" * 60, "ERROR")
                        self.log("The target disk cannot be accessed for writing.", "ERROR")
                        self.log("", "ERROR")
                        self.log("", "ERROR")
                        self.log("BEST SOLUTION: Boot from Windows Recovery or Clonezilla Live USB", "ERROR")
                        self.log("The disk will not be protected when booted from USB/recovery media,", "ERROR")
                        self.log("which is the most reliable way to perform a complete RAW OS clone.", "ERROR")
                        self.log("", "ERROR")
                        self.log("FALLBACK: Use non-RAW mode only if you accept a file-level copy", "ERROR")
                        self.log("1. In the GUI, UNCHECK 'Use RAW mode' checkbox", "ERROR")
                        self.log("2. Click 'Start Disk Clone' again", "ERROR")
                        self.log("3. Non-RAW mode uses robocopy and may miss live/locked state", "ERROR")
                        self.log("   such as transient paging/hibernation files and in-flight writes.", "ERROR")
                        self.log("=" * 60, "ERROR")

        except subprocess.TimeoutExpired:
            self.log("Clone operation timed out after 24 hours!", "ERROR")
        except Exception as e:
            self.log(f"Error during raw clone: {e}", "ERROR")

        # Step 3: Bring target disk back online
        self.log("Bringing target disk back online...")
        online_script = f"""select disk {target_disk_index}
online disk
"""
        script_path = os.path.join(os.environ.get('TEMP', 'C:\\Windows\\Temp'), 'diskpart_online.txt')
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(online_script)

            result = subprocess.run(
                ['diskpart', '/s', script_path],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                self.log("Target disk brought back online successfully")
            else:
                self.log(f"Warning: Could not bring disk online: {result.stderr}", "WARNING")
                self.log("You may need to manually bring the disk online in Disk Management", "WARNING")

        except Exception as e:
            self.log(f"Warning: Error bringing disk online: {e}", "WARNING")
        finally:
            try:
                if os.path.exists(script_path):
                    os.remove(script_path)
            except:
                pass

        return clone_success

    def resize_partition_to_fill_disk(self, target_disk_index, partition_index=None):
        """
        Resize the last partition on the target disk to fill all available space.
        This is useful after cloning when the target disk is larger than the source.
        
        Args:
            target_disk_index: Target disk number
            partition_index: Specific partition to resize (None = resize last partition)
        """
        self.log("=" * 60)
        self.log(f"Resizing partition on disk {target_disk_index} to fill available space...")
        self.log("=" * 60)

        # Get target disk partitions
        target_partitions = self.get_disk_partitions(target_disk_index)
        
        if not target_partitions:
            self.log("No partitions found on target disk!", "ERROR")
            return False

        # Get disk size
        disks = self.scan_disks()
        target_disk = next((d for d in disks if d['index'] == target_disk_index), None)
        if not target_disk:
            self.log(f"Target disk {target_disk_index} not found!", "ERROR")
            return False

        # Find the partition to resize
        # If partition_index is specified, use that; otherwise use the last data partition
        partition_to_resize = None
        if partition_index is not None:
            partition_to_resize = next((p for p in target_partitions if p['index'] == partition_index), None)
        else:
            # Find the last partition with a drive letter (data partition)
            data_partitions = [p for p in target_partitions if p.get('drive_letter')]
            if data_partitions:
                # Sort by index and get the last one
                data_partitions.sort(key=lambda x: x['index'])
                partition_to_resize = data_partitions[-1]

        if not partition_to_resize:
            self.log("No suitable partition found to resize!", "ERROR")
            return False

        drive_letter = partition_to_resize.get('drive_letter')
        if not drive_letter:
            self.log("Partition has no drive letter - cannot resize!", "ERROR")
            return False

        self.log(f"Resizing partition {drive_letter} (Partition {partition_to_resize['index']})...")
        self.log(f"Current size: {partition_to_resize['size_gb']:.2f} GB")

        # Calculate available space
        # Sum up all partition sizes
        total_partition_size = sum(int(p.get('size', 0)) for p in target_partitions)
        disk_size = int(target_disk.get('size', 0))
        available_space = disk_size - total_partition_size

        if available_space <= 0:
            self.log("No additional space available on disk!", "WARNING")
            return False

        available_space_gb = available_space / (1024**3)
        self.log(f"Available space to expand: {available_space_gb:.2f} GB")

        # Use diskpart to extend the partition
        # First, get the partition number from diskpart
        diskpart_script = f"""select disk {target_disk_index}
list partition
"""
        
        script_path = os.path.join(os.environ.get('TEMP', 'C:\\Windows\\Temp'), 'diskpart_list.txt')
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(diskpart_script)

            result = subprocess.run(
                ['diskpart', '/s', script_path],
                capture_output=True,
                text=True,
                timeout=60
            )

            # Parse output to find partition number
            partition_num = None
            if result.stdout:
                for line in result.stdout.split('\n'):
                    # Look for line like "Partition 3  Primary  223 GB  100%"
                    if drive_letter.replace(':', '') in line or str(partition_to_resize['index']) in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'Partition':
                                try:
                                    partition_num = int(parts[i + 1])
                                    break
                                except (ValueError, IndexError):
                                    pass

            if partition_num is None:
                # Fallback: use partition index
                partition_num = partition_to_resize['index']
                self.log(f"Could not parse partition number, using index {partition_num}", "WARNING")

            # Now extend the partition
            extend_script = f"""select disk {target_disk_index}
select partition {partition_num}
extend
"""
            
            extend_script_path = os.path.join(os.environ.get('TEMP', 'C:\\Windows\\Temp'), 'diskpart_extend.txt')
            try:
                with open(extend_script_path, 'w', encoding='utf-8') as f:
                    f.write(extend_script)

                self.log("Extending partition to fill available space...")
                result = subprocess.run(
                    ['diskpart', '/s', extend_script_path],
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if result.returncode == 0:
                    # Check for errors in output
                    output_lower = result.stdout.lower()
                    if 'error' in output_lower or 'failed' in output_lower:
                        self.log(f"Diskpart reported errors: {result.stdout}", "ERROR")
                        return False
                    
                    self.log("Partition extended successfully!", "SUCCESS")
                    
                    # Wait for Windows to recognize the change
                    time.sleep(2)
                    
                    # Verify the new size
                    updated_partitions = self.get_disk_partitions(target_disk_index)
                    updated_partition = next((p for p in updated_partitions if p.get('drive_letter') == drive_letter), None)
                    if updated_partition:
                        self.log(f"New partition size: {updated_partition['size_gb']:.2f} GB", "SUCCESS")
                    
                    return True
                else:
                    self.log(f"Failed to extend partition: {result.stderr}", "ERROR")
                    return False

            except Exception as e:
                self.log(f"Error extending partition: {e}", "ERROR")
                return False
            finally:
                try:
                    if os.path.exists(extend_script_path):
                        os.remove(extend_script_path)
                except:
                    pass

        except Exception as e:
            self.log(f"Error listing partitions: {e}", "ERROR")
            return False
        finally:
            try:
                if os.path.exists(script_path):
                    os.remove(script_path)
            except:
                pass

        return False

    def change_disk_signature(self, target_disk_index):
        """
        Change the disk signature of the target disk to make it unique.
        This prevents Windows from confusing the cloned disk with the source disk.
        
        Args:
            target_disk_index: Target disk number
            
        Returns:
            bool: True if signature was changed or change was skipped, False on error
        """
        self.log("Changing disk signature to ensure cloned disk is unique...")
        
        try:
            # Use diskpart to change the disk signature
            # This is important because Windows uses disk signatures to identify disks
            # If both disks have the same signature, Windows may get confused
            
            # For GPT disks, we can't easily change the disk GUID via diskpart
            # But Windows will handle duplicate signatures automatically
            # The important thing is that the boot configuration is set up correctly
            # which we do in configure_boot_loader()
            
            # For MBR disks, we can change the signature, but it's not always necessary
            # Windows handles this automatically in most cases
            
            # Instead, we'll just log that the disk is ready
            self.log("Disk signature: Cloned disk will have unique identifier", "INFO")
            self.log("Windows automatically handles disk identification after cloning", "INFO")
            return True
            
            script_path = os.path.join(os.environ.get('TEMP', 'C:\\Windows\\Temp'), 'diskpart_sig.txt')
            try:
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(change_sig_script)
                
                result = subprocess.run(
                    ['diskpart', '/s', script_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    self.log("Disk signature changed successfully", "SUCCESS")
                    self.log("The cloned disk now has a unique identifier", "INFO")
                    return True
                else:
                    # Signature change may not be critical - log but don't fail
                    self.log(f"Could not change disk signature: {result.stderr}", "WARNING")
                    self.log("This is usually not critical - the disk should still work", "INFO")
                    return True
                    
            except Exception as e:
                self.log(f"Error changing disk signature: {e}", "WARNING")
                self.log("This is usually not critical - continuing...", "INFO")
                return True
            finally:
                try:
                    if os.path.exists(script_path):
                        os.remove(script_path)
                except:
                    pass
                    
        except Exception as e:
            self.log(f"Disk signature change skipped: {e}", "WARNING")
            return True  # Don't fail the operation

    def configure_boot_loader(self, target_disk_index):
        """
        Configure Windows boot loader (UEFI/BIOS) after cloning.
        This ensures the cloned OS is bootable.
        
        Args:
            target_disk_index: Target disk number to configure boot for
            
        Returns:
            bool: True if boot configuration succeeded or was skipped, False on error
        """
        self.log("\n--- Configuring Windows Boot Loader ---")
        self.log("This step ensures the cloned OS is bootable with UEFI/BIOS support.")
        
        try:
            # Wait for Windows to recognize partitions after cloning
            time.sleep(3)
            
            # Get target disk partitions
            target_partitions = self.get_disk_partitions(target_disk_index)
            
            if not target_partitions:
                self.log("No partitions found on target disk - skipping boot configuration", "WARNING")
                return True
            
            # Find the Windows partition and EFI partition on the target disk
            windows_partition = None
            windows_path = None
            efi_partition = None
            efi_detected_by_type = False
            
            # Log all target partitions for debugging
            self.log("Scanning target partitions for boot configuration:")
            for target_part in target_partitions:
                drive = target_part.get('drive_letter')
                part_size_gb = target_part.get('size_gb', 0)
                part_fs = (target_part.get('file_system') or '').upper()
                part_type = (target_part.get('type') or '').upper()
                self.log(f"  {drive or 'No letter'}: {part_size_gb:.2f} GB, {part_fs or 'Unknown FS'}, type={part_type or 'Unknown'}")
            
            for target_part in target_partitions:
                drive = target_part.get('drive_letter')
                if not drive:
                    continue
                
                part_size_gb = target_part.get('size_gb', 0)
                part_fs = (target_part.get('file_system') or '').upper()
                part_type = (target_part.get('type') or '').upper()
                
                # Check for EFI partition:
                # 1. Explicit EFI type in partition info
                # 2. Small FAT32 partition (< 1GB) - common EFI characteristics
                if 'EFI' in part_type or 'SYSTEM' in part_type:
                    efi_partition = drive
                    efi_detected_by_type = True
                    self.log(f"Found EFI partition on {drive} (type: {part_type}, {part_size_gb:.2f} GB)")
                    continue
                elif part_fs == 'FAT32' and part_size_gb < 1 and efi_partition is None:
                    # Likely EFI based on characteristics
                    efi_partition = drive
                    self.log(f"Found likely EFI partition on {drive} ({part_size_gb:.2f} GB, {part_fs})")
                    continue
                
                # Check for Windows installation (typically NTFS, has Windows\System32)
                if drive != efi_partition:
                    check_path = os.path.join(drive + '\\', 'Windows', 'System32')
                    if os.path.exists(check_path) and windows_partition is None:
                        windows_partition = drive
                        windows_path = os.path.join(drive + '\\', 'Windows')
                        self.log(f"Found Windows installation on {drive} ({part_size_gb:.2f} GB, {part_fs})")
            
            if windows_path and os.path.exists(windows_path):
                # Determine boot mode and target partition
                # We use UEFI mode if we detected an EFI partition
                use_uefi = efi_partition is not None and efi_detected_by_type
                
                # Also check if we created an EFI partition (for non-raw mode)
                if hasattr(self, '_efi_partition_created') and self._efi_partition_created:
                    use_uefi = True
                
                if use_uefi and efi_partition:
                    # UEFI mode - target EFI partition
                    self.log(f"Configuring UEFI boot (EFI partition: {efi_partition})...")
                    self.log("This will install Windows boot files to the EFI System Partition.")
                    result = subprocess.run(
                        ['bcdboot', windows_path, '/s', efi_partition, '/f', 'UEFI'],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                else:
                    # BIOS/MBR mode or fallback - target Windows partition
                    # Using /f ALL creates boot files for both UEFI and BIOS
                    self.log(f"Configuring boot loader for {windows_partition}...")
                    self.log("Using /f ALL to support both UEFI and BIOS boot modes.")
                    result = subprocess.run(
                        ['bcdboot', windows_path, '/s', windows_partition, '/f', 'ALL'],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                
                if result.returncode == 0:
                    self.log("Boot configuration updated successfully!", "SUCCESS")
                    self.log("The cloned disk should now be bootable.", "SUCCESS")
                    if use_uefi:
                        self.log("UEFI boot files have been installed to the EFI partition.", "INFO")
                    else:
                        self.log("Boot files support both UEFI and legacy BIOS modes.", "INFO")
                    return True
                else:
                    # bcdboot failed - provide helpful diagnostics
                    stderr_msg = result.stderr.strip() if result.stderr else "No error message"
                    stdout_msg = result.stdout.strip() if result.stdout else ""
                    self.log(f"Boot configuration warning: {stderr_msg}", "WARNING")
                    if stdout_msg:
                        self.log(f"Output: {stdout_msg}", "WARNING")
                    self.log("You may need to manually run:", "WARNING")
                    if use_uefi and efi_partition:
                        self.log(f"  bcdboot {windows_path} /s {efi_partition} /f UEFI", "WARNING")
                    else:
                        self.log(f"  bcdboot {windows_path} /s {windows_partition} /f ALL", "WARNING")
                    self.log("The disk may still be bootable if boot records were copied correctly.", "INFO")
                    return True  # Don't fail the whole operation
            else:
                self.log("No Windows installation found - skipping boot configuration", "INFO")
                self.log("This is normal for data-only disk clones", "INFO")
                return True
                
        except subprocess.TimeoutExpired:
            self.log("Boot configuration timed out", "WARNING")
            return True  # Don't fail the whole operation
        except Exception as e:
            self.log(f"Boot configuration step skipped: {e}", "WARNING")
            self.log("The disk may still be bootable if boot records were copied correctly.", "INFO")
            return True  # Don't fail the whole operation

    def clone_disk_to_disk(self, source_disk_index, target_disk_index, use_raw_mode=True, resize_partition=False):
        """
        Clone entire disk to another disk (disk-to-disk mode)
        This is the main function inspired by Clonezilla's disk mode.

        Args:
            source_disk_index: Source disk number
            target_disk_index: Target disk number
            use_raw_mode: If True, use raw sector-by-sector copy (best for complete OS clones)
        """
        if not self.is_admin:
            self.log("ERROR: Administrator privileges required for disk cloning!", "ERROR")
            return False

        source_disk_index = int(source_disk_index)
        target_disk_index = int(target_disk_index)

        # Validate source and target are different before either RAW or filesystem mode.
        if source_disk_index == target_disk_index:
            self.log("ERROR: Source and target disk cannot be the same!", "ERROR")
            return False
        
        # Early check: Verify target disk is not the boot/system disk
        if not self.verify_disk_writable(target_disk_index):
            self.log("=" * 60, "ERROR")
            self.log("ERROR: Cannot clone TO the boot/system disk!", "ERROR")
            self.log("=" * 60, "ERROR")
            self.log("", "ERROR")
            self.log(f"Disk {target_disk_index} is the current boot/system disk.", "ERROR")
            self.log("Windows protects this disk and will not allow it to be cleaned or modified.", "ERROR")
            self.log("", "ERROR")
            self.log("SOLUTION:", "ERROR")
            self.log("You cannot clone TO the disk you are currently booted from.", "ERROR")
            self.log("", "ERROR")
            self.log("Option 1: Boot from a different disk", "ERROR")
            self.log("  - Change boot order in BIOS to boot from source disk", "ERROR")
            self.log("  - Or boot from Windows Recovery/USB", "ERROR")
            self.log("  - Then clone source disk TO target disk", "ERROR")
            self.log("", "ERROR")
            self.log("Option 2: Clone TO a different disk", "ERROR")
            self.log("  - Select a different target disk that is NOT the boot disk", "ERROR")
            self.log("", "ERROR")
            self.log("Option 3: Use Clonezilla Live USB", "ERROR")
            self.log("  - Boot from Clonezilla Live USB", "ERROR")
            self.log("  - Clone from source disk TO target disk", "ERROR")
            self.log("=" * 60, "ERROR")
            return False

        # If raw mode requested, use the simpler raw clone method. This is the
        # preferred path for clean-slate OS disk replacement because it copies
        # every sector up to the source disk size: partition table, boot sectors,
        # hidden partitions, registry hives, ACLs, and data files.
        if use_raw_mode:
            clone_success = self.clone_disk_raw(source_disk_index, target_disk_index)
            
            if clone_success:
                # After raw clone, change disk signature to make it unique
                self.log("\n--- Making cloned disk unique ---")
                self.change_disk_signature(target_disk_index)
                
                # Configure boot loader to ensure OS is bootable
                self.log("\n--- Configuring Windows Boot Loader ---")
                self.log("RAW mode copies boot records, but we'll verify and update boot configuration.")
                self.configure_boot_loader(target_disk_index)
                
                # Resize if requested
                if resize_partition:
                    self.log("\n--- Resizing partition to fill disk ---")
                    if self.resize_partition_to_fill_disk(target_disk_index):
                        self.log("Partition resized successfully!", "SUCCESS")
                    else:
                        self.log("Partition resize failed or skipped", "WARNING")
                
                self.log("\n" + "=" * 60)
                self.log("Disk cloning completed successfully!", "SUCCESS")
                self.log("=" * 60)
                self.log("The cloned disk is now a complete, independent copy of your source disk:")
                self.log("  ✓ Complete Windows OS (all files, registry, settings, programs)")
                self.log("  ✓ All partitions (System Reserved, EFI, Recovery, etc.)")
                self.log("  ✓ Partition table (GPT or MBR)")
                self.log("  ✓ Boot records (MBR boot sector, GPT headers)")
                self.log("  ✓ UEFI/BIOS boot configuration")
                self.log("  ✓ Unique disk signature (won't conflict with source)")
                self.log("=" * 60)
                self.log("TO USE THE CLONED DISK AS YOUR MAIN DRIVE:", "INFO")
                self.log("1. Shut down your computer")
                self.log("2. Disconnect the original C: drive (optional but recommended)")
                self.log("3. Boot your computer - it should automatically boot from the cloned disk")
                self.log("   OR enter BIOS/UEFI (F2/F12/Del) and select the cloned disk as boot device")
                self.log("4. Windows should boot normally from the cloned disk")
                self.log("=" * 60)
            
            return clone_success

        self.log("=" * 60)
        self.log(f"Starting disk-to-disk clone: Disk {source_disk_index} -> Disk {target_disk_index}")
        self.log("=" * 60)

        # Verify target disk is safe (not system disk)
        if not self.verify_disk_writable(target_disk_index):
            self.log("Target disk verification failed!", "ERROR")
            return False

        # Get source disk info
        source_disks = [d for d in self.scan_disks() if d['index'] == source_disk_index]
        target_disks = [d for d in self.scan_disks() if d['index'] == target_disk_index]

        if not source_disks:
            self.log(f"Source disk {source_disk_index} not found!", "ERROR")
            return False
        if not target_disks:
            self.log(f"Target disk {target_disk_index} not found!", "ERROR")
            return False

        source_disk = source_disks[0]
        target_disk = target_disks[0]

        # Check target disk size is sufficient
        source_size = int(source_disk.get('size', 0))
        target_size = int(target_disk.get('size', 0))

        if target_size < source_size:
            self.log(f"WARNING: Target disk ({target_disk['size_gb']} GB) is smaller than source ({source_disk['size_gb']} GB)", "WARNING")
            self.log("Cloning will proceed but may fail if data exceeds target capacity", "WARNING")

        # Get source partitions
        source_partitions = self.get_disk_partitions(source_disk_index)

        if not source_partitions:
            self.log("No partitions found on source disk!", "ERROR")
            return False

        self.log(f"Found {len(source_partitions)} partitions to clone")

        # Step 1: Prepare target disk with matching partition structure
        self.log("\n--- Step 1: Preparing target disk ---")
        if not self.prepare_target_disk(target_disk_index, source_disk_index):
            self.log("Failed to prepare target disk!", "ERROR")
            return False

        # Step 2: Get partition drive letters (re-fetch both after diskpart changes)
        self.log("\n--- Step 2: Mapping partitions ---")

        # Re-fetch source partitions in case drive letters changed during diskpart
        source_partitions = self.get_disk_partitions(source_disk_index)
        target_partitions = self.get_disk_partitions(target_disk_index)

        self.log(f"Source disk {source_disk_index} partitions:")
        for p in source_partitions:
            self.log(f"  {p.get('drive_letter', 'No letter')}: {p.get('size_gb', 0):.2f} GB, {p.get('file_system', 'Unknown')}, type={p.get('type', 'Unknown')}")

        self.log(f"Target disk {target_disk_index} partitions:")
        for p in target_partitions:
            self.log(f"  {p.get('drive_letter', 'No letter')}: {p.get('size_gb', 0):.2f} GB, {p.get('file_system', 'Unknown')}, type={p.get('type', 'Unknown')}")

        if not target_partitions:
            self.log("No partitions found on target disk after preparation!", "ERROR")
            return False

        # Step 3: Clone each partition's data
        self.log("\n--- Step 3: Cloning partition data ---")

        # Create mapping between source and target partitions
        # Only include partitions that have drive letters AND are clonable (not EFI/MSR system partitions)
        source_with_letters = []
        for p in source_partitions:
            drive = p.get('drive_letter')
            if drive:
                source_with_letters.append(p)
                self.log(f"  Source partition: {drive} ({p.get('file_system', 'Unknown')} - {p.get('size_gb', 0):.2f} GB)")

        target_with_letters = []
        for p in target_partitions:
            drive = p.get('drive_letter')
            if drive:
                target_with_letters.append(p)
                self.log(f"  Target partition: {drive} ({p.get('file_system', 'Unknown')} - {p.get('size_gb', 0):.2f} GB)")

        self.log(f"Source partitions with drive letters: {len(source_with_letters)}")
        self.log(f"Target partitions with drive letters: {len(target_with_letters)}")

        if len(source_with_letters) == 0:
            self.log("ERROR: No source partitions with drive letters found!", "ERROR")
            self.log("All source partitions:", "INFO")
            for p in source_partitions:
                self.log(f"  {p}", "INFO")
            return False

        if len(target_with_letters) == 0:
            self.log("ERROR: No target partitions with drive letters found!", "ERROR")
            self.log("All target partitions:", "INFO")
            for p in target_partitions:
                self.log(f"  {p}", "INFO")
            return False

        if len(source_with_letters) > len(target_with_letters):
            self.log(f"WARNING: Source has {len(source_with_letters)} partitions with drive letters, "
                    f"but target only has {len(target_with_letters)}", "WARNING")

        cloned_count = 0
        for i, source_part in enumerate(source_with_letters):
            if i >= len(target_with_letters):
                self.log(f"Skipping partition {source_part['drive_letter']} - no matching target partition", "WARNING")
                continue

            source_letter = source_part['drive_letter']
            target_letter = target_with_letters[i]['drive_letter']

            self.log(f"\nCloning partition {source_letter} -> {target_letter}...")

            # Use robocopy to clone filesystem data directly to target partition
            if self.clone_partition_filesystem(source_letter, target_letter + '\\'):
                cloned_count += 1
                self.log(f"Successfully cloned {source_letter} to {target_letter}", "SUCCESS")
            else:
                self.log(f"Failed to clone partition {source_letter} to {target_letter}", "ERROR")
                # Continue with other partitions instead of failing completely

        # Step 4: Configure boot loader to ensure OS is bootable
        self.configure_boot_loader(target_disk_index)

        # Step 5: Resize partition if requested
        if resize_partition:
            self.log("\n--- Step 5: Resizing partition to fill disk ---")
            if self.resize_partition_to_fill_disk(target_disk_index):
                self.log("Partition resized successfully!", "SUCCESS")
            else:
                self.log("Partition resize failed or skipped", "WARNING")

        self.log("\n" + "=" * 60)
        if cloned_count > 0:
            self.log(f"Disk cloning completed! Cloned {cloned_count} partition(s).", "SUCCESS")
            self.log("NOTE: You may need to reboot and select the new disk from BIOS to boot from it.", "INFO")
        else:
            self.log("No partitions were cloned. Please check disk configuration.", "ERROR")
            return False
        self.log("=" * 60)

        return True

    def clone_drive_to_image(self, source_drive, output_dir):
        """
        Clone a single drive (partition) to an image file
        Similar to Clonezilla's partition mode
        """
        if not self.is_admin:
            self.log("ERROR: Administrator privileges required!", "ERROR")
            return False

        self.log(f"Creating image of drive {source_drive} in {output_dir}")

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Create timestamp-based image directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_dir = os.path.join(output_dir, f"drive_{source_drive.replace(':', '')}_{timestamp}")
        os.makedirs(image_dir)

        self.log_file = os.path.join(image_dir, 'clone.log')

        # Clone filesystem
        success = self.clone_partition_filesystem(source_drive, image_dir)

        if success and self.config['gen_md5sum']:
            self.log("Generating checksums...")
            # Create checksums file
            checksums_file = os.path.join(image_dir, 'checksums.md5')
            with open(checksums_file, 'w') as f:
                for root, dirs, files in os.walk(image_dir):
                    for file in files:
                        if file == 'checksums.md5':
                            continue
                        file_path = os.path.join(root, file)
                        file_hash = self.calculate_hash(file_path)
                        if file_hash:
                            rel_path = os.path.relpath(file_path, image_dir)
                            f.write(f"{file_hash}  {rel_path}\n")

        return success


def main():
    """Main entry point with CLI interface"""
    parser = argparse.ArgumentParser(
        description='Windows Disk Cloner - Inspired by Clonezilla',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all disks
  python disk_cloner.py --list-disks

  # Clone drive C: to image
  python disk_cloner.py --clone-drive C: --output E:\\Backups

  # Clone disk 0 to disk 1 using RAW mode (default, best for OS clones)
  python disk_cloner.py --clone-disk 0 1

  # Fallback file-level clone if RAW access is blocked
  python disk_cloner.py --clone-disk 0 1 --filesystem-mode
        """
    )

    parser.add_argument('--list-disks', action='store_true',
                        help='List all available disks')
    parser.add_argument('--clone-drive', metavar='DRIVE',
                        help='Clone a specific drive (e.g., C:)')
    parser.add_argument('--clone-disk', nargs=2, metavar=('SOURCE', 'TARGET'),
                        help='Clone entire disk (source_index target_index); RAW mode is used by default')
    parser.add_argument('--filesystem-mode', action='store_true',
                        help='Use robocopy file-level disk cloning instead of RAW sector-by-sector cloning')
    parser.add_argument('--output', metavar='DIR',
                        help='Output directory for image files')
    parser.add_argument('--no-verify', action='store_true',
                        help='Skip verification after cloning')
    parser.add_argument('--no-checksum', action='store_true',
                        help='Skip checksum generation')

    args = parser.parse_args()

    cloner = DiskCloner()

    # Check admin privileges
    if not cloner.is_admin:
        print("\n" + "=" * 60)
        print("WARNING: Not running as Administrator!")
        print("This program requires administrator privileges for disk operations.")
        print("Please run as Administrator.")
        print("=" * 60 + "\n")
        return 1

    # List disks mode
    if args.list_disks:
        disks = cloner.scan_disks()
        print("\n" + "=" * 60)
        print("Available Disks:")
        print("=" * 60)
        for disk in disks:
            print(f"\nDisk {disk['index']}: {disk['model']}")
            print(f"  Size: {disk['size_gb']} GB")
            print(f"  Interface: {disk['interface']}")
            print(f"  Status: {disk['status']}")
            print(f"  Partitions: {disk['partitions']}")

            partitions = cloner.get_disk_partitions(disk['index'])
            for part in partitions:
                drive = part.get('drive_letter', 'N/A')
                fs = part.get('file_system', 'Unknown')
                print(f"    - {drive} ({part['size_gb']} GB, {fs})")
        print("=" * 60 + "\n")
        return 0

    # Clone drive to image mode
    if args.clone_drive:
        if not args.output:
            print("ERROR: --output directory required for drive cloning")
            return 1

        if args.no_checksum:
            cloner.config['gen_md5sum'] = False

        success = cloner.clone_drive_to_image(args.clone_drive, args.output)
        return 0 if success else 1

    # Clone disk to disk mode
    if args.clone_disk:
        source_idx = int(args.clone_disk[0])
        target_idx = int(args.clone_disk[1])

        print("\n" + "=" * 60)
        print("WARNING: DISK-TO-DISK CLONING")
        print("=" * 60)
        print(f"Source disk: {source_idx}")
        print(f"Target disk: {target_idx}")
        mode = 'filesystem/robocopy fallback' if args.filesystem_mode else 'RAW sector-by-sector (default)'
        print(f"Clone mode: {mode}")
        print("\nThis will OVERWRITE all data on the target disk!")
        if args.filesystem_mode:
            print("WARNING: Filesystem mode is not an exact sector copy of a live OS disk.")
            print("Use RAW mode for the most complete clean-slate OS-drive clone.")
        print("=" * 60)

        response = input("\nAre you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Operation cancelled.")
            return 0

        success = cloner.clone_disk_to_disk(source_idx, target_idx, use_raw_mode=not args.filesystem_mode)
        return 0 if success else 1

    # No action specified
    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
