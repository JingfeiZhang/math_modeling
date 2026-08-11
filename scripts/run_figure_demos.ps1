[CmdletBinding()]
param(
    [int]$Seed = 20260801,
    [string]$OutputRoot = 'output\_demos\matlab\matlab-single-figure-suite',
    [switch]$VerifyDeterminism
)

$ErrorActionPreference = 'Stop'
$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not [System.IO.Path]::IsPathRooted($OutputRoot)) {
    $OutputRoot = Join-Path $workspaceRoot $OutputRoot
}
$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

$rootForMatlab = $workspaceRoot.Replace('\','/')
$outputForMatlab = $OutputRoot.Replace('\','/')
$rootForMatlab = $rootForMatlab.Replace("'","''")
$outputForMatlab = $outputForMatlab.Replace("'","''")
$verifyValue = if ($VerifyDeterminism) { 'true' } else { 'false' }
$batch = "addpath(genpath('$rootForMatlab/matlab')); run_publication_demo_suite('$rootForMatlab','$outputForMatlab',$Seed,$verifyValue);"

Write-Host "Generating MATLAB R2026a figure fixtures..."
& (Join-Path $PSScriptRoot 'run_matlab.ps1') -Batch $batch
if ($LASTEXITCODE -ne 0) { throw "MATLAB demo generation failed with exit code $LASTEXITCODE." }

. (Join-Path $PSScriptRoot '_environment.ps1')
$resolved = Resolve-ModelingEnvironment -RequestedName 'base' -Tier 'core'
if ($resolved.Selected.Name -ne 'base') {
    throw "Demo QA must run in base; selected $($resolved.Selected.Name)."
}
$qaScript = Join-Path $workspaceRoot 'scripts\audit_demo_suite.py'
$qaResult = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @(
    'run','--no-capture-output','-p',$resolved.Selected.Prefix,'python',$qaScript,
    '--root',$OutputRoot,'--dpi','200'
) -DisableUserSite
if ($qaResult.ExitCode -ne 0) { throw "Demo PDF visual QA failed." }

$styleScript = Join-Path $workspaceRoot 'src\utils\audit_figure_style.py'
$styleOutput = Join-Path $OutputRoot 'figure_style_audit.json'
$styleResult = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @(
    'run','--no-capture-output','-p',$resolved.Selected.Prefix,'python',$styleScript,
    '--output',$styleOutput
) -DisableUserSite
if ($styleResult.ExitCode -ne 0) { throw "Figure palette audit failed." }

Write-Host "MATLAB demo suite and visual QA completed: $OutputRoot"
