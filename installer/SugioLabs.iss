#define MyAppName "Sugio Labs"
#define MyAppVersion "0.3.0"
#define MyAppPublisher "Sugio Labs"
#define MyAppExeName "SugioLabs.exe"

[Setup]
AppId={{B7A7D0DF-2A6C-4C74-A78F-E5D2C9DD8831}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Sugio Labs
DefaultGroupName=Sugio Labs
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=Sugio-Labs-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\backend\dist\SugioLabs.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Sugio Labs"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Sugio Labs"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Sugio Labs"; Flags: nowait postinstall skipifsilent
