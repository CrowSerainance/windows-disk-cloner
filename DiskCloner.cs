/*
 * Windows Disk Cloner - C# Implementation
 * Inspired by Clonezilla methodology using Windows Management Instrumentation (WMI)
 *
 * Author: Custom Build
 * License: GPL
 */

using System;
using System.IO;
using System.Management;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Diagnostics;
using System.Linq;
using System.Text.Json;

namespace WindowsDiskCloner
{
    /// <summary>
    /// Represents information about a physical disk
    /// </summary>
    public class DiskInfo
    {
        public int Index { get; set; }
        public string DeviceID { get; set; }
        public string Model { get; set; }
        public long Size { get; set; }
        public double SizeGB => Size / (1024.0 * 1024.0 * 1024.0);
        public string InterfaceType { get; set; }
        public int Partitions { get; set; }
        public string Status { get; set; }
        public List<PartitionInfo> PartitionList { get; set; } = new List<PartitionInfo>();
    }

    /// <summary>
    /// Represents information about a partition
    /// </summary>
    public class PartitionInfo
    {
        public int Index { get; set; }
        public string DeviceID { get; set; }
        public long Size { get; set; }
        public double SizeGB => Size / (1024.0 * 1024.0 * 1024.0);
        public string Type { get; set; }
        public bool Bootable { get; set; }
        public bool Primary { get; set; }
        public string DriveLetter { get; set; }
        public string FileSystem { get; set; }
        public string VolumeLabel { get; set; }
        public long? FreeSpace { get; set; }
    }

    /// <summary>
    /// Main disk cloning class inspired by Clonezilla's architecture
    /// </summary>
    public class DiskCloner
    {
        private readonly string logFile;
        private readonly Dictionary<string, bool> config;

        public DiskCloner()
        {
            config = new Dictionary<string, bool>
            {
                { "CheckMD5Sum", true },
                { "GenerateMD5Sum", true },
                { "VerifyAfterClone", true },
                { "SkipFreeSpace", true },
                { "RescueMode", false }
            };
        }

        /// <summary>
        /// Check if running with administrator privileges
        /// </summary>
        public static bool IsAdministrator()
        {
            var identity = System.Security.Principal.WindowsIdentity.GetCurrent();
            var principal = new System.Security.Principal.WindowsPrincipal(identity);
            return principal.IsInRole(System.Security.Principal.WindowsBuiltInRole.Administrator);
        }

        /// <summary>
        /// Log a message to console and file
        /// </summary>
        public void Log(string message, string level = "INFO")
        {
            string timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
            string logMessage = $"[{timestamp}] [{level}] {message}";

            Console.WriteLine(logMessage);

            if (!string.IsNullOrEmpty(logFile))
            {
                try
                {
                    File.AppendAllText(logFile, logMessage + Environment.NewLine);
                }
                catch { }
            }
        }

        /// <summary>
        /// Scan and list all physical disks (similar to ocs-scan-disk)
        /// </summary>
        public List<DiskInfo> ScanDisks()
        {
            Log("Scanning physical disks...");
            var disks = new List<DiskInfo>();

            try
            {
                using (var searcher = new ManagementObjectSearcher("SELECT * FROM Win32_DiskDrive"))
                {
                    foreach (ManagementObject disk in searcher.Get())
                    {
                        var diskInfo = new DiskInfo
                        {
                            Index = Convert.ToInt32(disk["Index"]),
                            DeviceID = disk["DeviceID"]?.ToString(),
                            Model = disk["Model"]?.ToString(),
                            Size = disk["Size"] != null ? Convert.ToInt64(disk["Size"]) : 0,
                            InterfaceType = disk["InterfaceType"]?.ToString(),
                            Partitions = disk["Partitions"] != null ? Convert.ToInt32(disk["Partitions"]) : 0,
                            Status = disk["Status"]?.ToString()
                        };

                        disks.Add(diskInfo);
                        Log($"Found disk {diskInfo.Index}: {diskInfo.Model} ({diskInfo.SizeGB:F2} GB)");
                    }
                }
            }
            catch (Exception ex)
            {
                Log($"Error scanning disks: {ex.Message}", "ERROR");
            }

            return disks;
        }

        /// <summary>
        /// Get all partitions for a specific disk
        /// </summary>
        public List<PartitionInfo> GetDiskPartitions(int diskIndex)
        {
            Log($"Getting partitions for disk {diskIndex}...");
            var partitions = new List<PartitionInfo>();

            try
            {
                using (var searcher = new ManagementObjectSearcher("SELECT * FROM Win32_DiskPartition"))
                {
                    foreach (ManagementObject partition in searcher.Get())
                    {
                        int partDiskIndex = Convert.ToInt32(partition["DiskIndex"]);

                        if (partDiskIndex == diskIndex)
                        {
                            var partInfo = new PartitionInfo
                            {
                                Index = Convert.ToInt32(partition["Index"]),
                                DeviceID = partition["DeviceID"]?.ToString(),
                                Size = partition["Size"] != null ? Convert.ToInt64(partition["Size"]) : 0,
                                Type = partition["Type"]?.ToString(),
                                Bootable = partition["Bootable"] != null && Convert.ToBoolean(partition["Bootable"]),
                                Primary = partition["PrimaryPartition"] != null && Convert.ToBoolean(partition["PrimaryPartition"])
                            };

                            // Get associated logical disk (drive letter)
                            try
                            {
                                using (var logicalDiskSearcher = new ManagementObjectSearcher(
                                    $"ASSOCIATORS OF {{Win32_DiskPartition.DeviceID='{partInfo.DeviceID}'}} " +
                                    "WHERE AssocClass = Win32_LogicalDiskToPartition"))
                                {
                                    foreach (ManagementObject logicalDisk in logicalDiskSearcher.Get())
                                    {
                                        partInfo.DriveLetter = logicalDisk["DeviceID"]?.ToString();
                                        partInfo.FileSystem = logicalDisk["FileSystem"]?.ToString();
                                        partInfo.VolumeLabel = logicalDisk["VolumeName"]?.ToString();
                                        partInfo.FreeSpace = logicalDisk["FreeSpace"] != null ?
                                            Convert.ToInt64(logicalDisk["FreeSpace"]) : (long?)null;
                                    }
                                }
                            }
                            catch { }

                            partitions.Add(partInfo);
                            Log($"  Partition {partInfo.Index}: {partInfo.DriveLetter ?? "N/A"} " +
                                $"({partInfo.SizeGB:F2} GB, {partInfo.FileSystem ?? "Unknown"})");
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Log($"Error getting partitions: {ex.Message}", "ERROR");
            }

            return partitions;
        }

        /// <summary>
        /// Calculate MD5 hash of a file
        /// </summary>
        public string CalculateMD5(string filePath)
        {
            try
            {
                using (var md5 = MD5.Create())
                using (var stream = File.OpenRead(filePath))
                {
                    byte[] hash = md5.ComputeHash(stream);
                    return BitConverter.ToString(hash).Replace("-", "").ToLowerInvariant();
                }
            }
            catch (Exception ex)
            {
                Log($"Error calculating MD5: {ex.Message}", "ERROR");
                return null;
            }
        }

        /// <summary>
        /// Clone a partition's filesystem using robocopy
        /// Similar to Clonezilla's partclone but using Windows tools
        /// </summary>
        public bool ClonePartitionFilesystem(string sourceDrive, string targetPath)
        {
            Log($"Cloning filesystem from {sourceDrive} to {targetPath}...");

            // Ensure source drive format
            if (!sourceDrive.EndsWith(":"))
            {
                sourceDrive = sourceDrive.TrimEnd('\\');
            }
            string sourcePath = sourceDrive + "\\";

            if (!Directory.Exists(targetPath))
            {
                Directory.CreateDirectory(targetPath);
            }

            // Robocopy flags for reliable disk cloning:
            // /MIR - Mirror mode
            // /ZB - Restartable + Backup mode for locked files
            // /SEC - Copy NTFS security
            // /SECFIX - Fix security on existing files
            // /TIMFIX - Fix timestamps
            // /R:1 - Retry once
            // /W:1 - Wait 1 sec
            // /MT:16 - 16 threads
            // /XJ - Exclude junctions
            // /XD - Exclude system directories
            // /XF - Exclude system files
            var arguments = new List<string>
            {
                $"\"{sourcePath}\"",
                $"\"{targetPath}\"",
                "/MIR",
                "/ZB",
                "/SEC",
                "/SECFIX",
                "/TIMFIX",
                "/R:1",
                "/W:1",
                "/MT:16",
                "/XJ",
                "/XD", "\"System Volume Information\"", "\"$RECYCLE.BIN\"", "\"Recovery\"",
                "/XF", "pagefile.sys", "hiberfil.sys", "swapfile.sys",
                "/NP",
                "/NDL",
                "/NC",
                "/NS",
                "/NJH",
                "/NJS"
            };

            try
            {
                Log($"Running robocopy with backup privileges...");
                Log($"Source: {sourcePath}");
                Log($"Target: {targetPath}");

                var processInfo = new ProcessStartInfo
                {
                    FileName = "robocopy.exe",
                    Arguments = string.Join(" ", arguments),
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true
                };

                using (var process = Process.Start(processInfo))
                {
                    // Set timeout for large disks
                    bool completed = process.WaitForExit(7200000); // 2 hours

                    if (!completed)
                    {
                        process.Kill();
                        Log("Cloning timed out after 2 hours!", "ERROR");
                        return false;
                    }

                    // Robocopy exit codes:
                    // 0-7 = success, 8 = some files skipped, 16+ = fatal error
                    if (process.ExitCode < 8)
                    {
                        Log($"Successfully cloned {sourceDrive} (exit code: {process.ExitCode})", "SUCCESS");
                        return true;
                    }
                    else if (process.ExitCode == 8)
                    {
                        Log($"Cloning completed with some skipped files (exit code: 8)", "WARNING");
                        Log("This is normal for locked system files", "WARNING");
                        return true;
                    }
                    else
                    {
                        string error = process.StandardError.ReadToEnd();
                        string output = process.StandardOutput.ReadToEnd();
                        Log($"Cloning failed with exit code {process.ExitCode}", "ERROR");
                        if (!string.IsNullOrEmpty(error))
                            Log($"Error: {error}", "ERROR");
                        return false;
                    }
                }
            }
            catch (Exception ex)
            {
                Log($"Error during cloning: {ex.Message}", "ERROR");
                return false;
            }
        }

        /// <summary>
        /// Save disk metadata to JSON file (similar to Clonezilla's metadata)
        /// </summary>
        public bool SaveDiskMetadata(int diskIndex, string outputDir)
        {
            Log($"Saving metadata for disk {diskIndex}...");

            var metadata = new Dictionary<string, object>
            {
                { "Timestamp", DateTime.Now },
                { "DiskIndex", diskIndex }
            };

            // Get disk info
            var disks = ScanDisks();
            var targetDisk = disks.FirstOrDefault(d => d.Index == diskIndex);
            if (targetDisk != null)
            {
                metadata["Disk"] = new
                {
                    targetDisk.Model,
                    targetDisk.Size,
                    targetDisk.InterfaceType,
                    targetDisk.DeviceID
                };
            }

            // Get partition info
            metadata["Partitions"] = GetDiskPartitions(diskIndex);

            // Save to JSON
            string metadataFile = Path.Combine(outputDir, $"disk_{diskIndex}_metadata.json");

            try
            {
                string json = JsonSerializer.Serialize(metadata, new JsonSerializerOptions
                {
                    WriteIndented = true
                });
                File.WriteAllText(metadataFile, json);
                Log($"Metadata saved to {metadataFile}", "SUCCESS");
                return true;
            }
            catch (Exception ex)
            {
                Log($"Error saving metadata: {ex.Message}", "ERROR");
                return false;
            }
        }

        /// <summary>
        /// Verify target disk is not the system disk
        /// </summary>
        public bool VerifyDiskWritable(int diskIndex)
        {
            Log($"Verifying disk {diskIndex} is safe to write to...");

            try
            {
                string systemDrive = Environment.GetEnvironmentVariable("SystemDrive") ?? "C:";
                var partitions = GetDiskPartitions(diskIndex);

                foreach (var partition in partitions)
                {
                    if (partition.DriveLetter == systemDrive)
                    {
                        Log($"WARNING: Disk {diskIndex} contains system drive {systemDrive}!", "WARNING");
                        return false;
                    }
                }
            }
            catch (Exception ex)
            {
                Log($"Error verifying disk: {ex.Message}", "ERROR");
                return false;
            }

            return true;
        }

        private bool _efiPartitionCreated = false;

        /// <summary>
        /// Prepare target disk with partition structure matching source disk
        /// </summary>
        public bool PrepareTargetDisk(int targetDiskIndex, int sourceDiskIndex)
        {
            Log($"Preparing target disk {targetDiskIndex}...");

            var sourcePartitions = GetDiskPartitions(sourceDiskIndex);

            if (sourcePartitions.Count == 0)
            {
                Log("No source partitions to replicate!", "ERROR");
                return false;
            }

            // Check if source is GPT or MBR
            // GPT disks have specific partition types that MBR disks don't have:
            //   - EFI System Partition (ESP) - FAT32, typically 100-550MB
            //   - Microsoft Reserved Partition (MSR) - no filesystem, 16-128MB
            //   - Recovery partitions with GPT-specific attributes
            bool isGpt = false;
            var gptIndicators = new List<string>();
            
            foreach (var p in sourcePartitions)
            {
                string pType = (p.Type ?? "").ToUpper();
                string pFs = (p.FileSystem ?? "").ToUpper();
                long pSizeMB = p.Size / (1024 * 1024);
                string pDrive = p.DriveLetter;

                // Check 1: Explicit EFI or GPT in partition type
                if (pType.Contains("EFI") || pType.Contains("GPT"))
                {
                    isGpt = true;
                    gptIndicators.Add($"EFI/GPT partition type detected: {pType}");
                    break;
                }
                
                // Check 2: MSR (Microsoft Reserved) partition - only exists on GPT disks
                if (pType.Contains("MSR") || pType.Contains("RESERVED"))
                {
                    isGpt = true;
                    gptIndicators.Add($"MSR partition detected: {pType}");
                    break;
                }
                
                // Check 3: Small FAT32 partition without drive letter (likely EFI System Partition)
                if (pFs == "FAT32" && pSizeMB > 50 && pSizeMB < 1000 && string.IsNullOrEmpty(pDrive))
                {
                    isGpt = true;
                    gptIndicators.Add($"Small FAT32 system partition ({pSizeMB}MB, no drive letter)");
                    break;
                }
                
                // Check 4: Small partition without drive letter that's not recovery
                if (pSizeMB > 0 && pSizeMB < 600 && string.IsNullOrEmpty(pDrive) && !pType.Contains("RECOVERY"))
                {
                    isGpt = true;
                    gptIndicators.Add($"Small system partition ({pSizeMB}MB, no drive letter, type: {pType})");
                    break;
                }
            }

            // Log detection results
            if (isGpt)
            {
                Log($"Detected disk type: GPT");
                foreach (var indicator in gptIndicators)
                {
                    Log($"  Reason: {indicator}");
                }
            }
            else
            {
                Log($"Detected disk type: MBR (no GPT indicators found)");
            }

            // Create diskpart script
            var diskpartScript = $@"select disk {targetDiskIndex}
clean
{(isGpt ? "convert gpt" : "convert mbr")}
";

            _efiPartitionCreated = false;

            for (int i = 0; i < sourcePartitions.Count; i++)
            {
                var partition = sourcePartitions[i];
                long sizeMB = partition.Size / (1024 * 1024);
                string partType = (partition.Type ?? "").ToUpper();

                // Skip tiny partitions
                if (sizeMB < 1)
                {
                    Log($"Skipping partition {i} with size < 1MB", "WARNING");
                    continue;
                }

                // Detect EFI partition: explicit type, or small partition without drive letter on GPT disk
                bool isEfiPartition = (
                    partType.Contains("EFI") ||
                    partType.Contains("SYSTEM") ||
                    (isGpt && sizeMB > 0 && sizeMB < 600 && string.IsNullOrEmpty(partition.DriveLetter) && !partType.Contains("RECOVERY"))
                );

                if (isEfiPartition)
                {
                    // EFI System Partition - minimum 100MB, typically 260MB
                    // Windows recommends 100MB minimum, but 260MB is safer for updates
                    long efiSize = Math.Max(sizeMB, 100);
                    diskpartScript += $@"create partition efi size={efiSize}
format fs=fat32 quick label=""EFI""
assign
";
                    _efiPartitionCreated = true;
                    Log($"  Creating EFI partition ({efiSize} MB)");
                }
                else if (partType.Contains("MSR") || partType.Contains("RESERVED"))
                {
                    // Microsoft Reserved Partition - typically 16MB on MBR, 128MB on GPT
                    // This partition has no filesystem and no drive letter
                    long msrSize = Math.Max(sizeMB, 16);
                    diskpartScript += $@"create partition msr size={msrSize}
";
                    Log($"  Creating MSR partition ({msrSize} MB)");
                }
                else if (partType.Contains("RECOVERY"))
                {
                    // Recovery partition with GPT-specific attributes
                    diskpartScript += $@"create partition primary size={sizeMB}
format fs=ntfs quick label=""Recovery""
set id=""de94bba4-06d1-4d40-a16a-bfd50179d6ac""
gpt attributes=0x8000000000000001
";
                    Log($"  Creating Recovery partition ({sizeMB} MB)");
                }
                else
                {
                    // Regular data partition (Windows, Data, etc.)
                    string fs = (partition.FileSystem ?? "NTFS").ToUpper();
                    string label = partition.VolumeLabel ?? "Data";

                    // Sanitize label: max 32 chars, only alphanumeric and basic punctuation
                    label = new string(label.Take(32).Where(c =>
                        char.IsLetterOrDigit(c) || c == ' ' || c == '-' || c == '_').ToArray());
                    if (string.IsNullOrEmpty(label)) label = "Data";

                    // Use remaining space for the last partition to maximize disk usage
                    bool isLast = (i == sourcePartitions.Count - 1);

                    if (isLast)
                    {
                        // No size specified = use all remaining space
                        diskpartScript += $@"create partition primary
format fs={fs} quick label=""{label}""
assign
";
                        Log($"  Creating primary partition (remaining space, {fs}, '{label}')");
                    }
                    else
                    {
                        diskpartScript += $@"create partition primary size={sizeMB}
format fs={fs} quick label=""{label}""
assign
";
                        Log($"  Creating primary partition ({sizeMB} MB, {fs}, '{label}')");
                    }
                }
            }

            // Write and execute diskpart script
            string scriptPath = Path.Combine(Path.GetTempPath(), "diskpart_clone.txt");
            try
            {
                // Log the script for debugging
                Log("Diskpart script:", "INFO");
                foreach (var line in diskpartScript.Split('\n'))
                {
                    if (!string.IsNullOrWhiteSpace(line))
                        Log($"  {line.Trim()}", "INFO");
                }

                File.WriteAllText(scriptPath, diskpartScript);

                Log("Running diskpart to prepare target disk...");
                var processInfo = new ProcessStartInfo
                {
                    FileName = "diskpart",
                    Arguments = $"/s \"{scriptPath}\"",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true
                };

                using (var process = Process.Start(processInfo))
                {
                    // 5 minute timeout
                    bool completed = process.WaitForExit(300000);

                    if (!completed)
                    {
                        process.Kill();
                        Log("Diskpart timed out!", "ERROR");
                        return false;
                    }

                    string output = process.StandardOutput.ReadToEnd();
                    string error = process.StandardError.ReadToEnd();

                    if (process.ExitCode != 0)
                    {
                        Log($"Diskpart failed with code {process.ExitCode}", "ERROR");
                        if (!string.IsNullOrEmpty(error))
                            Log($"Error: {error}", "ERROR");
                        if (!string.IsNullOrEmpty(output))
                            Log($"Output: {output}", "ERROR");
                        return false;
                    }

                    // Check for error messages in output
                    if (output.ToLower().Contains("error") || output.ToLower().Contains("failed"))
                    {
                        Log("Diskpart reported errors:", "ERROR");
                        Log(output, "ERROR");
                        return false;
                    }
                }

                Log("Target disk prepared successfully", "SUCCESS");

                // Wait for Windows to recognize partitions
                Log("Waiting for Windows to assign drive letters...");
                System.Threading.Thread.Sleep(3000);

                return true;
            }
            catch (Exception ex)
            {
                Log($"Error preparing target disk: {ex.Message}", "ERROR");
                return false;
            }
            finally
            {
                try
                {
                    if (File.Exists(scriptPath))
                    {
                        File.Delete(scriptPath);
                    }
                }
                catch { }
            }
        }

        /// <summary>
        /// Clone entire disk to another disk
        /// </summary>
        public bool CloneDiskToDisk(int sourceDiskIndex, int targetDiskIndex)
        {
            if (!IsAdministrator())
            {
                Log("ERROR: Administrator privileges required for disk cloning!", "ERROR");
                return false;
            }

            Log(new string('=', 60));
            Log($"Starting disk-to-disk clone: Disk {sourceDiskIndex} -> Disk {targetDiskIndex}");
            Log(new string('=', 60));

            // Validate source and target are different
            if (sourceDiskIndex == targetDiskIndex)
            {
                Log("ERROR: Source and target disk cannot be the same!", "ERROR");
                return false;
            }

            // Verify target disk is safe
            if (!VerifyDiskWritable(targetDiskIndex))
            {
                Log("Target disk verification failed!", "ERROR");
                return false;
            }

            // Get disk info
            var disks = ScanDisks();
            var sourceDisk = disks.FirstOrDefault(d => d.Index == sourceDiskIndex);
            var targetDisk = disks.FirstOrDefault(d => d.Index == targetDiskIndex);

            if (sourceDisk == null)
            {
                Log($"Source disk {sourceDiskIndex} not found!", "ERROR");
                return false;
            }
            if (targetDisk == null)
            {
                Log($"Target disk {targetDiskIndex} not found!", "ERROR");
                return false;
            }

            // Check size
            if (targetDisk.Size < sourceDisk.Size)
            {
                Log($"WARNING: Target disk ({targetDisk.SizeGB:F2} GB) is smaller than source ({sourceDisk.SizeGB:F2} GB)", "WARNING");
                Log("Cloning will proceed but may fail if data exceeds target capacity", "WARNING");
            }

            // Get source partitions
            var sourcePartitions = GetDiskPartitions(sourceDiskIndex);

            if (sourcePartitions.Count == 0)
            {
                Log("No partitions found on source disk!", "ERROR");
                return false;
            }

            Log($"Found {sourcePartitions.Count} partitions to clone");

            // Step 1: Prepare target disk
            Log("\n--- Step 1: Preparing target disk ---");
            if (!PrepareTargetDisk(targetDiskIndex, sourceDiskIndex))
            {
                Log("Failed to prepare target disk!", "ERROR");
                return false;
            }

            // Wait for Windows to assign drive letters
            System.Threading.Thread.Sleep(2000);

            // Step 2: Get partition drive letters (re-fetch both after diskpart changes)
            Log("\n--- Step 2: Mapping partitions ---");

            // Re-fetch source partitions in case drive letters changed during diskpart
            sourcePartitions = GetDiskPartitions(sourceDiskIndex);
            var targetPartitions = GetDiskPartitions(targetDiskIndex);

            Log($"Source disk {sourceDiskIndex} partitions:");
            foreach (var p in sourcePartitions)
            {
                Log($"  {p.DriveLetter ?? "No letter"}: {p.SizeGB:F2} GB, {p.FileSystem ?? "Unknown"}, type={p.Type ?? "Unknown"}");
            }

            Log($"Target disk {targetDiskIndex} partitions:");
            foreach (var p in targetPartitions)
            {
                Log($"  {p.DriveLetter ?? "No letter"}: {p.SizeGB:F2} GB, {p.FileSystem ?? "Unknown"}, type={p.Type ?? "Unknown"}");
            }

            if (targetPartitions.Count == 0)
            {
                Log("No partitions found on target disk after preparation!", "ERROR");
                return false;
            }

            // Step 3: Clone each partition
            Log("\n--- Step 3: Cloning partition data ---");

            var sourceWithLetters = new List<PartitionInfo>();
            foreach (var p in sourcePartitions)
            {
                if (!string.IsNullOrEmpty(p.DriveLetter))
                {
                    sourceWithLetters.Add(p);
                    Log($"  Source partition: {p.DriveLetter} ({p.FileSystem ?? "Unknown"} - {p.SizeGB:F2} GB)");
                }
            }

            var targetWithLetters = new List<PartitionInfo>();
            foreach (var p in targetPartitions)
            {
                if (!string.IsNullOrEmpty(p.DriveLetter))
                {
                    targetWithLetters.Add(p);
                    Log($"  Target partition: {p.DriveLetter} ({p.FileSystem ?? "Unknown"} - {p.SizeGB:F2} GB)");
                }
            }

            Log($"Source partitions with drive letters: {sourceWithLetters.Count}");
            Log($"Target partitions with drive letters: {targetWithLetters.Count}");

            if (sourceWithLetters.Count == 0)
            {
                Log("ERROR: No source partitions with drive letters found!", "ERROR");
                Log("All source partitions:", "INFO");
                foreach (var p in sourcePartitions)
                    Log($"  Drive={p.DriveLetter ?? "None"}, Size={p.SizeGB:F2}GB, FS={p.FileSystem ?? "Unknown"}", "INFO");
                return false;
            }

            if (targetWithLetters.Count == 0)
            {
                Log("ERROR: No target partitions with drive letters found!", "ERROR");
                Log("All target partitions:", "INFO");
                foreach (var p in targetPartitions)
                    Log($"  Drive={p.DriveLetter ?? "None"}, Size={p.SizeGB:F2}GB, FS={p.FileSystem ?? "Unknown"}", "INFO");
                return false;
            }

            if (sourceWithLetters.Count > targetWithLetters.Count)
            {
                Log($"WARNING: Source has {sourceWithLetters.Count} partitions with drive letters, " +
                    $"but target only has {targetWithLetters.Count}", "WARNING");
            }

            int clonedCount = 0;
            for (int i = 0; i < sourceWithLetters.Count; i++)
            {
                if (i >= targetWithLetters.Count)
                {
                    Log($"Skipping partition {sourceWithLetters[i].DriveLetter} - no matching target partition", "WARNING");
                    continue;
                }

                string sourceLetter = sourceWithLetters[i].DriveLetter;
                string targetLetter = targetWithLetters[i].DriveLetter;

                Log($"\nCloning partition {sourceLetter} -> {targetLetter}...");

                if (ClonePartitionFilesystem(sourceLetter, targetLetter + "\\"))
                {
                    clonedCount++;
                    Log($"Successfully cloned {sourceLetter} to {targetLetter}", "SUCCESS");
                }
                else
                {
                    Log($"Failed to clone partition {sourceLetter} to {targetLetter}", "ERROR");
                }
            }

            // Step 4: Configure boot
            Log("\n--- Step 4: Finalizing boot configuration ---");
            try
            {
                // Find the Windows partition and EFI partition on the target disk
                string windowsPartition = null;
                string windowsPath = null;
                string efiPartition = null;
                bool efiDetectedByType = false; // Track if we found EFI by explicit type

                // Log all target partitions for debugging
                Log("Scanning target partitions for boot configuration:");
                foreach (var targetPart in targetPartitions)
                {
                    string drive = targetPart.DriveLetter;
                    double partSizeGB = targetPart.SizeGB;
                    string fs = (targetPart.FileSystem ?? "").ToUpper();
                    string partType = (targetPart.Type ?? "").ToUpper();
                    Log($"  {drive ?? "No letter"}: {partSizeGB:F2} GB, {(string.IsNullOrEmpty(fs) ? "Unknown FS" : fs)}, type={partType}");
                }

                foreach (var targetPart in targetPartitions)
                {
                    string drive = targetPart.DriveLetter;
                    if (string.IsNullOrEmpty(drive))
                        continue;

                    double partSizeGB = targetPart.SizeGB;
                    string fs = (targetPart.FileSystem ?? "").ToUpper();
                    string partType = (targetPart.Type ?? "").ToUpper();

                    // Check for EFI partition:
                    // 1. Explicit EFI type in partition info
                    // 2. Small FAT32 partition (< 1GB) - common EFI characteristics
                    // EFI partitions are small FAT32 partitions, NOT NTFS
                    if (partType.Contains("EFI") || partType.Contains("SYSTEM"))
                    {
                        efiPartition = drive;
                        efiDetectedByType = true;
                        Log($"Found EFI partition on {drive} (type: {partType}, {partSizeGB:F2} GB)");
                        continue; // Don't check this partition for Windows
                    }
                    else if (fs == "FAT32" && partSizeGB < 1 && efiPartition == null)
                    {
                        // Likely EFI based on characteristics - must be FAT32 and small
                        efiPartition = drive;
                        Log($"Found likely EFI partition on {drive} ({partSizeGB:F2} GB, {fs})");
                        continue; // Don't check this partition for Windows
                    }

                    // Check for Windows installation (typically NTFS, has Windows\System32)
                    // Only check if this isn't already identified as EFI
                    if (drive != efiPartition)
                    {
                        string checkPath = Path.Combine(drive + "\\", "Windows", "System32");
                        if (Directory.Exists(checkPath) && windowsPartition == null)
                        {
                            windowsPartition = drive;
                            windowsPath = Path.Combine(drive + "\\", "Windows");
                            Log($"Found Windows installation on {drive} ({partSizeGB:F2} GB, {fs})");
                        }
                    }
                }

                if (windowsPath != null && Directory.Exists(windowsPath))
                {
                    // Determine boot mode and target partition
                    // We use UEFI mode if:
                    //   1. We created an EFI partition during disk preparation, OR
                    //   2. We detected an EFI partition by explicit type
                    bool useUefi = efiPartition != null && (_efiPartitionCreated || efiDetectedByType);

                    ProcessStartInfo processInfo;

                    if (useUefi)
                    {
                        // UEFI mode - target EFI partition
                        Log($"Configuring UEFI boot (EFI partition: {efiPartition})...");
                        processInfo = new ProcessStartInfo
                        {
                            FileName = "bcdboot",
                            Arguments = $"\"{windowsPath}\" /s {efiPartition} /f UEFI",
                            UseShellExecute = false,
                            RedirectStandardOutput = true,
                            RedirectStandardError = true,
                            CreateNoWindow = true
                        };
                    }
                    else
                    {
                        // BIOS/MBR mode or fallback - target Windows partition
                        // Using /f ALL creates boot files for both UEFI and BIOS
                        Log($"Configuring BIOS/legacy boot for {windowsPartition}...");
                        processInfo = new ProcessStartInfo
                        {
                            FileName = "bcdboot",
                            Arguments = $"\"{windowsPath}\" /s {windowsPartition} /f ALL",
                            UseShellExecute = false,
                            RedirectStandardOutput = true,
                            RedirectStandardError = true,
                            CreateNoWindow = true
                        };
                    }

                    using (var process = Process.Start(processInfo))
                    {
                        bool completed = process.WaitForExit(60000); // 1 minute timeout
                        if (!completed)
                        {
                            process.Kill();
                            Log("Boot configuration timed out", "WARNING");
                        }
                        else if (process.ExitCode == 0)
                        {
                            Log("Boot configuration updated successfully", "SUCCESS");
                        }
                        else
                        {
                            // bcdboot failed - provide helpful diagnostics
                            string error = process.StandardError.ReadToEnd()?.Trim() ?? "No error message";
                            Log($"Boot configuration warning: {error}", "WARNING");
                            Log("You may need to manually run:", "WARNING");
                            if (useUefi)
                            {
                                Log($"  bcdboot {windowsPath} /s {efiPartition} /f UEFI", "WARNING");
                            }
                            else
                            {
                                Log($"  bcdboot {windowsPath} /s {windowsPartition} /f ALL", "WARNING");
                            }
                        }
                    }
                }
                else
                {
                    Log("No Windows installation found - skipping boot configuration", "INFO");
                    Log("This is normal for data-only disk clones", "INFO");
                }
            }
            catch (Exception ex)
            {
                Log($"Boot configuration step skipped: {ex.Message}", "WARNING");
            }

            Log("\n" + new string('=', 60));
            if (clonedCount > 0)
            {
                Log($"Disk cloning completed! Cloned {clonedCount} partition(s).", "SUCCESS");
                Log("NOTE: You may need to reboot and select the new disk from BIOS to boot from it.", "INFO");
            }
            else
            {
                Log("No partitions were cloned. Please check disk configuration.", "ERROR");
                return false;
            }
            Log(new string('=', 60));

            return true;
        }

        /// <summary>
        /// Clone a drive to an image backup
        /// </summary>
        public bool CloneDriveToImage(string sourceDrive, string outputDir)
        {
            if (!IsAdministrator())
            {
                Log("ERROR: Administrator privileges required!", "ERROR");
                return false;
            }

            Log($"Creating image of drive {sourceDrive} in {outputDir}");

            if (!Directory.Exists(outputDir))
            {
                Directory.CreateDirectory(outputDir);
            }

            // Create timestamp-based image directory
            string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            string imageDir = Path.Combine(outputDir,
                $"drive_{sourceDrive.Replace(":", "")}_{timestamp}");
            Directory.CreateDirectory(imageDir);

            // Clone filesystem
            bool success = ClonePartitionFilesystem(sourceDrive, imageDir);

            // Generate checksums if requested
            if (success && config["GenerateMD5Sum"])
            {
                Log("Generating checksums...");
                string checksumsFile = Path.Combine(imageDir, "checksums.md5");

                try
                {
                    using (var writer = new StreamWriter(checksumsFile))
                    {
                        foreach (string file in Directory.GetFiles(imageDir, "*", SearchOption.AllDirectories))
                        {
                            if (Path.GetFileName(file) == "checksums.md5")
                                continue;

                            string hash = CalculateMD5(file);
                            if (hash != null)
                            {
                                string relativePath = Path.GetRelativePath(imageDir, file);
                                writer.WriteLine($"{hash}  {relativePath}");
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    Log($"Error generating checksums: {ex.Message}", "ERROR");
                }
            }

            return success;
        }
    }

    /// <summary>
    /// Main program entry point
    /// </summary>
    class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine("=" + new string('=', 59));
            Console.WriteLine("Windows Disk Cloner - Inspired by Clonezilla");
            Console.WriteLine("=" + new string('=', 59));
            Console.WriteLine();

            var cloner = new DiskCloner();

            // Check admin privileges
            if (!DiskCloner.IsAdministrator())
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("WARNING: Not running as Administrator!");
                Console.WriteLine("This program requires administrator privileges.");
                Console.WriteLine("Please run as Administrator.");
                Console.ResetColor();
                Console.WriteLine();
                Console.WriteLine("Press any key to exit...");
                Console.ReadKey();
                return;
            }

            // Simple menu
            while (true)
            {
                Console.WriteLine("\nChoose an option:");
                Console.WriteLine("1. List all disks");
                Console.WriteLine("2. Clone drive to image");
                Console.WriteLine("3. Clone disk to disk");
                Console.WriteLine("4. Exit");
                Console.Write("\nEnter choice: ");

                string choice = Console.ReadLine();

                switch (choice)
                {
                    case "1":
                        ListDisks(cloner);
                        break;

                    case "2":
                        CloneDriveToImage(cloner);
                        break;

                    case "3":
                        CloneDiskToDisk(cloner);
                        break;

                    case "4":
                        return;

                    default:
                        Console.WriteLine("Invalid choice!");
                        break;
                }
            }
        }

        static void ListDisks(DiskCloner cloner)
        {
            var disks = cloner.ScanDisks();

            Console.WriteLine("\n" + new string('=', 60));
            Console.WriteLine("Available Disks:");
            Console.WriteLine(new string('=', 60));

            foreach (var disk in disks)
            {
                Console.WriteLine($"\nDisk {disk.Index}: {disk.Model}");
                Console.WriteLine($"  Size: {disk.SizeGB:F2} GB");
                Console.WriteLine($"  Interface: {disk.InterfaceType}");
                Console.WriteLine($"  Status: {disk.Status}");
                Console.WriteLine($"  Partitions: {disk.Partitions}");

                var partitions = cloner.GetDiskPartitions(disk.Index);
                foreach (var part in partitions)
                {
                    string drive = part.DriveLetter ?? "N/A";
                    string fs = part.FileSystem ?? "Unknown";
                    Console.WriteLine($"    - {drive} ({part.SizeGB:F2} GB, {fs})");
                }
            }
            Console.WriteLine(new string('=', 60));
        }

        static void CloneDriveToImage(DiskCloner cloner)
        {
            Console.Write("\nEnter source drive letter (e.g., C:): ");
            string sourceDrive = Console.ReadLine()?.Trim();

            if (string.IsNullOrEmpty(sourceDrive))
            {
                Console.WriteLine("Invalid drive letter!");
                return;
            }

            Console.Write("Enter output directory (e.g., E:\\Backups): ");
            string outputDir = Console.ReadLine()?.Trim();

            if (string.IsNullOrEmpty(outputDir))
            {
                Console.WriteLine("Invalid output directory!");
                return;
            }

            Console.WriteLine($"\nReady to clone {sourceDrive} to {outputDir}");
            Console.Write("Continue? (yes/no): ");
            string confirm = Console.ReadLine()?.Trim().ToLower();

            if (confirm != "yes")
            {
                Console.WriteLine("Operation cancelled.");
                return;
            }

            bool success = cloner.CloneDriveToImage(sourceDrive, outputDir);

            if (success)
            {
                Console.ForegroundColor = ConsoleColor.Green;
                Console.WriteLine("\nCloning completed successfully!");
                Console.ResetColor();
            }
            else
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("\nCloning failed!");
                Console.ResetColor();
            }
        }

        static void CloneDiskToDisk(DiskCloner cloner)
        {
            // First list disks
            ListDisks(cloner);

            Console.Write("\nEnter source disk number (e.g., 0): ");
            string sourceInput = Console.ReadLine()?.Trim();

            if (string.IsNullOrEmpty(sourceInput) || !int.TryParse(sourceInput, out int sourceDiskIndex))
            {
                Console.WriteLine("Invalid disk number!");
                return;
            }

            Console.Write("Enter target disk number (e.g., 1): ");
            string targetInput = Console.ReadLine()?.Trim();

            if (string.IsNullOrEmpty(targetInput) || !int.TryParse(targetInput, out int targetDiskIndex))
            {
                Console.WriteLine("Invalid disk number!");
                return;
            }

            if (sourceDiskIndex == targetDiskIndex)
            {
                Console.WriteLine("Source and target disk cannot be the same!");
                return;
            }

            Console.WriteLine();
            Console.ForegroundColor = ConsoleColor.Red;
            Console.WriteLine(new string('=', 60));
            Console.WriteLine("WARNING: DESTRUCTIVE OPERATION");
            Console.WriteLine(new string('=', 60));
            Console.WriteLine($"Source: Disk {sourceDiskIndex}");
            Console.WriteLine($"Target: Disk {targetDiskIndex}");
            Console.WriteLine();
            Console.WriteLine("ALL DATA ON THE TARGET DISK WILL BE PERMANENTLY ERASED!");
            Console.WriteLine(new string('=', 60));
            Console.ResetColor();

            Console.Write("\nType 'yes' to continue: ");
            string confirm = Console.ReadLine()?.Trim().ToLower();

            if (confirm != "yes")
            {
                Console.WriteLine("Operation cancelled.");
                return;
            }

            Console.Write("Are you absolutely sure? Type 'CONFIRM' to proceed: ");
            string confirm2 = Console.ReadLine()?.Trim();

            if (confirm2 != "CONFIRM")
            {
                Console.WriteLine("Operation cancelled.");
                return;
            }

            bool success = cloner.CloneDiskToDisk(sourceDiskIndex, targetDiskIndex);

            if (success)
            {
                Console.ForegroundColor = ConsoleColor.Green;
                Console.WriteLine("\nDisk cloning completed successfully!");
                Console.WriteLine("You may need to reboot and select the new disk from BIOS to boot from it.");
                Console.ResetColor();
            }
            else
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("\nDisk cloning failed!");
                Console.ResetColor();
            }
        }
    }
}
