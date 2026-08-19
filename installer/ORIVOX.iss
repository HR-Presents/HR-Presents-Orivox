#define MyAppName "ORIVOX"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "HR-Presents"
#define MyAppExeName "ORIVOX.exe"

[Setup]
AppId={{D4011725-6F8B-4DDF-9DCB-7F7C2C83610A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\HR-Presents\ORIVOX
DefaultGroupName=HR-Presents ORIVOX
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist\installer
OutputBaseFilename=ORIVOX-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName=HR-Presents ORIVOX

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\ORIVOX.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\HR-Presents ORIVOX"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\ORIVOX"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch ORIVOX"; Flags: nowait postinstall skipifsilent
