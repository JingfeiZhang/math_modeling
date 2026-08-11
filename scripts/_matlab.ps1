function Get-ConfiguredMatlabRoot {
    param([string]$WorkspaceRoot)

    if (-not $WorkspaceRoot) {
        $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    }
    $contestPath = Join-Path $WorkspaceRoot 'contest.yaml'
    if (-not (Test-Path -LiteralPath $contestPath)) { return $null }

    $line = Get-Content -LiteralPath $contestPath -Encoding UTF8 |
        Where-Object { $_ -match '^\s+matlab_root:\s*(.+?)\s*$' } |
        Select-Object -First 1
    if (-not $line) { return $null }

    $value = ($line -replace '^\s+matlab_root:\s*', '').Trim().Trim('"').Trim("'")
    if (-not $value) { return $null }
    return $value.Replace('/', '\')
}

function Resolve-MatlabInstallation {
    param(
        [string]$PreferredRoot,
        [switch]$StrictPreferred
    )

    if ($PreferredRoot -and $StrictPreferred) {
        $preferredExecutable = Join-Path $PreferredRoot 'bin\matlab.exe'
        if (-not (Test-Path -LiteralPath $preferredExecutable)) {
            throw "Configured MATLAB root is invalid or incomplete: $PreferredRoot"
        }
    }

    $candidates = [System.Collections.Generic.List[object]]::new()
    if ($PreferredRoot) {
        [void]$candidates.Add([pscustomobject]@{ Root = $PreferredRoot; Source = 'configured' })
    }
    if ($env:MATLAB_ROOT) {
        [void]$candidates.Add([pscustomobject]@{ Root = $env:MATLAB_ROOT; Source = 'MATLAB_ROOT' })
    }

    foreach ($registryBase in @(
        'HKLM:\SOFTWARE\MathWorks\MATLAB',
        'HKCU:\SOFTWARE\MathWorks\MATLAB',
        'HKLM:\SOFTWARE\WOW6432Node\MathWorks\MATLAB'
    )) {
        if (-not (Test-Path -LiteralPath $registryBase)) { continue }
        Get-ChildItem -LiteralPath $registryBase -ErrorAction SilentlyContinue |
            Sort-Object PSChildName -Descending |
            ForEach-Object {
                $properties = Get-ItemProperty -LiteralPath $_.PSPath -ErrorAction SilentlyContinue
                $rootProperty = if ($properties) { $properties.PSObject.Properties['MATLABROOT'] } else { $null }
                $root = if ($rootProperty) { $rootProperty.Value } else { $null }
                if ($root) {
                    [void]$candidates.Add([pscustomobject]@{
                        Root = [string]$root
                        Source = "registry:$($_.PSChildName)"
                    })
                }
            }
    }

    $command = Get-Command matlab.exe -ErrorAction SilentlyContinue
    if ($command) {
        [void]$candidates.Add([pscustomobject]@{
            Root = Split-Path -Parent (Split-Path -Parent $command.Source)
            Source = 'process-path'
        })
    }

    foreach ($pathScope in @('Machine', 'User')) {
        $pathValue = [Environment]::GetEnvironmentVariable('Path', $pathScope)
        foreach ($entry in [string]$pathValue -split ';') {
            $trimmed = $entry.Trim().TrimEnd('\')
            if ($trimmed -match '(?i)\\MATLAB\\R[^\\]+\\bin$') {
                [void]$candidates.Add([pscustomobject]@{
                    Root = Split-Path -Parent $trimmed
                    Source = "$($pathScope.ToLowerInvariant())-path"
                })
            }
        }
    }

    foreach ($parent in @('D:\MATLAB', 'C:\Program Files\MATLAB')) {
        if (-not (Test-Path -LiteralPath $parent)) { continue }
        Get-ChildItem -LiteralPath $parent -Directory -Filter 'R*' -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object {
                [void]$candidates.Add([pscustomobject]@{
                    Root = $_.FullName
                    Source = 'discovered-directory'
                })
            }
    }

    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($candidate in $candidates) {
        if (-not $candidate.Root) { continue }
        try {
            $root = [System.IO.Path]::GetFullPath([string]$candidate.Root).TrimEnd('\')
        } catch {
            continue
        }
        if (-not $seen.Add($root)) { continue }
        $executable = Join-Path $root 'bin\matlab.exe'
        if (-not (Test-Path -LiteralPath $executable)) { continue }

        $runtime = Join-Path $root 'runtime\win64'
        $release = Split-Path -Leaf $root
        $fileVersion = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($executable)
        return [pscustomobject]@{
            Root = (Resolve-Path -LiteralPath $root).Path
            Executable = (Resolve-Path -LiteralPath $executable).Path
            Runtime = if (Test-Path -LiteralPath $runtime) { (Resolve-Path -LiteralPath $runtime).Path } else { $null }
            Release = $release
            ExecutableVersion = $fileVersion.ProductVersion
            Source = $candidate.Source
        }
    }

    throw 'MATLAB was not found. Configure workflow.matlab_root, pass -MatlabRoot, or set MATLAB_ROOT.'
}
