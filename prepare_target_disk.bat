@echo off
REM Helper script to prepare target disk for cloning
REM This removes drive letters and takes the disk offline

echo ============================================================
echo Prepare Target Disk for Cloning
echo ============================================================
echo.
echo This script will help you prepare a target disk for cloning
echo by removing drive letters and taking it offline.
echo.
echo WARNING: This will make the disk inaccessible until you bring it back online!
echo.
pause

echo.
echo Opening Disk Management...
echo.
echo INSTRUCTIONS:
echo 1. In Disk Management, find your TARGET disk (the one you want to clone TO)
echo 2. For each volume on that disk:
echo    - Right-click the volume
echo    - Select "Change Drive Letter and Paths..."
echo    - Click "Remove" (confirm if prompted)
echo 3. Right-click the DISK itself (at the left side, not a volume)
echo    - Select "Offline"
echo.
echo 4. Once the disk shows as "Offline", close Disk Management
echo 5. Return to the Disk Cloner and try the clone operation again
echo.
echo Press any key to open Disk Management...
pause >nul

start diskmgmt.msc

echo.
echo Disk Management has been opened.
echo Follow the instructions above, then return to the Disk Cloner.
echo.
pause

