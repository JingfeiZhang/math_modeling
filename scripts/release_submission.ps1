[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('seal','verify')]
    [string]$Action,
    [string]$EnvironmentName = 'auto',
    [switch]$RequireOperatorConfirmation,
    [string]$ProjectRoot,
    [string]$WorkspaceRoot
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_environment.ps1')
$hub = Get-ModelingRoot
$root = if ($ProjectRoot) { [System.IO.Path]::GetFullPath($ProjectRoot) } else { $hub }
$sharedRoot = if ($WorkspaceRoot) { [System.IO.Path]::GetFullPath($WorkspaceRoot) } else { $hub }
$resolved = Resolve-ModelingEnvironment -RequestedName $EnvironmentName -Tier full
$selected = $resolved.Selected
if ($selected.CorePrefixMissing.Count -gt 0 -or $selected.ExtendedMissing.Count -gt 0) {
    throw "Release tasks require the independent full environment; missing: $((@($selected.CorePrefixMissing) + @($selected.ExtendedMissing)) -join ', ')"
}
if ($Action -eq 'seal') {
    & (Join-Path $PSScriptRoot 'audit_submission.ps1') -EnvironmentName $selected.Prefix -Strict -ProjectRoot $root -WorkspaceRoot $sharedRoot
    if ($LASTEXITCODE -ne 0) { throw 'Submission audit failed; release was not sealed.' }
}
$arguments = @(
    'run','--no-capture-output','-p',$selected.Prefix,'python','-s',
    (Join-Path $sharedRoot 'src\utils\release_submission.py'),'--root',$root,'--workspace-root',$sharedRoot,'--action',$Action
)
if ($RequireOperatorConfirmation) { $arguments += '--require-confirmations' }
$run = Invoke-CondaCommand -Conda $resolved.Conda -Arguments $arguments -DisableUserSite
exit $run.ExitCode
