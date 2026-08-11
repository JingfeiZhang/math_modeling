[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('list','scaffold','status','preflight')]
    [string]$Action,
    [string]$Project,
    [switch]$Force,
    [string]$EnvironmentName = 'auto'
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_environment.ps1')
$hub = Get-ModelingRoot
$resolved = Resolve-ModelingEnvironment -RequestedName $EnvironmentName -Tier core
$selected = $resolved.Selected
if ($selected.CoreMissing.Count -gt 0) { throw "Selected environment lacks core packages: $($selected.CoreMissing -join ', ')" }
$arguments = @(
    'run','--no-capture-output','-p',$selected.Prefix,'python','-s',
    (Join-Path $hub 'src\workflow\project_workspace.py'), '--root', $hub, '--action', $Action
)
if ($Project) { $arguments += @('--project', $Project) }
if ($Force) { $arguments += '--force' }
$run = Invoke-CondaCommand -Conda $resolved.Conda -Arguments $arguments -DisableUserSite
exit $run.ExitCode

