[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('inspect','preview','normalize','verify')]
    [string]$Action
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_environment.ps1')
$root = Get-ModelingRoot
$conda = Get-CondaExecutable
$resolved = Resolve-ModelingEnvironment -RequestedName 'base' -Tier 'core'
$script = Join-Path $root 'src\utils\workspace_layout.py'
$python = Join-Path $resolved.Selected.Prefix 'python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw "Selected Python executable is missing: $python" }
$lock = Enter-CondaLock -Conda $conda -TimeoutSeconds 900
$previousUserSite = [Environment]::GetEnvironmentVariable('PYTHONNOUSERSITE', 'Process')
try {
    [Environment]::SetEnvironmentVariable('PYTHONNOUSERSITE', '1', 'Process')
    & $python -E -s $script --root $root --action $Action
    $exitCode = $LASTEXITCODE
}
finally {
    [Environment]::SetEnvironmentVariable('PYTHONNOUSERSITE', $previousUserSite, 'Process')
    Exit-CondaLock -Lock $lock
}
if ($exitCode -ne 0) { throw "Workspace action '$Action' failed with exit code $exitCode." }
