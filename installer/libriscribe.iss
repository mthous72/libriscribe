; Inno Setup Script for LibriScribe GUI
; Requires Inno Setup 6.x -- https://jrsoftware.org/isinfo.php

#define MyAppName "LibriScribe GUI"
#define MyAppVersion "0.5.0"
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
Name: "createenv"; Description: "Create starter .env file for API key configuration"; Flags: checkedonce

[Files]
; Main application (PyInstaller output)
Source: "..\dist\LibriScribeGUI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; .env example
Source: "..\.env.example"; DestDir: "{app}"; DestName: ".env.example"; Flags: ignoreversion

[Dirs]
; Writable projects directory
Name: "{app}\projects"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Configure API Keys"; Filename: "{app}\.env"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvSrc, EnvDst: string;
begin
  if CurStep = ssPostInstall then
  begin
    if IsTaskSelected('createenv') then
    begin
      EnvDst := ExpandConstant('{app}\.env');
      EnvSrc := ExpandConstant('{app}\.env.example');
      if not FileExists(EnvDst) then
      begin
        FileCopy(EnvSrc, EnvDst, False);
      end;
    end;
  end;
end;
