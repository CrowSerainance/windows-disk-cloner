; Inno Setup Script for Windows Disk Cloner
; Creates a professional installer with all dependencies

[Setup]
AppName=Windows Disk Cloner
AppVersion=1.0.0
AppPublisher=Clonezilla-Inspired Project
AppPublisherURL=https://clonezilla.org/
DefaultDirName={pf}\WindowsDiskCloner
DefaultGroupName=Windows Disk Cloner
OutputDir=installer
OutputBaseFilename=WindowsDiskCloner-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
LicenseFile=
InfoBeforeFile=INSTALLER_README.txt
WizardImageFile=
WizardSmallImageFile=

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Create a &Quick Launch icon"; GroupDescription: "Additional icons:"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "dist\DiskClonerGUI.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\DiskClonerCLI.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Windows Disk Cloner (GUI)"; Filename: "{app}\DiskClonerGUI.exe"; WorkingDir: "{app}"
Name: "{group}\Windows Disk Cloner (CLI)"; Filename: "{app}\DiskClonerCLI.exe"; WorkingDir: "{app}"
Name: "{group}\Uninstall Windows Disk Cloner"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Windows Disk Cloner"; Filename: "{app}\DiskClonerGUI.exe"; Tasks: desktopicon; WorkingDir: "{app}"

[Run]
Filename: "{app}\DiskClonerGUI.exe"; Description: "Launch Windows Disk Cloner"; Flags: nowait postinstall skipifsilent; Check: not WizardSilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  // Check if running as administrator
  if not IsAdminLoggedOn then
  begin
    MsgBox('This installer requires administrator privileges. Please run as Administrator.', mbError, MB_OK);
    Result := False;
  end;
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  if not IsAdminLoggedOn then
  begin
    MsgBox('This uninstaller requires administrator privileges. Please run as Administrator.', mbError, MB_OK);
    Result := False;
  end;
end;

