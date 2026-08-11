Set-StrictMode -Version Latest

function Resolve-ModelingProject {
    param([string]$Project)
    $hub = Get-ModelingRoot
    if ([string]::IsNullOrWhiteSpace($Project)) {
        return [pscustomobject]@{
            Id = 'legacy-root'
            HubRoot = $hub
            Root = $hub
            Legacy = $true
            Profile = $null
        }
    }
    $registryPath = Join-Path $hub 'config\projects.json'
    if (-not (Test-Path -LiteralPath $registryPath)) { throw "Project registry is missing: $registryPath" }
    $registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $matches = @($registry.projects | Where-Object { [string]$_.id -eq $Project })
    if ($matches.Count -ne 1) { throw "Unknown or ambiguous project id: $Project" }
    $projectsRoot = [System.IO.Path]::GetFullPath((Join-Path $hub 'projects')).TrimEnd('\')
    $root = [System.IO.Path]::GetFullPath((Join-Path $hub ([string]$matches[0].root))).TrimEnd('\')
    try { [System.IO.Path]::GetFullPath($root).Substring(0, $projectsRoot.Length) | Out-Null } catch { throw "Invalid project root: $root" }
    if (-not ($root.StartsWith($projectsRoot + '\', [System.StringComparison]::OrdinalIgnoreCase))) {
        throw "Project root must remain under projects/: $root"
    }
    return [pscustomobject]@{
        Id = [string]$matches[0].id
        HubRoot = $hub
        Root = $root
        Legacy = $false
        Profile = [string]$matches[0].profile
    }
}

function Assert-ProjectRoot {
    param([Parameter(Mandatory)][pscustomobject]$ProjectContext)
    if (-not $ProjectContext.Legacy -and -not (Test-Path -LiteralPath (Join-Path $ProjectContext.Root 'contest.yaml'))) {
        throw "Project has not been scaffolded: $($ProjectContext.Id). Run scripts/project.ps1 -Action scaffold -Project $($ProjectContext.Id)."
    }
}

