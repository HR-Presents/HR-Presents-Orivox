$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
if (Test-Path release) { Remove-Item release -Recurse -Force }
New-Item -ItemType Directory -Force release | Out-Null

python -m PyInstaller --clean --noconfirm ORIVOX.spec

if (-not (Test-Path 'dist\ORIVOX.exe')) {
  throw 'PyInstaller did not produce dist\ORIVOX.exe'
}

$inno = @(
  "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
  "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $inno) {
  throw 'Inno Setup 6 was not found. Install it or run: choco install innosetup -y'
}

& $inno 'installer\orivox.iss'

$installer = Get-ChildItem release\ORIVOX-v*-Windows-Setup.exe | Select-Object -First 1
if (-not $installer) { throw 'Installer was not produced' }
Get-FileHash $installer.FullName -Algorithm SHA256 | Format-List
Write-Host "Built $($installer.FullName)"
