$ErrorActionPreference = 'Stop'
$ProgressPreference = 'Continue'
Set-Location (Split-Path -Parent $PSScriptRoot)

function Header($text) {
  Write-Host ""
  Write-Host "============================================================" -ForegroundColor Cyan
  Write-Host " ORIVOX - $text" -ForegroundColor Cyan
  Write-Host "============================================================" -ForegroundColor Cyan
}

function Step($text) { Write-Host "`n>> $text" -ForegroundColor Yellow }
function Good($text) { Write-Host "[OK] $text" -ForegroundColor Green }
function Info($text) { Write-Host "[INFO] $text" -ForegroundColor Gray }

Header 'Local setup and launch'
Write-Host 'This window stays open so you can see exactly what ORIVOX is installing.'
Write-Host 'First launch can take time because Python packages and the local AI model are downloaded.'
Write-Host 'Later launches reuse everything already installed.'

# ---------- Python ----------
Step 'Checking Python 3.11+'
$python = $null
$pythonMode = 'exe'
$pythonCandidates = @(
  "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
)
foreach ($candidate in $pythonCandidates) {
  if (Test-Path $candidate) { $python = $candidate; break }
}
if (-not $python) {
  $cmd = Get-Command py -ErrorAction SilentlyContinue
  if ($cmd) {
    try {
      & py -3.11 -c "import sys; assert sys.version_info >= (3,11)" 2>$null
      if ($LASTEXITCODE -eq 0) { $python = 'py'; $pythonMode = 'py' }
    } catch {}
  }
}
if (-not $python) {
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if ($cmd) {
    try {
      & python -c "import sys; assert sys.version_info >= (3,11)" 2>$null
      if ($LASTEXITCODE -eq 0) { $python = $cmd.Source; $pythonMode = 'exe' }
    } catch {}
  }
}

if (-not $python) {
  Step 'Python 3.11 is not installed. ORIVOX will install it for your user account.'
  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if (-not $winget) { throw 'Python 3.11+ is required and Windows Package Manager (winget) is unavailable. Install Python 3.11 from python.org, then run Start ORIVOX.bat again.' }
  & winget install --id Python.Python.3.11 -e --scope user --accept-source-agreements --accept-package-agreements
  if ($LASTEXITCODE -ne 0) { throw 'Python installation failed.' }
  $python = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
  $pythonMode = 'exe'
  if (-not (Test-Path $python)) { throw 'Python installed but executable was not found. Reopen Start ORIVOX.bat.' }
}
Good 'Python is ready.'

function Run-Python([string[]]$Arguments) {
  if ($pythonMode -eq 'py') { & py -3.11 @Arguments }
  else { & $python @Arguments }
  if ($LASTEXITCODE -ne 0) { throw "Python command failed: $($Arguments -join ' ')" }
}

# ---------- venv / requirements ----------
$venvPython = Join-Path $PWD '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
  Step 'Creating private ORIVOX Python environment (.venv)'
  Run-Python @('-m','venv','.venv')
}
Good 'Private Python environment is ready.'

$reqHash = (Get-FileHash 'requirements.txt' -Algorithm SHA256).Hash
$marker = Join-Path $PWD '.venv\.orivox-requirements.sha256'
$installedHash = if (Test-Path $marker) { (Get-Content $marker -Raw).Trim() } else { '' }
if ($installedHash -ne $reqHash) {
  Step 'Installing / updating ORIVOX requirements'
  Info 'You will see pip download and install progress below.'
  & $venvPython -m pip install --upgrade pip
  if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }
  & $venvPython -m pip install --progress-bar on -r requirements.txt
  if ($LASTEXITCODE -ne 0) { throw 'ORIVOX dependency installation failed.' }
  Set-Content -Path $marker -Value $reqHash -Encoding ASCII
} else {
  Good 'Python requirements are already installed; skipping download.'
}

# ---------- Ollama ----------
Step 'Checking Ollama local AI runtime'
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
$ollamaExe = if ($ollamaCmd) { $ollamaCmd.Source } else { $null }
if (-not $ollamaExe) {
  $known = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
  if (Test-Path $known) { $ollamaExe = $known }
}
if (-not $ollamaExe) {
  Info 'Ollama is not installed. ORIVOX will install it now.'
  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if (-not $winget) { throw 'Ollama is required and winget is unavailable. Install Ollama from ollama.com, then run Start ORIVOX.bat again.' }
  & winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
  if ($LASTEXITCODE -ne 0) { throw 'Ollama installation failed.' }
  $known = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
  if (Test-Path $known) { $ollamaExe = $known }
  if (-not $ollamaExe) {
    $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaCmd) { $ollamaExe = $ollamaCmd.Source }
  }
  if (-not $ollamaExe) { throw 'Ollama installed but was not found. Reopen Start ORIVOX.bat.' }
}
Good 'Ollama is installed.'

$ollamaReady = $false
try { Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2 | Out-Null; $ollamaReady = $true } catch {}
if (-not $ollamaReady) {
  Step 'Starting Ollama local service'
  Start-Process -FilePath $ollamaExe -ArgumentList 'serve' -WindowStyle Hidden | Out-Null
  for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try { Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2 | Out-Null; $ollamaReady = $true; break } catch {}
  }
}
if (-not $ollamaReady) { throw 'Ollama could not start on http://127.0.0.1:11434.' }
Good 'Ollama service is running locally.'

# ---------- Qwen model ----------
$model = if ($env:ORIVOX_LLM_MODEL) { $env:ORIVOX_LLM_MODEL } else { 'qwen2.5:3b' }
Step "Checking local AI model: $model"
$modelPresent = $false
try {
  $tags = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5
  foreach ($m in $tags.models) {
    if ($m.name -eq $model -or $m.model -eq $model) { $modelPresent = $true; break }
  }
} catch {}

if (-not $modelPresent) {
  Header 'First-time AI model download'
  Write-Host "Model: $model" -ForegroundColor White
  Write-Host 'Ollama will now show download layers, percentage, downloaded size, total size and speed.' -ForegroundColor White
  Write-Host 'This is the large first-time download that can take several minutes depending on your internet.' -ForegroundColor White
  Write-Host 'Do NOT close this terminal while the pull is running.' -ForegroundColor Yellow
  Write-Host ''
  & $ollamaExe pull $model
  if ($LASTEXITCODE -ne 0) { throw "Failed to download AI model $model." }
  Good "AI model $model is downloaded and ready."
} else {
  Good "AI model $model is already installed; skipping download."
}

# ---------- Launch ----------
Header 'Starting local ORIVOX website'
$port = if ($env:ORIVOX_PORT) { $env:ORIVOX_PORT } else { '8765' }
$url = "http://127.0.0.1:$port"
Write-Host "Local address: $url" -ForegroundColor Green
Write-Host 'Keep this terminal open while using ORIVOX. Press Ctrl+C here to stop the server.'

$server = Start-Process -FilePath $venvPython -ArgumentList @('run.py') -PassThru -NoNewWindow
$opened = $false
for ($i = 0; $i -lt 60; $i++) {
  if ($server.HasExited) { throw "ORIVOX server exited with code $($server.ExitCode)." }
  Start-Sleep -Milliseconds 750
  try {
    $health = Invoke-RestMethod -Uri "$url/api/health" -TimeoutSec 2
    if ($health.ok) { Start-Process $url; $opened = $true; break }
  } catch {}
}
if (-not $opened) { throw "ORIVOX did not become ready at $url." }
Good "ORIVOX is running at $url"
Wait-Process -Id $server.Id
