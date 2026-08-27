[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('verify','lookup','sync','status')]
    [string]$Action,
    [string[]]$Tags,
    [string]$Source,
    [string]$Query,
    [ValidateRange(1,50)]
    [int]$Limit = 5,
    [ValidateSet('card','module','playbook','code','all')]
    [string]$Layer = 'all',
    [string]$EnvironmentName = 'auto'
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_environment.ps1')

if ($Action -eq 'lookup' -and ($null -eq $Tags -or $Tags.Count -eq 0 -or [string]::IsNullOrWhiteSpace(($Tags -join '')))) {
    throw 'lookup requires -Tags, for example: optimization,milp'
}
if ($Action -eq 'sync' -and [string]::IsNullOrWhiteSpace($Source)) {
    throw 'sync requires -Source, for example: github-jingfeizhang-1'
}

$root = Get-ModelingRoot
$resolved = Resolve-ModelingEnvironment -RequestedName $EnvironmentName -Tier core
if ($resolved.Selected.CoreMissing.Count -gt 0) {
    throw "Selected environment lacks core packages: $($resolved.Selected.CoreMissing -join ', ')"
}

$arguments = @(
    'run', '--no-capture-output', '-p', $resolved.Selected.Prefix, 'python', '-s',
    (Join-Path $root 'src\workflow\reference_library_cli.py'), '--workspace-root', $root, $Action
)
if ($Action -eq 'lookup') {
    $arguments += @('--tags', ($Tags -join ','), '--limit', [string]$Limit, '--layer', $Layer)
    if (-not [string]::IsNullOrWhiteSpace($Query)) {
        $arguments += @('--query', $Query)
    }
}
if ($Action -eq 'sync') {
    $arguments += @('--source', $Source)
}

# The Python adapter installs the strict P1-P3 L3 playbook boundary and then
# reuses the mature reference_library implementation. It reads local source
# mappings and performs explicit sync only for the pinned algorithm source.
# It never runs repository scripts, OCR, MATLAB, or upstream example code.
# Lookup never performs network requests.
$run = Invoke-CondaCommand -Conda $resolved.Conda -Arguments $arguments -CaptureOutput -DisableUserSite
foreach ($line in @($run.Output)) { [Console]::Out.WriteLine([string]$line) }
foreach ($line in @($run.ErrorOutput)) { [Console]::Error.WriteLine([string]$line) }
exit $run.ExitCode
