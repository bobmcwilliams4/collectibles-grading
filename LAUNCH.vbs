' ═══════════════════════════════════════════════════════════════════════════════
'   COLLECTIBLES GRADING SYSTEM - VBS LAUNCHER
'   Double-click this file to launch the system with graphics and sound
' ═══════════════════════════════════════════════════════════════════════════════

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script is located
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Path to PowerShell launcher
strPSLauncher = strScriptDir & "\LAUNCH_COLLECTIBLES_GRADING.ps1"

' Check if PowerShell launcher exists
If objFSO.FileExists(strPSLauncher) Then
    ' Launch PowerShell with execution policy bypass and the launcher script
    strCommand = "powershell.exe -ExecutionPolicy Bypass -NoProfile -File """ & strPSLauncher & """"
    objShell.Run strCommand, 1, False
Else
    ' Fallback to batch launcher
    strBatchLauncher = strScriptDir & "\LAUNCH_COLLECTIBLES_GRADING.bat"
    If objFSO.FileExists(strBatchLauncher) Then
        objShell.Run """" & strBatchLauncher & """", 1, False
    Else
        MsgBox "Launcher not found! Please check your installation.", vbCritical, "Collectibles Grading System"
    End If
End If

Set objShell = Nothing
Set objFSO = Nothing
