$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host '==> Preparing ORIVOX Windows build environment'
if (-not (Test-Path '.venv-build')) {
    py -3.11 -m venv .venv-build
}
& .\.venv-build\Scripts\python.exe -m pip install --upgrade pip
& .\.venv-build\Scripts\python.exe -m pip install -r requirements-desktop.txt

Write-Host '==> Compiling Python sources'
& .\.venv-build\Scripts\python.exe -m compileall -q orivox desktop.py run.py

Write-Host '==> Building desktop application'
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
& .\.venv-build\Scripts\pyinstaller.exe --noconfirm --clean ORIVOX.spec

if (-not (Test-Path 'dist\ORIVOX\ORIVOX.exe')) {
    throw 'PyInstaller finished without creating dist\ORIVOX\ORIVOX.exe'
}

Write-Host '==> Creating portable package'
$PackageDir = 'dist\ORIVOX-Portable'
Remove-Item -Recurse -Force $PackageDir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $PackageDir | Out-Null
Copy-Item -Recurse 'dist\ORIVOX\*' $PackageDir
@'
HR-Presents ORIVOX

1. Install Ollama from its official installer.
2. Run: ollama pull qwen2.5:3b
3. Launch ORIVOX.exe.

ORIVOX stores user data and downloaded application models in %LOCALAPPDATA%\ORIVOX by default.
'@ | Set-Content -Encoding UTF8 "$PackageDir\README-WINDOWS.txt"

$Zip = 'dist\ORIVOX-Windows-Portable.zip'
Remove-Item -Force $Zip -ErrorAction SilentlyContinue
Compress-Archive -Path "$PackageDir\*" -DestinationPath $Zip -CompressionLevel Optimal
Write-Host "Build complete: $Zip"
