[CmdletBinding()]
param(
    [int]$Seed = 20260807,
    [string]$OutputRoot = 'output\_demos\python\python-single-figure-suite-v2',
    [switch]$VerifyDeterminism
)

$ErrorActionPreference = 'Stop'
$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not [System.IO.Path]::IsPathRooted($OutputRoot)) {
    $OutputRoot = Join-Path $workspaceRoot $OutputRoot
}
$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)
$workspaceBoundary = [System.IO.Path]::GetFullPath($workspaceRoot).TrimEnd('\') + '\'
if (-not ($OutputRoot + '\').StartsWith($workspaceBoundary, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Python demo output must remain inside the modeling workspace: $OutputRoot"
}
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

. (Join-Path $PSScriptRoot '_environment.ps1')
$resolved = Resolve-ModelingEnvironment -RequestedName 'base' -Tier 'core'
if ($resolved.Selected.Name -ne 'base') {
    throw "Python figure demos must run in base; selected $($resolved.Selected.Name)."
}
if ($resolved.Selected.Python -notmatch '^3\.13\.') {
    throw "Python figure demos require the local Python 3.13 base environment; found $($resolved.Selected.Python)."
}

$generator = Join-Path $workspaceRoot 'src\demos\python_figure_suite.py'
$auditor = Join-Path $workspaceRoot 'scripts\audit_python_figure_suite.py'
$styleAuditor = Join-Path $workspaceRoot 'src\utils\audit_figure_style.py'

Write-Host "Generating ten Python publication figures with seed $Seed..."
$generation = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @(
    'run','--no-capture-output','-p',$resolved.Selected.Prefix,
    'python','-s',$generator,'--output-root',$OutputRoot,'--seed',[string]$Seed
) -DisableUserSite -TimeoutSeconds 1800
if ($generation.ExitCode -ne 0) { throw "Python figure generation failed with exit code $($generation.ExitCode)." }

$referenceRoot = $null
if ($VerifyDeterminism) {
    $referenceRoot = Join-Path $OutputRoot '_determinism\run-2'
    New-Item -ItemType Directory -Force -Path $referenceRoot | Out-Null
    Write-Host 'Repeating the suite for deterministic visual hashes...'
    $repeat = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @(
        'run','--no-capture-output','-p',$resolved.Selected.Prefix,
        'python','-s',$generator,'--output-root',$referenceRoot,'--seed',[string]$Seed
    ) -DisableUserSite -TimeoutSeconds 1800
    if ($repeat.ExitCode -ne 0) { throw "Python determinism run failed with exit code $($repeat.ExitCode)." }
}

$auditArguments = @(
    'run','--no-capture-output','-p',$resolved.Selected.Prefix,
    'python','-s',$auditor,'--root',$OutputRoot,'--dpi','200'
)
if ($referenceRoot) { $auditArguments += @('--reference-root',$referenceRoot) }
$audit = Invoke-CondaCommand -Conda $resolved.Conda -Arguments $auditArguments -DisableUserSite -TimeoutSeconds 1800
if ($audit.ExitCode -ne 0) { throw 'Python demo visual or determinism audit failed.' }

$styleOutput = Join-Path $OutputRoot 'figure_style_audit.json'
$styleAudit = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @(
    'run','--no-capture-output','-p',$resolved.Selected.Prefix,
    'python','-s',$styleAuditor,'--output',$styleOutput
) -DisableUserSite -TimeoutSeconds 900
if ($styleAudit.ExitCode -ne 0) { throw 'Shared figure palette audit failed.' }

Write-Host "Python single-figure suite passed: $OutputRoot"
