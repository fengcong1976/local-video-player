; 本地视频播放器 - Inno Setup 安装包（per-user，免 UAC）
; 版本必须与 app/version.py 一致

#define MyAppName "本地视频播放器"
#define MyAppVersion "1.4.2"
#define MyAppPublisher "深圳市创炫互动网络科技有限公司"
#define MyAppURL "https://www.mrheedu.com"
#define MyAppExeName "本地视频播放器.exe"
#define MyProgId "MrheeduLocalVideoPlayer.Video"

[Setup]
AppId={{449A04BA-E56F-4D47-9663-0211514D77B9}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
RedirectionGuard=no
OutputDir=installer_output
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVersion}
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked
Name: "assoc_common"; Description: "关联常用视频格式（MP4、MKV、AVI、MOV、WMV、FLV、WebM、M4V）"; GroupDescription: "文件关联（可多选）："; Flags: checkedonce
Name: "assoc_disc"; Description: "关联高清/光盘格式（TS、M2TS、MTS、VOB、MPG、MPEG）"; GroupDescription: "文件关联（可多选）："; Flags: unchecked
Name: "assoc_other"; Description: "关联其他格式（RMVB、RM、OGV、3GP、DIVX、F4V、M2V、ASF、MPV、MQV）"; GroupDescription: "文件关联（可多选）："; Flags: unchecked

[Files]
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Registry]
; ---- 播放器 ProgID ----
Root: HKCU; Subkey: "Software\Classes\{#MyProgId}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppName} 视频文件"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\{#MyProgId}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\{#MyProgId}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

; ---- 在右键「打开方式」中显示本程序（所有格式，无条件注册）----
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#MyAppName}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey

; ---- 系统「默认应用」里可找到本播放器 ----
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer"; ValueType: string; ValueName: ""; ValueData: ""; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "{#MyAppName}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "{#MyAppName}，支持全格式视频与字幕"
Root: HKCU; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: "Software\MrheeduLocalVideoPlayer\Capabilities"; Flags: uninsdeletevalue

; ---- 常用格式 ----
Root: HKCU; Subkey: "Software\Classes\.mp4"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_common; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.mp4\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".mp4"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mp4"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.mkv"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_common; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.mkv\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".mkv"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mkv"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.avi"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_common; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.avi\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".avi"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".avi"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.mov"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_common; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.mov\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".mov"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mov"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.wmv"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_common; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.wmv\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".wmv"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".wmv"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.flv"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_common; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.flv\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".flv"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".flv"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.webm"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_common; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.webm\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".webm"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".webm"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.m4v"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_common; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.m4v\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".m4v"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".m4v"; ValueData: "{#MyProgId}"

; ---- 高清与光盘格式 ----
Root: HKCU; Subkey: "Software\Classes\.ts"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_disc; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.ts\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".ts"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".ts"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.m2ts"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_disc; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.m2ts\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".m2ts"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".m2ts"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.mts"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_disc; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.mts\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".mts"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mts"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.vob"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_disc; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.vob\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".vob"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".vob"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.mpg"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_disc; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.mpg\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".mpg"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mpg"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.mpeg"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_disc; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.mpeg\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".mpeg"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mpeg"; ValueData: "{#MyProgId}"

; ---- 其他格式 ----
Root: HKCU; Subkey: "Software\Classes\.rmvb"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_other; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.rmvb\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".rmvb"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".rmvb"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.rm"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_other; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.rm\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".rm"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".rm"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.ogv"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_other; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.ogv\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".ogv"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".ogv"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.3gp"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_other; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.3gp\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".3gp"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".3gp"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.divx"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_other; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.divx\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".divx"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".divx"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.f4v"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_other; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.f4v\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".f4v"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".f4v"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.m2v"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_other; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.m2v\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".m2v"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".m2v"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.asf"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_other; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.asf\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".asf"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".asf"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.mpv"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_other; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.mpv\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".mpv"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mpv"; ValueData: "{#MyProgId}"
Root: HKCU; Subkey: "Software\Classes\.mqv"; ValueType: string; ValueName: ""; ValueData: "{#MyProgId}"; Tasks: assoc_other; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.mqv\OpenWithProgids"; ValueType: string; ValueName: "{#MyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".mqv"; ValueData: ""
Root: HKCU; Subkey: "Software\MrheeduLocalVideoPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mqv"; ValueData: "{#MyProgId}"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
procedure SHChangeNotify(EventId: Integer; Flags: Cardinal; Item1, Item2: Cardinal);
  external 'SHChangeNotify@shell32.dll stdcall';

procedure NotifyShell;
begin
  SHChangeNotify($08000000, $0000, 0, 0);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    NotifyShell;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    NotifyShell;
end;
