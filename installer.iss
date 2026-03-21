; ============================================================
;  VELORIX — Inno Setup Script
;  Creeaza: Setup_Velorix_v1.0.exe
;  Cerinte: Inno Setup 6.x
; ============================================================

#define AppName        "Velorix"
#define AppVersion     "1.0"
#define AppPublisher   "Velorix Software"
#define AppURL         "https://velorix.ro"
#define AppExeName     "Velorix.exe"
#define AppDescription "Management Service Motociclete"

[Setup]
AppId={{B7E4F2A1-3C8D-4E9F-A012-5B6C7D8E9F0A}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={userappdata}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=Setup_Velorix_v{#AppVersion}
SetupIconFile=assets\velorix.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=120
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0
DisableReadyPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Creeaza o pictograma pe Desktop"; GroupDescription: "Pictograme aditionale:"; Flags: checkedonce

[Files]
Source: "dist\Velorix\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\assets\velorix.ico"; Comment: "{#AppDescription}"; Tasks: desktopicon
Name: "{app}\Dezinstaleaza {#AppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Lanseaza {#AppName}"; Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files; Name: "{app}\service_moto.db"
Type: files; Name: "{app}\.env"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure InitializeWizard();
begin
  WizardForm.WelcomeLabel1.Font.Size := 14;
  WizardForm.WelcomeLabel1.Font.Style := [fsBold];
end;

function InitializeUninstall(): Boolean;
var
  Response: Integer;
  Msg: String;
begin
  Msg := 'Esti sigur ca vrei sa dezinstalezi Velorix?' + #13#10 + #13#10;
  Msg := Msg + 'Atentie: baza de date locala va fi stearsa.' + #13#10;
  Msg := Msg + 'Backup-urile din folderul backup\ vor fi pastrate.';
  Response := MsgBox(Msg, mbConfirmation, MB_YESNO);
  Result := (Response = IDYES);
end;