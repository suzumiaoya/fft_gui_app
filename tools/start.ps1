param([switch]$CheckOnly)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $PSScriptRoot 'start_app.py'
$candidates = [System.Collections.Generic.List[string]]::new()
$candidates.Add((Join-Path $projectRoot '.venv\Scripts\python.exe'))
$candidates.Add((Join-Path $projectRoot '.venv\python.exe'))

# Query the Windows Python launcher, including installations outside PATH.
$py = Get-Command py.exe -ErrorAction SilentlyContinue
if ($py) {
    $installed = & $py.Source -0p 2>$null
    foreach ($line in $installed) {
        if ("$line" -match '([A-Za-z]:\\.*?python(?:\d+(?:\.\d+)*)?\.exe)\s*$') {
            $candidates.Add($Matches[1])
        }
    }
}
foreach ($name in @('python.exe', 'python3.exe')) {
    foreach ($command in @(Get-Command $name -All -ErrorAction SilentlyContinue)) {
        if ($command.Source -and $command.Source -notlike '*\WindowsApps\*') {
            $candidates.Add($command.Source)
        }
    }
}

# Conda records custom installation/environment paths even when it is not on PATH.
if ($env:CONDA_PREFIX) { $candidates.Add((Join-Path $env:CONDA_PREFIX 'python.exe')) }
$condaEnvironments = Join-Path $env:USERPROFILE '.conda\environments.txt'
if (Test-Path -LiteralPath $condaEnvironments) {
    foreach ($environment in Get-Content -LiteralPath $condaEnvironments) {
        if ($environment.Trim()) {
            $candidates.Add((Join-Path $environment.Trim() 'python.exe'))
        }
    }
}

try {
    $selected = $null
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        Write-Host "Checking Python: $candidate"
        & $candidate $launcher --probe
        if ($LASTEXITCODE -eq 0) {
            $selected = $candidate
            break
        }
    }
    if (-not $selected) {
        throw 'No compatible Python found. Install Python 3.13 or newer with Tcl/Tk and pip from https://www.python.org/downloads/ and enable the Python launcher or Add Python to PATH, then retry.'
    }
    $launchArguments = @($launcher)
    if ($CheckOnly) { $launchArguments += '--check-only' }
    $pythonHome = Split-Path -Parent $selected
    if (Test-Path -LiteralPath (Join-Path $pythonHome 'conda-meta')) {
        $env:PATH = "$pythonHome;$pythonHome\Library\bin;$pythonHome\Scripts;$env:PATH"
    }
    & $selected @launchArguments
    exit $LASTEXITCODE
} catch {
    Write-Host "Startup failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
