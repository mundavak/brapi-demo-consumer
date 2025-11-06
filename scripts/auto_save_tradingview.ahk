; AutoHotkey Script for TradingView Export Automation
; This script automatically clicks Save in Windows save dialogs
; 
; USAGE:
; 1. Install AutoHotkey (https://www.autohotkey.com/)
; 2. Run this script
; 3. Use your TradingView extension
; 4. When save dialog appears, script will auto-click Save
;
; Press Ctrl+Alt+Q to quit this script

#NoEnv
#SingleInstance Force
#Persistent

; Configuration
SetTitleMatchMode, 2  ; Partial title matching
SetControlDelay, 10
SetWinDelay, 10

; Display tray tip
TrayTip, TradingView Auto-Save, Script is running. Ctrl+Alt+Q to quit., 3

; Main loop - check for save dialogs every 100ms
SetTimer, CheckForSaveDialog, 100

CheckForSaveDialog:
    ; Look for common save dialog titles
    IfWinExist, Save As
    {
        WinActivate, Save As
        Sleep, 100
        ; Try different methods to click Save
        
        ; Method 1: Send Enter key
        Send, {Enter}
        Sleep, 200
        
        ; Method 2: Click Save button by text
        ControlClick, Button1, Save As  ; Usually the first button
        Sleep, 200
        
        ; Method 3: Alt+S (Save shortcut)
        Send, !s
        
        TrayTip, Auto-Save, Save button clicked!, 2
        return
    }
    
    ; Check for Chrome download dialog
    IfWinExist, ahk_class Chrome_WidgetWin_1
    {
        WinGetTitle, Title, ahk_class Chrome_WidgetWin_1
        IfInString, Title, wants to save
        {
            WinActivate, ahk_class Chrome_WidgetWin_1
            Sleep, 100
            Send, {Enter}  ; Accept the download
            TrayTip, Auto-Save, Chrome download accepted!, 2
            return
        }
    }
    
    ; Check for Windows 10/11 save dialog
    IfWinExist, ahk_class #32770  ; Standard Windows dialog class
    {
        WinGetTitle, DialogTitle, ahk_class #32770
        IfInString, DialogTitle, Save
        {
            WinActivate, ahk_class #32770
            Sleep, 100
            
            ; Try to find and click Save button
            ControlClick, Button1, ahk_class #32770
            Sleep, 100
            
            ; Fallback: Enter key
            Send, {Enter}
            
            TrayTip, Auto-Save, Windows save dialog handled!, 2
            return
        }
    }
return

; Hotkey to quit the script
^!q::
    TrayTip, TradingView Auto-Save, Script stopped., 2
    ExitApp

; Hotkey to manually trigger save (Ctrl+Alt+S)
^!s::
    TrayTip, Manual Save, Sending Enter key..., 1
    Send, {Enter}
return

; Show help when script starts
^!h::
    MsgBox, 64, TradingView Auto-Save Help, 
    (
    TradingView Export Auto-Save Script
    
    ACTIVE HOTKEYS:
    Ctrl+Alt+Q - Quit script
    Ctrl+Alt+S - Manual save (send Enter)
    Ctrl+Alt+H - Show this help
    
    FEATURES:
    • Automatically detects Windows save dialogs
    • Clicks Save button when TradingView export triggered
    • Works with Chrome download confirmations
    • Runs silently in system tray
    
    The script monitors for save dialogs and automatically:
    1. Activates the dialog window
    2. Clicks the Save button
    3. Shows notification when complete
    
    Safe to run in background while using TradingView.
    )
return