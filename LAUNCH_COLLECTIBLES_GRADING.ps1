# ═══════════════════════════════════════════════════════════════════════════════
#   COLLECTIBLES GRADING SYSTEM - ADVANCED PRODUCTION LAUNCHER
#   AI-Powered Collectibles Analysis Platform with Sound & Graphics
# ═══════════════════════════════════════════════════════════════════════════════

$Host.UI.RawUI.WindowTitle = "Collectibles Grading System"
$ErrorActionPreference = "SilentlyContinue"

# Set console colors
$Host.UI.RawUI.BackgroundColor = "Black"
$Host.UI.RawUI.ForegroundColor = "Cyan"
Clear-Host

# ─── SOUND FUNCTIONS ───────────────────────────────────────────────────────────

function Play-StartupSequence {
    $notes = @(523, 659, 784, 1047)  # C5, E5, G5, C6
    foreach ($freq in $notes) {
        [Console]::Beep($freq, 150)
        Start-Sleep -Milliseconds 50
    }
}

function Play-SuccessSound {
    [Console]::Beep(784, 100)
    Start-Sleep -Milliseconds 50
    [Console]::Beep(988, 100)
    Start-Sleep -Milliseconds 50
    [Console]::Beep(1319, 200)
}

function Play-ErrorSound {
    [Console]::Beep(200, 500)
}

function Play-ClickSound {
    [Console]::Beep(800, 50)
}

function Play-ProgressTone {
    param([int]$step)
    $freq = 400 + ($step * 50)
    [Console]::Beep($freq, 80)
}

# ─── DISPLAY FUNCTIONS ─────────────────────────────────────────────────────────

function Write-ColorText {
    param(
        [string]$Text,
        [ConsoleColor]$Color = "White"
    )
    $oldColor = $Host.UI.RawUI.ForegroundColor
    $Host.UI.RawUI.ForegroundColor = $Color
    Write-Host $Text -NoNewline
    $Host.UI.RawUI.ForegroundColor = $oldColor
}

function Write-Banner {
    $banner = @"

    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║   ██████╗  ██████╗ ██╗     ██╗     ███████╗ ██████╗████████╗     ║
    ║  ██╔════╝ ██╔═══██╗██║     ██║     ██╔════╝██╔════╝╚══██╔══╝     ║
    ║  ██║      ██║   ██║██║     ██║     █████╗  ██║        ██║        ║
    ║  ██║      ██║   ██║██║     ██║     ██╔══╝  ██║        ██║        ║
    ║  ╚██████╗ ╚██████╔╝███████╗███████╗███████╗╚██████╗   ██║        ║
    ║   ╚═════╝  ╚═════╝ ╚══════╝╚══════╝╚══════╝ ╚═════╝   ╚═╝        ║
    ║                                                                   ║
    ║              ██████╗ ██████╗  █████╗ ██████╗ ██╗███╗   ██╗ ██████╗║
    ║             ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║██╔════╝║
    ║             ██║  ███╗██████╔╝███████║██║  ██║██║██╔██╗ ██║██║  ███║
    ║             ██║   ██║██╔══██╗██╔══██║██║  ██║██║██║╚██╗██║██║   ██║
    ║             ╚██████╔╝██║  ██║██║  ██║██████╔╝██║██║ ╚████║╚██████╔╝
    ║              ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝║
    ║                                                                   ║
    ║                    AI-POWERED ANALYSIS SYSTEM                     ║
    ║                         Version 2.0.0                             ║
    ╚═══════════════════════════════════════════════════════════════════╝

"@

    Write-Host $banner -ForegroundColor Cyan
}

function Write-Status {
    param(
        [string]$Message,
        [ValidateSet("INFO", "SUCCESS", "WARNING", "ERROR")]
        [string]$Type = "INFO"
    )

    $timestamp = Get-Date -Format "HH:mm:ss"
    $colors = @{
        "INFO"    = "Cyan"
        "SUCCESS" = "Green"
        "WARNING" = "Yellow"
        "ERROR"   = "Red"
    }

    Write-Host "[$timestamp] " -ForegroundColor DarkGray -NoNewline
    Write-Host "[$($Type.PadRight(7))] " -ForegroundColor $colors[$Type] -NoNewline
    Write-Host $Message -ForegroundColor White
}

function Show-ProgressAnimation {
    param(
        [string]$Activity,
        [int]$PercentComplete
    )

    $width = 40
    $filled = [math]::Floor($width * $PercentComplete / 100)
    $empty = $width - $filled

    $bar = "█" * $filled + "░" * $empty

    Write-Host "`r" -NoNewline
    Write-Host "  [$bar] $PercentComplete% - $Activity     " -ForegroundColor Cyan -NoNewline
}

function Show-Spinner {
    param([int]$Iterations = 10)

    $spinChars = @("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
    for ($i = 0; $i -lt $Iterations; $i++) {
        foreach ($char in $spinChars) {
            Write-Host "`r  $char " -ForegroundColor Cyan -NoNewline
            Start-Sleep -Milliseconds 80
        }
    }
    Write-Host "`r    " -NoNewline
}

# ─── SYSTEM CHECK FUNCTIONS ────────────────────────────────────────────────────

function Test-SystemComponent {
    param(
        [string]$Name,
        [string]$Path
    )

    Write-Host "  " -NoNewline
    Write-Host "○ " -ForegroundColor DarkGray -NoNewline
    Write-Host "Checking $Name..." -ForegroundColor Gray -NoNewline

    Start-Sleep -Milliseconds 300

    if (Test-Path $Path) {
        Write-Host "`r  " -NoNewline
        Write-Host "● " -ForegroundColor Green -NoNewline
        Write-Host "$Name " -ForegroundColor White -NoNewline
        Write-Host "READY" -ForegroundColor Green
        return $true
    } else {
        Write-Host "`r  " -NoNewline
        Write-Host "● " -ForegroundColor Red -NoNewline
        Write-Host "$Name " -ForegroundColor White -NoNewline
        Write-Host "NOT FOUND" -ForegroundColor Red
        return $false
    }
}

function Test-AllSystems {
    Write-Host ""
    Write-Host "  ┌─────────────────────────────────────────┐" -ForegroundColor DarkCyan
    Write-Host "  │         SYSTEM DIAGNOSTICS              │" -ForegroundColor DarkCyan
    Write-Host "  └─────────────────────────────────────────┘" -ForegroundColor DarkCyan
    Write-Host ""

    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    if (-not $scriptDir) { $scriptDir = $PWD.Path }

    $checks = @(
        @{Name = "Backend Server"; Path = "$scriptDir\backend\main.py"},
        @{Name = "Electron App"; Path = "$scriptDir\electron-app\main.js"},
        @{Name = "Database"; Path = "$scriptDir\collectibles.db"},
        @{Name = "AI Providers"; Path = "$scriptDir\backend\ai_providers"},
        @{Name = "Pricing Engine"; Path = "$scriptDir\backend\pricing_sources"},
        @{Name = "Webcam Module"; Path = "$scriptDir\webcam_module"}
    )

    $allPassed = $true
    $step = 0

    foreach ($check in $checks) {
        $result = Test-SystemComponent -Name $check.Name -Path $check.Path
        if (-not $result) { $allPassed = $false }
        Play-ProgressTone -step $step
        $step++
    }

    Write-Host ""
    return $allPassed
}

# ─── LAUNCH FUNCTIONS ──────────────────────────────────────────────────────────

function Start-Backend {
    Write-Status "Starting FastAPI Backend Server..." "INFO"

    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    if (-not $scriptDir) { $scriptDir = $PWD.Path }
    $backendDir = "$scriptDir\backend"

    $env:PYTHONPATH = $scriptDir

    Start-Process -FilePath "cmd.exe" -ArgumentList "/k", "cd /d `"$backendDir`" && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload" -WindowStyle Normal

    Write-Status "Backend server starting at http://localhost:8000" "SUCCESS"
    Write-Status "API Documentation: http://localhost:8000/docs" "INFO"

    return $true
}

function Start-GUI {
    Write-Status "Starting Electron GUI..." "INFO"

    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    if (-not $scriptDir) { $scriptDir = $PWD.Path }
    $electronDir = "$scriptDir\electron-app"

    Start-Process -FilePath "cmd.exe" -ArgumentList "/k", "cd /d `"$electronDir`" && npm start" -WindowStyle Normal

    Write-Status "Electron GUI launching..." "SUCCESS"

    return $true
}

function Open-WebLauncher {
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    if (-not $scriptDir) { $scriptDir = $PWD.Path }
    $launcherHtml = "$scriptDir\launcher\launcher.html"

    if (Test-Path $launcherHtml) {
        Start-Process $launcherHtml
        Write-Status "Opened web launcher in browser" "SUCCESS"
    } else {
        Write-Status "Web launcher not found" "ERROR"
    }
}

# ─── MAIN MENU ─────────────────────────────────────────────────────────────────

function Show-Menu {
    Write-Host ""
    Write-Host "  ┌─────────────────────────────────────────┐" -ForegroundColor Cyan
    Write-Host "  │            LAUNCH OPTIONS               │" -ForegroundColor Cyan
    Write-Host "  └─────────────────────────────────────────┘" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "    [1] " -ForegroundColor Yellow -NoNewline
    Write-Host "Launch Full System (Backend + GUI)" -ForegroundColor White
    Write-Host "    [2] " -ForegroundColor Yellow -NoNewline
    Write-Host "Launch Backend Only" -ForegroundColor White
    Write-Host "    [3] " -ForegroundColor Yellow -NoNewline
    Write-Host "Launch GUI Only" -ForegroundColor White
    Write-Host "    [4] " -ForegroundColor Yellow -NoNewline
    Write-Host "Open Web Launcher (Browser)" -ForegroundColor White
    Write-Host "    [5] " -ForegroundColor Yellow -NoNewline
    Write-Host "Run System Diagnostics" -ForegroundColor White
    Write-Host "    [Q] " -ForegroundColor Red -NoNewline
    Write-Host "Exit" -ForegroundColor White
    Write-Host ""
}

# ─── MAIN EXECUTION ────────────────────────────────────────────────────────────

# Play startup sound
Play-StartupSequence

# Show banner
Write-Banner

# Initial system check
$systemReady = Test-AllSystems

if (-not $systemReady) {
    Write-Host ""
    Write-Status "Some components may be missing. Proceed with caution." "WARNING"
    Play-ErrorSound
}

# Main loop
$running = $true
while ($running) {
    Show-Menu

    $choice = Read-Host "    Enter choice"
    Play-ClickSound

    switch ($choice.ToUpper()) {
        "1" {
            Write-Host ""
            Write-Status "Launching full system..." "INFO"
            Write-Host ""

            # Progress animation
            for ($i = 0; $i -le 100; $i += 10) {
                Show-ProgressAnimation -Activity "Initializing..." -PercentComplete $i
                Start-Sleep -Milliseconds 100
            }
            Write-Host ""

            Start-Backend
            Start-Sleep -Seconds 3
            Start-GUI

            Play-SuccessSound
            Write-Host ""
            Write-Status "SYSTEM LAUNCH COMPLETE!" "SUCCESS"
            Write-Host ""

            $running = $false
        }
        "2" {
            Write-Host ""
            Start-Backend
            Play-SuccessSound
        }
        "3" {
            Write-Host ""
            Start-GUI
            Play-SuccessSound
        }
        "4" {
            Write-Host ""
            Open-WebLauncher
        }
        "5" {
            Write-Host ""
            Test-AllSystems
        }
        "Q" {
            Write-Host ""
            Write-Status "Goodbye!" "INFO"
            $running = $false
        }
        default {
            Write-Status "Invalid option" "WARNING"
        }
    }
}

Write-Host ""
Write-Host "  ═══════════════════════════════════════════" -ForegroundColor DarkCyan
Write-Host "    Press any key to close..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
