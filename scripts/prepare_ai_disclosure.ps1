[CmdletBinding()]
param(
    [string]$EnvironmentName = 'auto',
    [string]$ProjectRoot,
    [string]$WorkspaceRoot
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_environment.ps1')
$hub = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$root = if ($ProjectRoot) { [System.IO.Path]::GetFullPath($ProjectRoot) } else { $hub }
$sharedRoot = if ($WorkspaceRoot) { [System.IO.Path]::GetFullPath($WorkspaceRoot) } else { $hub }
$resolved = Resolve-ModelingEnvironment -RequestedName $EnvironmentName -Tier core
$selected = $resolved.Selected
if ($selected.CoreMissing.Count -gt 0) {
    throw "AI disclosure preparation requires core Python packages: $($selected.CoreMissing -join ', ')"
}
$receipt = Join-Path $root 'output\ai\disclosure_prepare.json'
$run = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @(
    'run','--no-capture-output','-p',$selected.Prefix,'python','-s',(Join-Path $sharedRoot 'src\utils\prepare_ai_disclosure.py'),
    '--root',$root,
    '--policy',(Join-Path $sharedRoot 'config\ai_usage_policy.yaml'),
    '--compile-details',
    '--output',$receipt
) -DisableUserSite
if ($run.ExitCode -ne 0) { throw 'AI disclosure preparation failed.' }
Write-Host "AI disclosure receipt: $receipt"
