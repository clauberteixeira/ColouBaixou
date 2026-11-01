; Instalador do ColouBaixô (Inno Setup 6). Gere com scripts\make_installer.ps1.
#define AppName "ColouBaixô"
#define AppExe "ColouBaixou.exe"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{6F3B2A41-8C7D-4E59-9B1A-2D5C7E0F9A13}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppName}
AppPublisherURL=https://github.com/clauberteixeira/ColouBaixou
; instala só para o usuário: não pede senha de administrador
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\ColouBaixou
DisableProgramGroupPage=yes
DisableDirPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist\installer
OutputBaseFilename=ColouBaixou-Setup-{#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/ultra64
SolidCompression=yes
LZMANumBlockThreads=4
; o compilador é de 32 bits e fica sem memória nesta compressão; em processo separado usa 64 bits
LZMAUseSeparateProcess=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; numa atualização, apaga os arquivos internos da versão anterior antes de copiar os novos
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\ColouBaixou\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir o {#AppName}"; Flags: nowait postinstall skipifsilent
; atualização automática (instalador rodando em silêncio): reabre o programa sozinho
Filename: "{app}\{#AppExe}"; Flags: nowait; Check: WizardSilent

[UninstallDelete]
; componentes baixados pelo programa (yt-dlp, Deno), temporários e logs; os vídeos baixados ficam
Type: filesandordirs; Name: "{localappdata}\YoutubeForDownload\bin"
Type: filesandordirs; Name: "{localappdata}\YoutubeForDownload\tmp"
Type: filesandordirs; Name: "{localappdata}\YoutubeForDownload\logs"
