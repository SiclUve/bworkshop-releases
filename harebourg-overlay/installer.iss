; Installateur de Harebourg Overlay (Inno Setup 6). Compile avec build_installer.bat.
; Installation pour l'utilisateur seul : pas besoin d'être administrateur, et config.json reste modifiable.
; Deux langues (anglais, français) : celle choisie dans l'installateur est aussi celle de l'application.
#define AppName "Harebourg Overlay"
#define AppVersion "0.3.0"
#define AppExe "HarebourgOverlay.exe"

[Setup]
AppId={{B7C2D1E4-5F63-4A8B-9C10-2E7A4D6F8B31}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\HarebourgOverlay
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=HarebourgOverlay-Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; DestName: "Mode d'emploi.md"; Languages: french; Flags: ignoreversion
Source: "README.en.md"; DestDir: "{app}"; DestName: "User guide.md"; Languages: english; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

; Les réglages et le journal d'erreurs sont créés par le programme : on les retire à la désinstallation.
[UninstallDelete]
Type: files; Name: "{app}\config.json"
Type: files; Name: "{app}\harebourg.log"

[Code]
{ La langue choisie dans l'installateur devient la langue de l'application : on l'écrit dans config.json,
  sauf si ce fichier existe déjà (mise à jour : on garde les réglages et la langue de l'utilisateur). }
procedure CurStepChanged(CurStep: TSetupStep);
var
  Cfg, Lang: String;
begin
  if CurStep = ssPostInstall then
  begin
    Cfg := ExpandConstant('{app}\config.json');
    if not FileExists(Cfg) then
    begin
      if ActiveLanguage = 'french' then
        Lang := 'fr'
      else
        Lang := 'en';
      SaveStringToFile(Cfg, '{"lang": "' + Lang + '"}', False);
    end;
  end;
end;
