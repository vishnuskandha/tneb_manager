<#
PowerShell build helper for creating a single-file executable with PyInstaller.
Usage: Run from the project root in PowerShell (pwsh) with appropriate permissions.
This script will:
 - create a virtual env at .venv
 - install dependencies from requirements.txt plus pyinstaller
 - run PyInstaller producing dist\tneb_manager.exe

Notes:
 - PyInstaller's --add-data on Windows uses a semicolon separator: "SRC;DEST"
 - This script includes the `data` folder to ensure config and backups are available.
 - If you want a console app instead of GUI windowed app, remove --windowed.
#>

set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Write-Host "Project root: $projRoot"
Push-Location $projRoot

# Create venv
if (-Not (Test-Path -Path ".venv")) {
    Write-Host "Creating virtual environment .venv..."
    python -m venv .venv
} else {
    Write-Host ".venv already exists"
}

# Activate venv for the current pwsh session
$activate = Join-Path -Path $projRoot -ChildPath ".venv\Scripts\Activate.ps1"
if (Test-Path $activate) {
    Write-Host "Activating virtual environment"
    & $activate
} else {
    Write-Warning "Activation script not found; ensure you have Python and venv support installed."
}

# Upgrade pip and install requirements + pyinstaller
Write-Host "Installing dependencies (this may take a minute)..."
python -m pip install --upgrade pip
if (Test-Path "requirements.txt") {
    python -m pip install -r requirements.txt
}
python -m pip install pyinstaller

# Build options
$exeName = "tneb_manager"
$mainScript = "main.py"
# Include data directory (config, backups, etc.) - on Windows src;dest
$addDataArg = "data;data"
# Hidden imports that PyInstaller often misses (tkcalendar, pandas internals)
$hiddenImports = @("tkcalendar")

# Construct argument list for PyInstaller safely
$piArgs = @(
    '--noconfirm',
    '--onefile',
    '--windowed',
    '--name', $exeName,
    '--version-file', 'version_info.txt',
    '--add-data', $addDataArg
)

foreach ($hi in $hiddenImports) {
    $piArgs += '--hidden-import'
    $piArgs += $hi
}

# Finally add the entry script
$piArgs += $mainScript

Write-Host "Running PyInstaller with arguments:`n  $($piArgs -join ' ')"

# Invoke pyinstaller executable from the venv if available, otherwise rely on PATH
$pyinstallerExe = Join-Path -Path $projRoot -ChildPath ".venv\Scripts\pyinstaller.exe"
if (-Not (Test-Path $pyinstallerExe)) {
    $pyinstallerExe = "pyinstaller"
}

# Use Start-Process to preserve proper argument quoting and capture exit
$proc = Start-Process -FilePath $pyinstallerExe -ArgumentList $piArgs -NoNewWindow -Wait -PassThru
if ($proc.ExitCode -eq 0) {
    $outPath = Join-Path $projRoot "dist\$exeName.exe"
    if (Test-Path $outPath) {
        Write-Host "Build succeeded: dist\$exeName.exe"
    } else {
        Write-Warning "PyInstaller reported success but the expected exe was not found at $outPath"
    }
} else {
    Write-Error "PyInstaller failed with exit code $($proc.ExitCode). Check the output above for details."
}

Pop-Location
