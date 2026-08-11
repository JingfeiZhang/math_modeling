[CmdletBinding(DefaultParameterSetName = 'Script')]
param(
    [Parameter(Mandatory = $true, ParameterSetName = 'Script')]
    [string]$Script,

    [Parameter(Mandatory = $true, ParameterSetName = 'Batch')]
    [string]$Batch,

    [string]$MatlabRoot
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_matlab.ps1')

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$configuredRoot = if ($MatlabRoot) { $MatlabRoot } else { Get-ConfiguredMatlabRoot -WorkspaceRoot $workspaceRoot }
$installation = Resolve-MatlabInstallation -PreferredRoot $configuredRoot -StrictPreferred:([bool]$configuredRoot)
$resolvedRoot = $installation.Root
$matlabExe = $installation.Executable
$runtimeDir = $installation.Runtime

# Refresh the current process without duplicating permanent user PATH entries.
$pathParts = [System.Collections.Generic.List[string]]::new()
foreach ($entry in @(
    (Join-Path $resolvedRoot 'bin'),
    $runtimeDir,
    [Environment]::GetEnvironmentVariable('Path', 'Machine'),
    [Environment]::GetEnvironmentVariable('Path', 'User')
)) {
    if ($entry) {
        foreach ($part in $entry -split ';') {
            if ($part -and -not $pathParts.Contains($part)) { $pathParts.Add($part) }
        }
    }
}
$env:Path = $pathParts -join ';'
$env:MATLAB_ROOT = $resolvedRoot

if ($PSCmdlet.ParameterSetName -eq 'Script') {
    $resolvedScript = (Resolve-Path -LiteralPath $Script).Path.Replace('\', '/')
    $escapedScript = $resolvedScript.Replace("'", "''")
    $batchExpression = "run('$escapedScript')"
} else {
    $batchExpression = $Batch
}

Write-Host "MATLAB root: $resolvedRoot"
Write-Host "MATLAB release: $($installation.Release)"
Write-Host "Batch command: $batchExpression"
& $matlabExe -batch $batchExpression
exit $LASTEXITCODE
