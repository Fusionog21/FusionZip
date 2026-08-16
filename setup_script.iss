; =============================================================================
; FUSION ZIP — OFFICIAL INNO SETUP INSTALLER SCRIPT
; =============================================================================

[Setup]
AppName=Fusion Zip
AppVersion=1.1.0
AppPublisher=Fusion Zip
DefaultDirName={autopf}\Fusion Zip
DefaultGroupName=Fusion Zip
UninstallDisplayIcon={app}\FusionZip.exe
Compression=lzma2
SolidCompression=yes
OutputDir=.
OutputBaseFilename=FusionZip_Setup
SetupIconFile=icon.ico
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "dist\FusionZip.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "FusionZipShell.dll"; DestDir: "{app}"; Flags: ignoreversion regserver
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "unpack_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "vault_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Fusion Zip"; Filename: "{app}\FusionZip.exe"
Name: "{autodesktop}\Fusion Zip"; Filename: "{app}\FusionZip.exe"

[Run]
Filename: "{app}\FusionZip.exe"; Parameters: "--install-shell"; Flags: runhidden
Filename: "{app}\FusionZip.exe"; Description: "Launch Fusion Zip"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{app}\FusionZip.exe"; Parameters: "--uninstall-shell"; Flags: runhidden