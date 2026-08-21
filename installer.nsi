; SGK E-Kesinti Otomasyon - NSIS Kurulum Sihirbazı
; Sürüm: 1.0.6

!include "MUI2.nsh"

; ============================================================
; UYGULAMA BİLGİLERİ
; ============================================================
!define UYGULAMA_ADI "SGK E-Kesinti Otomasyon"
!define SURUM "1.0.6"
!define GELISTIRICI "Arda Yazılım"
!define KISAYOL_ADI "SGK E-Kesinti Otomasyon"
!define EXE_ADI "SGK_E_Kesinti_Otomasyon.exe"

Name "${UYGULAMA_ADI} v${SURUM}"
OutFile "SGK_E_Kesinti_Otomasyon_Setup_v${SURUM}.exe"
InstallDir "$PROGRAMFILES\${UYGULAMA_ADI}"
InstallDirRegKey HKLM "Software\${UYGULAMA_ADI}" "InstallDir"
RequestExecutionLevel admin

; ============================================================
; GÖRSEL AYARLAR
; ============================================================
!define MUI_ICON "installer_icon.ico"
!define MUI_UNICON "installer_icon.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "header.bmp"
!define MUI_ABORTWARNING

; ============================================================
; SAYFA SIRASI
; ============================================================
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; ============================================================
; DILLER
; ============================================================
!insertmacro MUI_LANGUAGE "Turkish"
!insertmacro MUI_LANGUAGE "English"

; ============================================================
; KURULUM
; ============================================================
Section "Kurulum"
    SetOutPath "$INSTDIR"
    
    ; Dosyaları kopyala
    File "dist\SGK_E_Kesinti_Otomasyon\${EXE_ADI}"
    File "dist\SGK_E_Kesinti_Otomasyon\sgk_bot.py"
    File "dist\SGK_E_Kesinti_Otomasyon\KURULUM.py"
    File "dist\SGK_E_Kesinti_Otomasyon\BAT_BASLAT.bat"
    File "dist\SGK_E_Kesinti_Otomasyon\BENI_OKU.txt"
    
    ; Docs klasörünü kopyala
    SetOutPath "$INSTDIR\docs"
    File /r "dist\SGK_E_Kesinti_Otomasyon\docs\*.*"
    
    ; Gerekli DLL'leri kopyala
    SetOutPath "$INSTDIR"
    File /r "dist\SGK_E_Kesinti_Otomasyon\*.dll"
    File /r "dist\SGK_E_Kesinti_Otomasyon\*.pyd"
    
    ; Klasörleri oluştur
    CreateDirectory "$INSTDIR\_internal"
    SetOutPath "$INSTDIR\_internal"
    File /r "dist\SGK_E_Kesinti_Otomasyon\_internal\*.*"
    
    ; Kısayol oluştur
    CreateDirectory "$SMPROGRAMS\${KISAYOL_ADI}"
    CreateShortCut "$SMPROGRAMS\${KISAYOL_ADI}\${UYGULAMA_ADI}.lnk" "$INSTDIR\${EXE_ADI}"
    CreateShortCut "$SMPROGRAMS\${KISAYOL_ADI}\Kaldır.lnk" "$INSTDIR\uninstall.exe"
    
    ; Masaüstü kısayolu
    CreateShortCut "$DESKTOP\${KISAYOL_ADI}.lnk" "$INSTDIR\${EXE_ADI}"
    
    ; Kaldırıcı oluştur
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Registry bilgileri
    WriteRegStr HKLM "Software\${UYGULAMA_ADI}" "InstallDir" "$INSTDIR"
    WriteRegStr HKLM "Software\${UYGULAMA_ADI}" "Version" "${SURUM}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${UYGULAMA_ADI}" \
        "DisplayName" "${UYGULAMA_ADI}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${UYGULAMA_ADI}" \
        "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${UYGULAMA_ADI}" \
        "DisplayVersion" "${SURUM}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${UYGULAMA_ADI}" \
        "Publisher" "${GELISTIRICI}"
    
SectionEnd

; ============================================================
; KALDIRMA
; ============================================================
Section "Kaldır"
    Delete "$INSTDIR\${EXE_ADI}"
    Delete "$INSTDIR\sgk_bot.py"
    Delete "$INSTDIR\KURULUM.py"
    Delete "$INSTDIR\BAT_BASLAT.bat"
    Delete "$INSTDIR\BENI_OKU.txt"
    Delete "$INSTDIR\uninstall.exe"
    Delete "$INSTDIR\*.dll"
    Delete "$INSTDIR\*.pyd"
    
    RMDir /r "$INSTDIR\docs"
    RMDir /r "$INSTDIR\_internal"
    RMDir "$INSTDIR"
    
    Delete "$SMPROGRAMS\${KISAYOL_ADI}\${UYGULAMA_ADI}.lnk"
    Delete "$SMPROGRAMS\${KISAYOL_ADI}\Kaldır.lnk"
    RMDir "$SMPROGRAMS\${KISAYOL_ADI}"
    Delete "$DESKTOP\${KISAYOL_ADI}.lnk"
    
    DeleteRegKey HKLM "Software\${UYGULAMA_ADI}"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${UYGULAMA_ADI}"
SectionEnd
