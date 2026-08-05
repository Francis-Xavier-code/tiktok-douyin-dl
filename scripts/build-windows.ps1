$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PythonProject = Join-Path $RepoRoot "python"
$GuiEntry = Join-Path $RepoRoot "apps\windows\gui\gui_downloader.py"
$Icon = Join-Path $RepoRoot "assets\app.ico"
$BrowserCache = Join-Path $RepoRoot "ms-playwright"
$Version = if ([string]::IsNullOrWhiteSpace($env:APP_VERSION)) { "1.8.2" } else { $env:APP_VERSION }

python -m pip install --upgrade pip
python -m pip install -e "$PythonProject[windows]" pyinstaller

$env:PLAYWRIGHT_BROWSERS_PATH = "$env:USERPROFILE\.cache\ms-playwright"
python -m playwright install chromium
if (Test-Path $BrowserCache) {
    Remove-Item $BrowserCache -Recurse -Force
}
Copy-Item $env:PLAYWRIGHT_BROWSERS_PATH $BrowserCache -Recurse

$StealthPath = python -c "import pathlib, playwright_stealth; print(pathlib.Path(playwright_stealth.__file__).parent)"
python -m PyInstaller `
    --noconfirm `
    --onedir `
    --noconsole `
    --icon $Icon `
    --name MediaDownloader_GUI `
    --paths (Join-Path $PythonProject "src") `
    --hidden-import media_downloader.platforms.douyin `
    --hidden-import media_downloader.platforms.tiktok `
    --hidden-import media_downloader.i18n.catalogs `
    --hidden-import auto_updater `
    --hidden-import sv_ttk `
    --add-data "$StealthPath\js;playwright_stealth\js" `
    --collect-all playwright `
    --collect-all PIL `
    --collect-all sv_ttk `
    --distpath (Join-Path $RepoRoot "dist") `
    --workpath (Join-Path $RepoRoot "build") `
    --specpath (Join-Path $RepoRoot "build") `
    --clean `
    $GuiEntry

python -m PyInstaller `
    --noconfirm `
    --onefile `
    --name media-downloader `
    --paths (Join-Path $PythonProject "src") `
    --hidden-import media_downloader.platforms.douyin `
    --hidden-import media_downloader.platforms.tiktok `
    --hidden-import media_downloader.i18n.catalogs `
    --add-data "$StealthPath\js;playwright_stealth\js" `
    --collect-all playwright `
    --collect-all PIL `
    --collect-all sv_ttk `
    --distpath (Join-Path $RepoRoot "dist") `
    --workpath (Join-Path $RepoRoot "build\media-downloader") `
    --specpath (Join-Path $RepoRoot "build") `
    --clean `
    (Join-Path $PythonProject "src\media_downloader\cli.py")

$Iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $Iscc)) {
    throw "Inno Setup 6 was not found at $Iscc"
}
& $Iscc "/DAppVersion=$Version" (Join-Path $RepoRoot "apps\windows\installer\installer.iss")
