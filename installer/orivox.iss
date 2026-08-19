#define MyAppName "ORIVOX"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "HR-Presents"
#define MyAppExeName "ORIVOX.exe"

[Setup]
AppId={{0E3B7CC9-B30D-4E1F-A64F-2B9782E42F01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\HR-Presents\ORIVOX
DefaultGroupName=HR-Presents ORIVOX
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=ORIVOX-v{#MyAppVersion}-Windows-Setup
SetupIconFile=..\assets\orivox.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\ORIVOX.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\HR-Presents ORIVOX"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\ORIVOX"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch ORIVOX"; Flags: nowait postinstall skipifsilent
