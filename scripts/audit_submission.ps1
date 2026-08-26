[CmdletBinding()]
param(
    [string]$EnvironmentName = 'auto',
    [switch]$Strict,
    [switch]$SkipPackage,
    [string]$ProjectRoot,
    [string]$WorkspaceRoot
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_environment.ps1')
$hub = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$root = if ($ProjectRoot) { [System.IO.Path]::GetFullPath($ProjectRoot) } else { $hub }
$sharedRoot = if ($WorkspaceRoot) { [System.IO.Path]::GetFullPath($WorkspaceRoot) } else { $hub }
$resolved = Resolve-ModelingEnvironment -RequestedName $EnvironmentName -Tier full
$selected = $resolved.Selected
if ($selected.CorePrefixMissing.Count -gt 0 -or -not $selected.Coverage['pypdf']) {
    throw "PDF audit requires an independent prefix with pypdf; missing: $($selected.CorePrefixMissing -join ', ')"
}

# Refresh the concise AI statement, stage summary and details PDF from the
# latest internal evidence before any formal audit. Precontest projects no-op.
& (Join-Path $PSScriptRoot 'prepare_ai_disclosure.ps1') -EnvironmentName $EnvironmentName -ProjectRoot $root -WorkspaceRoot $sharedRoot

$paperDir = Join-Path $root 'paper'
$pdf = Join-Path $root 'output\submission.pdf'
$latexAudit = Join-Path $root 'output\paper_audit.json'
$figureAudit = Join-Path $root 'output\figure_audit.json'
$visualAudit = Join-Path $root 'output\pdf_visual_audit.json'
$visualPages = Join-Path $root 'output\_verification\pdf\rendered-pages'
$packageAudit = Join-Path $root 'output\package_audit.json'
$codeParityAudit = Join-Path $root 'output\code_parity_audit.json'
$aiUsageAudit = Join-Path $root 'output\ai_usage_audit.json'
$styleAudit = Join-Path $root 'output\figure_style_audit.json'
$auditScript = Join-Path $sharedRoot 'src\utils\audit_latex.py'
$figureScript = Join-Path $sharedRoot 'src\utils\audit_figures.py'
$visualScript = Join-Path $sharedRoot 'src\utils\audit_pdf_visual.py'
$packageScript = Join-Path $sharedRoot 'src\utils\audit_package.py'
$common = @('--paper-dir', $paperDir, '--pdf', $pdf, '--output', $latexAudit, '--contest-config', (Join-Path $root 'contest.yaml'), '--require-anonymous')
$latexRun = Invoke-CondaCommand -Conda $resolved.Conda -Arguments (@('run', '--no-capture-output', '-p', $selected.Prefix, 'python', '-s', $auditScript) + $common) -DisableUserSite
$latexExit = $latexRun.ExitCode
$figureRun = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @('run', '--no-capture-output', '-p', $selected.Prefix, 'python', '-s', $figureScript, '--paper-dir', $paperDir, '--output', $figureAudit, '--min-raster-px', '1200', '--min-dpi', '400', '--strict') -DisableUserSite
$figureExit = $figureRun.ExitCode
$visualRun = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @(
    'run', '--no-capture-output', '-p', $selected.Prefix, 'python', '-s', $visualScript,
    '--pdf', $pdf, '--render-dir', $visualPages, '--output', $visualAudit, '--dpi', '300'
) -CaptureOutput -DisableUserSite
$visualExit = $visualRun.ExitCode
$styleArguments = @('run', '--no-capture-output', '-p', $selected.Prefix, 'python', '-s', (Join-Path $sharedRoot 'src\utils\audit_figure_style.py'), '--output', $styleAudit, '--project-root', $root)
if (Test-Path -LiteralPath (Join-Path $root 'paper\figure_contracts.yaml')) {
    $styleArguments += @('--manifest', (Join-Path $root 'paper\figure_contracts.yaml'), '--strict')
}
$styleRun = Invoke-CondaCommand -Conda $resolved.Conda -Arguments $styleArguments -CaptureOutput -DisableUserSite
$styleExit = $styleRun.ExitCode
$codeParityArguments = @(
    'run', '--no-capture-output', '-p', $selected.Prefix, 'python', '-s', (Join-Path $sharedRoot 'src\utils\audit_code_parity.py'),
    '--root', $root, '--paper-dir', $paperDir, '--support', (Join-Path $root 'output\supporting.zip'), '--output', $codeParityAudit
)
if ($SkipPackage) { $codeParityArguments += '--skip-support' }
$codeParityRun = Invoke-CondaCommand -Conda $resolved.Conda -Arguments $codeParityArguments -CaptureOutput -DisableUserSite
$codeParityExit = $codeParityRun.ExitCode
$aiUsageArguments = @(
    'run', '--no-capture-output', '-p', $selected.Prefix, 'python', '-s', (Join-Path $sharedRoot 'src\utils\audit_ai_usage.py'),
    '--root', $root, '--policy', (Join-Path $sharedRoot 'config\ai_usage_policy.yaml'), '--output', $aiUsageAudit
)
if ($SkipPackage) { $aiUsageArguments += '--skip-support' }
$aiUsageRun = Invoke-CondaCommand -Conda $resolved.Conda -Arguments $aiUsageArguments -CaptureOutput -DisableUserSite
$aiUsageExit = $aiUsageRun.ExitCode
if ($SkipPackage) {
    $packageExit = 0
} elseif (Test-Path -LiteralPath (Join-Path $root 'output\supporting.zip')) {
    $packageRun = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @(
        'run', '--no-capture-output', '-p', $selected.Prefix, 'python', '-s', $packageScript,
        '--source', (Join-Path $root 'output\supporting.zip'), '--output', $packageAudit, '--strict'
    ) -CaptureOutput -DisableUserSite
    $packageExit = $packageRun.ExitCode
} else {
    $packageExit = 1
}
$submissionArgs = @('run', '--no-capture-output', '-p', $selected.Prefix, 'python', '-s', (Join-Path $sharedRoot 'src\utils\audit_submission.py'), '--root', $root)
if ($Strict) { $submissionArgs += '--strict' }
if ($SkipPackage) { $submissionArgs += '--skip-package' }
$submissionRun = Invoke-CondaCommand -Conda $resolved.Conda -Arguments $submissionArgs -DisableUserSite
$submissionExit = $submissionRun.ExitCode
Write-Host "Audit exits: latex=$latexExit figures=$figureExit submission=$submissionExit"
Write-Host "Audit exits: visual=$visualExit style=$styleExit codeParity=$codeParityExit aiUsage=$aiUsageExit package=$packageExit"
if ($latexExit -ne 0 -or $figureExit -ne 0 -or $visualExit -ne 0 -or $styleExit -ne 0 -or $codeParityExit -ne 0 -or $aiUsageExit -ne 0 -or $packageExit -ne 0 -or $submissionExit -ne 0) { exit 1 }
exit 0
