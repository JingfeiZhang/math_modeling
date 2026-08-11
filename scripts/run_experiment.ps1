[CmdletBinding()]
param(
    [string]$ExperimentId = 'demo',
    [int]$Seed = 20260801,
    [string]$OutputRoot,
    [string]$EnvironmentName = 'auto',
    [string]$Config,
    [string]$Question,
    [string]$ProjectRoot,
    [string]$WorkspaceRoot
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_environment.ps1')
. (Join-Path $PSScriptRoot '_matlab.ps1')
$hub = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$root = if ($ProjectRoot) { [System.IO.Path]::GetFullPath($ProjectRoot) } else { $hub }
$sharedRoot = if ($WorkspaceRoot) { [System.IO.Path]::GetFullPath($WorkspaceRoot) } else { $hub }
$rootPrefix = $root.TrimEnd('\') + '\'
$resolved = Resolve-ModelingEnvironment -RequestedName $EnvironmentName -Tier core
$selected = $resolved.Selected
if ($selected.CoreMissing.Count -gt 0) { throw "Selected environment lacks core packages: $($selected.CoreMissing -join ', ')" }

if (-not $Config) {
    $targetRoot = if ($OutputRoot) { [System.IO.Path]::GetFullPath($OutputRoot) } else { Join-Path $root 'experiments' }
    if (-not $targetRoot.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase) -and $targetRoot -ne $root.TrimEnd('\')) {
        throw "Experiment output must remain inside the selected project root: $targetRoot"
    }
    New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null
    Write-Host "Experiment environment: $($selected.Name)"
    $result = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @(
        'run', '--no-capture-output', '-p', $selected.Prefix, 'python', '-s', (Join-Path $sharedRoot 'src\modeling\run_demo.py'),
        '--experiment-id', $ExperimentId, '--seed', "$Seed", '--output-root', $targetRoot
    )
    exit $result.ExitCode
}

$configPath = (Resolve-Path -LiteralPath $Config).Path
$resolveRun = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @(
    'run','--no-capture-output','-p',$selected.Prefix,'python','-s',(Join-Path $sharedRoot 'src\workflow\competition_workflow.py'),
    '--root',$root,'--workspace-root',$sharedRoot,'resolve-run-config','--config',$configPath
) -CaptureOutput
if ($resolveRun.ExitCode -ne 0) { throw "Invalid experiment configuration: $($resolveRun.ErrorOutput -join [Environment]::NewLine)" }
$runConfig = ($resolveRun.Output -join [Environment]::NewLine) | ConvertFrom-Json
if ($Question -and $Question -ne $runConfig.question) { throw "Question mismatch: command=$Question config=$($runConfig.question)" }

$ExperimentId = [string]$runConfig.experiment_id
$Seed = [int]$runConfig.seed
$runner = [string]$runConfig.runner_path
$targetRelative = [string]$runConfig.output_root
$targetAbsolute = [System.IO.Path]::GetFullPath((Join-Path $root $targetRelative))
New-Item -ItemType Directory -Force -Path $targetAbsolute | Out-Null
$startedAt = [DateTimeOffset]::UtcNow
$clock = [System.Diagnostics.Stopwatch]::StartNew()
$commandForManifest = @()
$exitCode = 1
$matlabInstallation = $null

if ($runConfig.engine -eq 'python') {
    $runnerAbsolute = [System.IO.Path]::GetFullPath((Join-Path $root $runner))
    $runnerArguments = @('run','--no-capture-output','-p',$selected.Prefix,'python','-s',$runnerAbsolute,'--experiment-id',$ExperimentId,'--seed',"$Seed",'--output-root',$targetAbsolute)
    foreach ($argument in @($runConfig.arguments)) { $runnerArguments += [string]$argument }
    if ($runConfig.run_mode -eq 'paper-evidence') {
        foreach ($argument in @($runConfig.diagnostic_arguments)) { $runnerArguments += [string]$argument }
    }
    $commandForManifest = @('conda') + $runnerArguments
    Write-Host "Experiment environment: $($selected.Name)"
    $runResult = Invoke-CondaCommand -Conda $resolved.Conda -Arguments $runnerArguments
    $exitCode = $runResult.ExitCode
} else {
    $configuredMatlabRoot = Get-ConfiguredMatlabRoot -WorkspaceRoot $root
    $matlabInstallation = Resolve-MatlabInstallation -PreferredRoot $configuredMatlabRoot -StrictPreferred:([bool]$configuredMatlabRoot)
    $commandForManifest = @('scripts/run_matlab.ps1','-Script',$runner,'-MatlabRoot',$matlabInstallation.Root)
    & (Join-Path $PSScriptRoot 'run_matlab.ps1') -Script (Join-Path $root $runner) -MatlabRoot $matlabInstallation.Root
    $exitCode = $LASTEXITCODE
}

$clock.Stop()
$matlabReportedVersion = $null
if ($matlabInstallation) {
    $matlabReportPath = Join-Path $root 'output\matlab_environment.json'
    if (Test-Path -LiteralPath $matlabReportPath) {
        try {
            $matlabReport = Get-Content -LiteralPath $matlabReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $reportedRoot = [System.IO.Path]::GetFullPath([string]$matlabReport.matlab.root).TrimEnd('\')
            if ($reportedRoot -eq $matlabInstallation.Root.TrimEnd('\')) {
                $matlabReportedVersion = [string]$matlabReport.matlab.version
            }
        } catch { $matlabReportedVersion = $null }
    }
}
$environment = @{
    conda_name = $selected.Name
    conda_prefix = $selected.Prefix
    python = $selected.Python
    matlab_root = if ($matlabInstallation) { $matlabInstallation.Root } else { $null }
    matlab_release = if ($matlabInstallation) { $matlabInstallation.Release } else { $null }
    matlab_version = if ($matlabReportedVersion) { $matlabReportedVersion } elseif ($matlabInstallation) { $matlabInstallation.ExecutableVersion } else { $null }
    matlab_executable_version = if ($matlabInstallation) { $matlabInstallation.ExecutableVersion } else { $null }
}
$recordArguments = @(
    'run','--no-capture-output','-p',$selected.Prefix,'python','-s',(Join-Path $sharedRoot 'src\workflow\competition_workflow.py'),'--root',$root,'--workspace-root',$sharedRoot,
    'record-run','--config',$configPath,'--command-json',($commandForManifest | ConvertTo-Json -Compress),
    '--environment-json',($environment | ConvertTo-Json -Compress),'--started-at',$startedAt.ToString('o'),
    '--duration',$clock.Elapsed.TotalSeconds.ToString([System.Globalization.CultureInfo]::InvariantCulture)
)
if ($exitCode -eq 0) { $recordArguments += '--success' }
$recordRun = Invoke-CondaCommand -Conda $resolved.Conda -Arguments $recordArguments
if ($recordRun.ExitCode -ne 0) { throw 'Run manifest recording failed.' }
exit $exitCode
