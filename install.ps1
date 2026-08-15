<#
    TikTok & Douyin Downloader - Windows One-Click Installer (PowerShell)

    Install:
        irm https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/install.ps1 | iex

    Options (only when run directly, e.g. powershell -File install.ps1):
        -Lang        "zh" or "en" (auto-detected from the system locale by default)
        -InstallDir  custom installation directory (default: $env:LOCALAPPDATA\MediaDownloader)

    What it does:
        1. Downloads MediaDownloader-Windows-x64-CLI-<ver>.zip from GitHub Releases
           (direct GitHub first, then gh-proxy.com / ghproxy.net mirrors)
        2. Extracts the CLI (media-downloader.exe + bundled Playwright browser sidecar)
           into the installation directory
        3. Adds the installation directory to the user PATH
        4. Prints the changelog of the installed version

    Uninstall:
        irm https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/uninstall.ps1 | iex
#>

param(
    [string]$Lang = "",
    [string]$InstallDir = ""
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# -----------------------------------------------------------------------------
# GitHub Repository Configuration
# -----------------------------------------------------------------------------
$GITHUB_USER = "Francis-Xavier-code"
$GITHUB_REPO = "tiktok-douyin-dl"
$RELEASE_TAG = "v2.1.0"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
function Write-Colored($Color, $Text) {
    Write-Host -ForegroundColor $Color $Text
}

# -----------------------------------------------------------------------------
# Pretty progress-bar download helpers (style inspired by the Pi installer)
# -----------------------------------------------------------------------------
$script:spIdx = 0

function Draw-Progress {
    param([int]$Pct, [string]$Label)
    $esc = [char]27
    $spinners = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    $sp = $spinners[$script:spIdx % $spinners.Length]
    $script:spIdx++
    $width = 30
    $filled = [math]::Floor($Pct * $width / 100)
    if ($filled -gt $width) { $filled = $width }
    if ($filled -lt 0) { $filled = 0 }
    $third = [math]::Floor($width / 3)
    $sb = [System.Text.StringBuilder]::new()
    for ($i = 0; $i -lt $width; $i++) {
        if ($i -lt $filled) {
            if ($i -lt $third) { [void]$sb.Append("${esc}[32m█${esc}[0m") }
            elseif ($i -lt ($third * 2)) { [void]$sb.Append("${esc}[36m█${esc}[0m") }
            else { [void]$sb.Append("${esc}[33m█${esc}[0m") }
        }
        elseif ($i -eq $filled) { [void]$sb.Append("${esc}[1;37m▓${esc}[0m") }
        else { [void]$sb.Append("${esc}[2m░${esc}[0m") }
    }
    $pctStr = if ($Pct -lt 0) { ' --' } else { '{0,3}' -f $Pct }
    Write-Host "`r${esc}[K  $sp $($sb.ToString()) $pctStr% $Label" -NoNewline
}

function Invoke-DownloadWithProgress {
    param([string]$Url, [string]$OutFile, [string]$Label)

    $total = 0L
    try {
        $headReq = [System.Net.HttpWebRequest]::Create($Url)
        $headReq.Method = 'HEAD'
        $headReq.UserAgent = 'MediaDownloader-Installer'
        $headReq.Timeout = 20000
        $headResp = $headReq.GetResponse()
        try { $total = $headResp.ContentLength } finally { $headResp.Close() }
    } catch {
        $total = 0
    }

    $handler = New-Object System.Net.Http.HttpClientHandler
    $client = New-Object System.Net.Http.HttpClient($handler)
    $client.DefaultRequestHeaders.UserAgent.ParseAdd('MediaDownloader-Installer')
    try {
        $resp = $client.GetAsync($Url, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
        if (-not $resp.IsSuccessStatusCode) {
            throw "HTTP $([int]$resp.StatusCode) $($resp.StatusCode)"
        }
        if ($total -le 0) {
            $cl = $resp.Content.Headers.ContentLength
            if ($cl -and $cl -gt 0) { $total = $cl } else { $total = 0 }
        }
        $stream = $resp.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
        $fs = [System.IO.File]::Create($OutFile)
        $buffer = New-Object byte[] (81920)
        $downloaded = 0L
        $last = 0
        try {
            while (($read = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {
                $fs.Write($buffer, 0, $read)
                $downloaded += $read
                $now = [Environment]::TickCount
                if ($total -gt 0 -and ($now - $last) -gt 60) {
                    $pct = [math]::Floor($downloaded * 100 / $total)
                    Draw-Progress -Pct $pct -Label $Label
                    $last = $now
                }
            }
        } finally {
            $fs.Dispose()
            $stream.Dispose()
            $resp.Dispose()
        }
        if ($total -gt 0) { Draw-Progress -Pct 100 -Label $Label }
        Write-Host ""
    } finally {
        $client.Dispose()
    }
}

# 1. Choose language (auto-detect from system locale; -Lang overrides)
if (-not $Lang) {
    $Lang = if ((Get-Culture).Name -like "zh*") { "zh" } else { "en" }
}

function T($Zh, $En) {
    if ($Lang -eq "zh") { $Zh } else { $En }
}

Write-Host ""
Write-Colored Blue "=================================================="
Write-Colored Blue "   🚀 TikTok & Douyin Downloader Installer        "
Write-Colored Blue "=================================================="
Write-Host ""

# -----------------------------------------------------------------------------
# 2. Installation directory
# -----------------------------------------------------------------------------
if (-not $InstallDir) {
    $InstallDir = Join-Path $env:LOCALAPPDATA "MediaDownloader"
}
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# -----------------------------------------------------------------------------
# 3. Download + extract the CLI zip (direct GitHub, then mirrors)
# -----------------------------------------------------------------------------
if ($GITHUB_USER -eq "YOUR_GITHUB_USERNAME" -or $GITHUB_REPO -eq "YOUR_GITHUB_REPO") {
    Write-Colored Red (T "❌ 错误: install.ps1 中的 GITHUB_USER / GITHUB_REPO 未配置。" "❌ Error: GITHUB_USER / GITHUB_REPO not configured in install.ps1.")
    exit 1
}

$version  = $RELEASE_TAG.TrimStart("v")
$archive  = "MediaDownloader-Windows-x64-CLI-$version.zip"
$rawUrl   = "https://github.com/$GITHUB_USER/$GITHUB_REPO/releases/download/$RELEASE_TAG/$archive"

# Mirror URLs: direct GitHub first, then domestic accelerators.
$mirrorUrls = @(
    $rawUrl
    "https://gh-proxy.com/$rawUrl"
    "https://ghproxy.net/$rawUrl"
)

$tmpZip = Join-Path $env:TEMP ("MediaDownloader-" + [guid]::NewGuid().ToString("N") + ".zip")
$downloaded = $false
$script:spIdx = 0

$mirrorTotal = $mirrorUrls.Count
$mirrorIdx = 0
foreach ($url in $mirrorUrls) {
    $mirrorIdx++
    $dlLabel = T "下载 $archive (镜像 $mirrorIdx/$mirrorTotal)" "Downloading $archive (mirror $mirrorIdx/$mirrorTotal)"
    try {
        Invoke-DownloadWithProgress -Url $url -OutFile $tmpZip -Label $dlLabel
        $downloaded = $true
        break
    } catch {
        Write-Host ""
        Write-Host (T "   ⚠ 下载失败，尝试下一个源..." "   ⚠ Download failed, trying next mirror...")
        Remove-Item -Force $tmpZip -ErrorAction SilentlyContinue
    }
}

if (-not $downloaded) {
    Remove-Item -Force $tmpZip -ErrorAction SilentlyContinue
    Write-Colored Red (T "❌ 错误: 所有下载源均失败（$RELEASE_TAG）。" "❌ Error: All download sources failed ($RELEASE_TAG).")
    Write-Colored Red (T "   请检查网络或开启代理后重试。" "   Please check your network or enable a proxy and retry.")
    exit 1
}

Write-Host (T "📦 正在解压到 $InstallDir ..." "📦 Extracting to $InstallDir ...")
Expand-Archive -Path $tmpZip -DestinationPath $InstallDir -Force
Remove-Item -Force $tmpZip -ErrorAction SilentlyContinue

$exe = Join-Path $InstallDir "media-downloader.exe"
if (-not (Test-Path $exe)) {
    Write-Colored Red (T "❌ 错误: 解压后未找到 media-downloader.exe。" "❌ Error: media-downloader.exe not found after extraction.")
    exit 1
}

# -----------------------------------------------------------------------------
# 4. Add the installation directory to the user PATH
# -----------------------------------------------------------------------------
$needRestart = $false
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathEntries = @($userPath -split ";") | Where-Object { $_ -and $_.Trim() -eq $InstallDir.Trim() }
if ($pathEntries.Count -gt 0) {
    Write-Host (T "✓ 已存在于 PATH 中，跳过配置。" "✓ Already on PATH, skipping configuration.")
} else {
    $newPath = if ($userPath) { $userPath.TrimEnd(";") + ";" + $InstallDir } else { $InstallDir }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    # Make it work in the current session right away
    $env:Path = $InstallDir + ";" + $env:Path
    $needRestart = $true
    Write-Host (T "✓ 已将安装目录添加到用户 PATH。" "✓ Added the installation directory to the user PATH.")
}

# -----------------------------------------------------------------------------
# 5. Show the changelog of the installed version (CLI + 全平台 entries)
# -----------------------------------------------------------------------------
function Show-Changelog {
    $changelogUrl = "https://raw.githubusercontent.com/$GITHUB_USER/$GITHUB_REPO/main/changelog.json"
    $mirrors = @(
        $changelogUrl
        "https://gh-proxy.com/$changelogUrl"
        "https://ghproxy.net/$changelogUrl"
        "https://fastly.jsdelivr.net/gh/$GITHUB_USER/$GITHUB_REPO@main/changelog.json"
    )
    $tmpJson = Join-Path $env:TEMP ("MediaDownloader-changelog-" + [guid]::NewGuid().ToString("N") + ".json")
    $fetched = $false
    foreach ($url in $mirrors) {
        try {
            Invoke-WebRequest -Uri $url -OutFile $tmpJson -UseBasicParsing `
                -TimeoutSec 15 -Headers @{ "User-Agent" = "MediaDownloader-Installer" } -ErrorAction Stop
            $fetched = $true
            break
        } catch { }
    }
    if (-not $fetched) {
        Remove-Item -Force $tmpJson -ErrorAction SilentlyContinue
        return
    }
    try {
        $data = Get-Content -Raw $tmpJson | ConvertFrom-Json
        $target = $data.versions | Where-Object { $_.version.TrimStart("v") -eq $version } | Select-Object -First 1
        if ($target) {
            $entries = @()
            $entries += $target.entries.cli
            $entries += $target.entries.all
            $entries = @($entries | Where-Object { $_ })
            if ($entries.Count -gt 0) {
                $title = if ($Lang -eq "zh") { "📝 本版本更新内容" } else { "📝 Changelog for this version" }
                Write-Host ""
                Write-Host "$title  v$version"
                Write-Host ("-" * 50)
                foreach ($e in $entries) {
                    foreach ($line in ($e -split "`n")) {
                        Write-Host "  • $line"
                    }
                }
                Write-Host ("-" * 50)
            }
        }
    } catch { }
    Remove-Item -Force $tmpJson -ErrorAction SilentlyContinue
}

Show-Changelog

# -----------------------------------------------------------------------------
# 6. Success message
# -----------------------------------------------------------------------------
Write-Host ""
Write-Colored Green "=================================================="
if ($Lang -eq "zh") {
    Write-Colored Green "🎉 安装与配置成功！"
    Write-Colored Green "=================================================="
    Write-Host "📁 程序保存路径: $InstallDir"
    Write-Host '🚀 统一下载命令: media-downloader "分享文本或链接"'
    Write-Host "🔎 程序会自动识别抖音或 TikTok 链接。"
    Write-Host ""
    Write-Colored Yellow "🔔 使用提示:"
    if ($needRestart) {
        Write-Host "1. 💡 请新开一个终端窗口（或重新登录）使 PATH 配置生效！"
        Write-Host '2. 之后在任意目录运行 media-downloader "分享文本或链接" 即可下载！'
    } else {
        Write-Host '1. 终端任意目录下直接运行 media-downloader "分享文本或链接" 即可下载！'
    }
} else {
    Write-Colored Green "🎉 Installation & Configuration Successful!"
    Write-Colored Green "=================================================="
    Write-Host "📁 Installation Directory: $InstallDir"
    Write-Host '🚀 Unified command: media-downloader "share text or link"'
    Write-Host "🔎 The platform is detected automatically from the link."
    Write-Host ""
    Write-Colored Yellow "🔔 Note:"
    if ($needRestart) {
        Write-Host "1. 💡 Open a new terminal window (or log out/in) to apply the PATH change!"
        Write-Host '2. Then run media-downloader "share text or link" anywhere in the terminal.'
    } else {
        Write-Host '1. Run media-downloader "share text or link" anywhere in the terminal.'
    }
}
Write-Host "=================================================="
