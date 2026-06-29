; Inno Setup Script for LibriScribe GUI
; Requires Inno Setup 6.x -- https://jrsoftware.org/isinfo.php

#define MyAppName "LibriScribe GUI"
#define MyAppVersion "0.6.0"
#define MyAppPublisher "mthous72"
#define MyAppURL "https://github.com/mthous72/libriscribe"
#define MyAppExeName "LibriScribeGUI.exe"

[Setup]
AppId={{A1F2B3C4-D5E6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\LibriScribeGUI
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=..\dist\installer
OutputBaseFilename=LibriScribeGUI-{#MyAppVersion}-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=libriscribe.ico
UninstallDisplayIcon={app}\LibriScribeGUI.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application (PyInstaller output). The bundle includes .env.example, which
; the app copies to %LOCALAPPDATA%\LibriScribe\.env on first run. API keys and
; generated projects live there (user-writable); Program Files stays read-only.
Source: "..\dist\LibriScribeGUI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
