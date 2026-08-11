[CmdletBinding()]
param(
    [string]$EnvironmentName = 'auto',
    [ValidateSet('core','full')][string]$Tier = 'core',
    [switch]$NoAggregateReport
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_environment.ps1')
. (Join-Path $PSScriptRoot '_matlab.ps1')
$root = Get-ModelingRoot
$conda = Get-CondaExecutable
$requirementsPath = Join-Path $root 'config\environment_requirements.json'
$report = Join-Path $root 'output\environment.json'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $report) | Out-Null

function Invoke-EnvironmentProbe {
    param([Parameter(Mandatory)]$Selection, [Parameter(Mandatory)][ValidateSet('core','full')][string]$ProbeTier)
    $temp = Join-Path ([System.IO.Path]::GetTempPath()) "mathmodel-env-$PID-$ProbeTier.json"
    try {
        $env:MATHMODEL_SELECTED_ENV = $Selection.Name
        $env:MATHMODEL_SELECTED_PREFIX = $Selection.Prefix
        $result = Invoke-CondaCommand -Conda $conda -Arguments @(
            'run', '--no-capture-output', '-p', $Selection.Prefix, 'python', '-E', '-s',
            'src\utils\verify_env.py', '--tier', $ProbeTier,
            '--requirements', 'config\environment_requirements.json', '--json', $temp
        ) -CaptureOutput
        if (-not (Test-Path -LiteralPath $temp)) { throw "Environment probe did not create a report for $ProbeTier." }
        $payload = Get-Content -LiteralPath $temp -Raw -Encoding UTF8 | ConvertFrom-Json
        $payload | Add-Member -NotePropertyName exit_code -NotePropertyValue $result.ExitCode -Force
        return $payload
    } finally {
        Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
    }
}

$coreResolved = Resolve-ModelingEnvironment -RequestedName $EnvironmentName -Tier core
$fullResolved = Resolve-ModelingEnvironment -RequestedName $EnvironmentName -Tier full
$coreProbe = Invoke-EnvironmentProbe -Selection $coreResolved.Selected -ProbeTier core
$fullProbe = Invoke-EnvironmentProbe -Selection $fullResolved.Selected -ProbeTier full
$configuredMatlabRoot = Get-ConfiguredMatlabRoot -WorkspaceRoot $root
$matlabInstallation = $null
$matlabResolutionError = $null
try {
    $matlabInstallation = Resolve-MatlabInstallation -PreferredRoot $configuredMatlabRoot -StrictPreferred:([bool]$configuredMatlabRoot)
} catch {
    $matlabResolutionError = $_.Exception.Message
}
$matlabSmokePath = Join-Path $root 'output\matlab_environment.json'
$matlabSmoke = $null
if (Test-Path -LiteralPath $matlabSmokePath) {
    try { $matlabSmoke = Get-Content -LiteralPath $matlabSmokePath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $matlabSmoke = $null }
}
$matlabSmokeMatches = $false
if ($matlabInstallation -and $matlabSmoke -and $matlabSmoke.matlab.root) {
    try {
        $matlabSmokeMatches = [System.IO.Path]::GetFullPath([string]$matlabSmoke.matlab.root).TrimEnd('\') -eq $matlabInstallation.Root.TrimEnd('\')
    } catch { $matlabSmokeMatches = $false }
}
$candidateMap = @{}
foreach ($candidate in $coreResolved.Candidates + $fullResolved.Candidates) {
    $candidateMap[$candidate.Prefix.ToLowerInvariant()] = $candidate
}
$candidates = @($candidateMap.Values | Sort-Object Name,Prefix | ForEach-Object {
    [ordered]@{
        name = $_.Name; prefix = $_.Prefix; python = $_.Python; is_base = $_.IsBase
        core_score = $_.CoreScore; full_score = $_.FullScore
        core_missing = @($_.CoreMissing); extended_missing = @($_.ExtendedMissing)
    }
})
$snapshot = [ordered]@{
    schema_version = 2
    policy = 'existing_first'
    conda_executable = $conda
    selection = [ordered]@{
        core = [ordered]@{ name = $coreResolved.Selected.Name; prefix = $coreResolved.Selected.Prefix; python = $coreResolved.Selected.Python }
        full = [ordered]@{ name = $fullResolved.Selected.Name; prefix = $fullResolved.Selected.Prefix; python = $fullResolved.Selected.Python }
    }
    tiers = [ordered]@{ core = $coreProbe; full = $fullProbe }
    candidates = $candidates
    matlab = [ordered]@{
        available = [bool]$matlabInstallation
        configured_root = $configuredMatlabRoot
        root = if ($matlabInstallation) { $matlabInstallation.Root } else { $null }
        path = if ($matlabInstallation) { $matlabInstallation.Executable } else { $null }
        release = if ($matlabInstallation) { $matlabInstallation.Release } else { $null }
        executable_version = if ($matlabInstallation) { $matlabInstallation.ExecutableVersion } else { $null }
        reported_version = if ($matlabSmokeMatches) { [string]$matlabSmoke.matlab.version } else { $null }
        discovery_source = if ($matlabInstallation) { $matlabInstallation.Source } else { $null }
        resolution_error = $matlabResolutionError
        smoke_report = [ordered]@{
            path = if (Test-Path -LiteralPath $matlabSmokePath) { $matlabSmokePath } else { $null }
            matches_installation = $matlabSmokeMatches
            required_checks_passed = if ($matlabSmokeMatches) { [bool]$matlabSmoke.requiredChecksPassed } else { $false }
            statistics_available = if ($matlabSmokeMatches) { [bool]$matlabSmoke.optionalStatisticsAvailable } else { $false }
        }
    }
}
$selectedTier = if ($Tier -eq 'core') { $coreProbe } else { $fullProbe }
if (-not $NoAggregateReport) {
    $tempReport = "$report.tmp-$PID"
    [System.IO.File]::WriteAllText($tempReport, ($snapshot | ConvertTo-Json -Depth 12), [System.Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tempReport -Destination $report -Force
    Get-Content -LiteralPath $report -Encoding UTF8
} else {
    $selectedTier | ConvertTo-Json -Depth 12
}
exit $(if ($selectedTier.status -eq 'PASS') { 0 } else { 1 })
