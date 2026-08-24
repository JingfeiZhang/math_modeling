[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('verify','lookup','status')]
    [string]$Action,
    [string]$Tags,
    [ValidateRange(1,50)]
    [int]$Limit = 5,
    [ValidateSet('card','module','playbook','all')]
    [string]$Layer = 'all',
    [string]$EnvironmentName = 'auto'
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_environment.ps1')

if ($Action -eq 'lookup' -and [string]::IsNullOrWhiteSpace($Tags)) {
    throw 'lookup requires -Tags, for example: optimization,milp'
}

$root = Get-ModelingRoot
$resolved = Resolve-ModelingEnvironment -RequestedName $EnvironmentName -Tier core
if ($resolved.Selected.CoreMissing.Count -gt 0) {
    throw "Selected environment lacks core packages: $($resolved.Selected.CoreMissing -join ', ')"
}

$arguments = @(
    'run', '--no-capture-output', '-p', $resolved.Selected.Prefix, 'python', '-s',
    (Join-Path $root 'src\workflow\reference_library.py'), '--workspace-root', $root, $Action
)
if ($Action -eq 'lookup') {
    $arguments += @('--tags', $Tags, '--limit', [string]$Limit, '--layer', $Layer)
}

# The Python module only reads the local source mapping and PDF bytes. It never
# runs OCR, network requests, MATLAB, or upstream example code.
$run = Invoke-CondaCommand -Conda $resolved.Conda -Arguments $arguments -DisableUserSite
exit $run.ExitCode
