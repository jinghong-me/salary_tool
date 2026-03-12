; 工资报表生成工具 - Inno Setup 安装脚本
; 使用 Inno Setup 6.x 编译

#define MyAppName "工资报表生成工具"
#define MyAppVersion "2.2"
#define MyAppPublisher "惊鸿科技（济宁）有限公司"
#define MyAppURL "https://www.jinghongtech.com"
#define MyAppExeName "工资报表生成工具.exe"
#define MyAppIcon "icon.ico"

[Setup]
; 安装程序基本信息
AppId={{8F3A2B1C-4D5E-6F7G-8H9I-0J1K2L3M4N5O}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; 默认安装目录
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}

; 安装程序文件名
OutputDir=installer
OutputBaseFilename=工资报表生成工具_v{#MyAppVersion}_安装包

; 安装程序图标
SetupIconFile=icon.ico

; 压缩设置
Compression=lzma2
SolidCompression=yes

; 权限设置
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; 显示设置
WizardStyle=modern
DisableWelcomePage=no
DisableDirPage=no
DisableProgramGroupPage=no

; 版本信息
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} 安装程序
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}.0

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
; 创建快捷方式选项
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; 主程序文件
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

; 数据文件
Source: "net_bank_code.csv"; DestDir: "{app}"; Flags: ignoreversion

; 说明文档
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
; 注意：数据库文件 salary_tool.db 不打包，首次运行时自动创建

[Icons]
; 开始菜单快捷方式
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; 桌面快捷方式
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

; 快速启动栏快捷方式
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: quicklaunchicon

[Run]
; 安装完成后可选运行程序
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 卸载时删除的文件和目录
Type: filesandordirs; Name: "{app}\导出报表"

[Code]
// 安装前检查是否已安装旧版本
function InitializeSetup(): Boolean;
var
  Version: String;
begin
  Result := true;
  
  // 检查是否已有旧版本
  if RegKeyExists(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{8F3A2B1C-4D5E-6F7G-8H9I-0J1K2L3M4N5O}_is1') then
  begin
    if MsgBox('检测到已安装旧版本的工资报表生成工具。' + #13#10 + 
              '建议先卸载旧版本后再安装。' + #13#10 + #13#10 +
              '是否继续安装？', mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := false;
    end;
  end;
end;

// 安装完成后显示提示
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // 创建导出报表目录
    CreateDir(ExpandConstant('{app}\导出报表'));
  end;
end;

// 卸载前确认
function InitializeUninstall(): Boolean;
begin
  Result := MsgBox('确定要卸载 {#MyAppName} 吗？' + #13#10 +
                   '注意：导出报表目录中的文件不会被删除。', 
                   mbConfirmation, MB_YESNO) = IDYES;
end;

// 卸载完成后清理
procedure DeinitializeUninstall();
begin
  // 清理空目录
  RemoveDir(ExpandConstant('{app}'));
end;
