#ifndef MyAppVersion
#define MyAppVersion "16.1.1"
#endif
#define MyAppName "SEPP-MarketRadar"
#define MyAppPublisher "SEPP"
#define MyAppExeName "MarketRadar.exe"
[Setup]
AppId={{A6B4B1B6-8D8A-4E7A-8D9D-4A6F0C8D4C21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\SEPP-MarketRadar
DefaultGroupName={#MyAppName}
OutputDir=release\installer
OutputBaseFilename=SEPP-MarketRadar-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
[Files]
Source: "release\portable\MarketRadar\*"; DestDir: "{app}"; Excludes: ".portable"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\packaging\install_scheduled_scan.ps1"""; Description: "Install background operations and daily scan tasks"; Flags: postinstall skipifsilent runhidden
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
