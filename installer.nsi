!ifndef VERSION
  !define VERSION '1.0.0'
!endif

; The name of the installer
Name "Cura ${VERSION}"

; The file to write
OutFile "CuraBCN3D_${VERSION}.exe"

; The default installation directory
InstallDir $PROGRAMFILES\CuraBCN3D_${VERSION}

; Registry key to check for directory (so if you install again, it will 
; overwrite the old one automatically)
InstallDirRegKey HKLM "Software\CuraBCN3D_${VERSION}" "Install_Dir"

; Request application privileges for Windows Vista
RequestExecutionLevel admin

; Set the LZMA compressor to reduce size.
SetCompressor /SOLID lzma
;--------------------------------

!include "MUI2.nsh"
!include "Library.nsh"

; !define MUI_ICON "dist/resources/cura.ico"
!define MUI_BGCOLOR FFFFFF

; Directory page defines
!define MUI_DIRECTORYPAGE_VERIFYONLEAVE

; Header
; Don't show the component description box
!define MUI_COMPONENTSPAGE_NODESC

;Do not leave (Un)Installer page automaticly
!define MUI_FINISHPAGE_NOAUTOCLOSE
!define MUI_UNFINISHPAGE_NOAUTOCLOSE

;Run Cura after installing
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Start CuraBCN3D ${VERSION}"
!define MUI_FINISHPAGE_RUN_FUNCTION "LaunchLink"

;Add an option to show release notes
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\plugins\ChangeLogPlugin\changelog.txt"

; Pages
;!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Reserve Files
!insertmacro MUI_RESERVEFILE_LANGDLL
ReserveFile '${NSISDIR}\Plugins\x86-unicode\InstallOptions.dll'

;--------------------------------

; The stuff to install
Section "CuraBCN3D ${VERSION}"

  SectionIn RO
  
  ; Set output path to the installation directory.
  SetOutPath $INSTDIR
  
  ; Put file there
  File /r "dist\"
  
  ; Write the installation path into the registry
  WriteRegStr HKLM "SOFTWARE\CuraBCN3D_${VERSION}" "Install_Dir" "$INSTDIR"
  
  ; Write the uninstall keys for Windows
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CuraBCN3D_${VERSION}" "DisplayName" "CuraBCN3D ${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CuraBCN3D_${VERSION}" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CuraBCN3D_${VERSION}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CuraBCN3D_${VERSION}" "NoRepair" 1
  WriteUninstaller "uninstall.exe"

  ; Write start menu entries for all users
  SetShellVarContext all
  
  CreateDirectory "$SMPROGRAMS\CuraBCN3D ${VERSION}"
  CreateShortCut "$SMPROGRAMS\CuraBCN3D ${VERSION}\Uninstall CuraBCN3D ${VERSION}.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
  CreateShortCut "$SMPROGRAMS\CuraBCN3D ${VERSION}\CuraBCN3D ${VERSION}.lnk" "$INSTDIR\CuraBCN3D.exe" '' "$INSTDIR\CuraBCN3D.exe" 0
  
SectionEnd

Function LaunchLink
  ; Write start menu entries for all users
  SetShellVarContext all
  Exec '"$WINDIR\explorer.exe" "$SMPROGRAMS\CuraBCN3D ${VERSION}\CuraBCN3D ${VERSION}.lnk"'
FunctionEnd

Section "Install Visual Studio 2010 Redistributable"
    SetOutPath "$INSTDIR"
    File "..\cura-binary-data\windows\vcredist_x32.exe"
    
    IfSilent +2
      ExecWait '"$INSTDIR\vcredist_x32.exe" /q /norestart'

SectionEnd

Section "Install Arduino Drivers"
  ; Set output path to the driver directory.
  SetOutPath "$INSTDIR\drivers\"
  File /r "..\cura-binary-data\windows\arduino\"
  
  ${If} ${RunningX64}
    IfSilent +2
      ExecWait '"$INSTDIR\drivers\dpinst64.exe" /lm'
  ${Else}
    IfSilent +2
      ExecWait '"$INSTDIR\drivers\dpinst32.exe" /lm'
  ${EndIf}
SectionEnd

Section "Open STL files with Cura"
	WriteRegStr HKCR .stl "" "Cura STL model file"
	DeleteRegValue HKCR .stl "Content Type"
	WriteRegStr HKCR "Cura STL model file\DefaultIcon" "" "$INSTDIR\CuraBCN3D.exe,0"
	WriteRegStr HKCR "Cura STL model file\shell" "" "open"
	WriteRegStr HKCR "Cura STL model file\shell\open\command" "" '"$INSTDIR\CuraBCN3D.exe" "%1"'
SectionEnd

Section /o "Open OBJ files with Cura"
	WriteRegStr HKCR .obj "" "Cura OBJ model file"
	DeleteRegValue HKCR .obj "Content Type"
	WriteRegStr HKCR "Cura OBJ model file\DefaultIcon" "" "$INSTDIR\CuraBCN3D.exe,0"
	WriteRegStr HKCR "Cura OBJ model file\shell" "" "open"
	WriteRegStr HKCR "Cura OBJ model file\shell\open\command" "" '"$INSTDIR\CuraBCN3D.exe" "%1"'
SectionEnd

;--------------------------------

; Uninstaller

Section "Uninstall"
  
  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CuraBCN3D_${VERSION}"
  DeleteRegKey HKLM "SOFTWARE\CuraBCN3D_${VERSION}"

  ; Write start menu entries for all users
  SetShellVarContext all
  ; Remove directories used
  RMDir /r "$SMPROGRAMS\CuraBCN3D ${VERSION}"
  RMDir /r "$INSTDIR"

SectionEnd
