<#
    TikTok & Douyin Downloader - Windows Uninstaller (PowerShell)

    Run:
        irm https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/uninstall.ps1 | iex

    Removes:
        1. The MediaDownloader installation directory (from the user PATH, or the
           default %LOCALAPPDATA%\MediaDownloader)
        2. The corresponding entry from the user PATH
#>

$ErrorActionPreference = 'Stop'

# -----------------------------------------------------------------------------
# Locate the installation directory
# -----------------------------------------------------------------------------
$installDir = ""
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath) {
    foreach ($entry in $userPath -split ";") {
        if ($entry -and (Test-Path (Join-Path $entry "media-downloader.exe"))) {
            $installDir = $entry.Trim()
            break
        }
    }
}
if (-not $installDir) {
    $installDir = Join-Path $env:LOCALAPPDATA "MediaDownloader"
}

Write-Host ""
Write-Host "=================================================="
Write-Host "   🗑  TikTok & Douyin Downloader Uninstaller    "
Write-Host "=================================================="

if (Test-Path $installDir) {
    Write-Host "Removing installation directory: $installDir"
    Remove-Item -Recurse -Force $installDir
} else {
    Write-Host "Installation directory not found: $installDir"
}

# -----------------------------------------------------------------------------
# Remove the PATH entry
# -----------------------------------------------------------------------------
$changed = $false
if ($userPath) {
    $parts = @($userPath -split ";" | Where-Object { $_ -and $_.Trim() -ne $installDir.Trim() })
    $newPath = $parts -join ";"
    if ($newPath -ne $userPath) {
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        $changed = $true
        Write-Host "Removed PATH entry: $installDir"
    }
}

Write-Host ""
if ($changed) {
    Write-Host "✅ Uninstalled. Please open a new terminal window to apply the PATH change."
} else {
    Write-Host "✅ Uninstalled."
}
Write-Host "=================================================="
