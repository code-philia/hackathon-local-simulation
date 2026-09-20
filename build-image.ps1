[CmdletBinding()]
param(
    [string]$MonorepoRoot = $env:ARCBENCH_MONOREPO_ROOT,
    [string]$BaseImage = $(if ($env:ARCBENCH_LOCAL_BASE_IMAGE) { $env:ARCBENCH_LOCAL_BASE_IMAGE } else { "arcbench-runner:local-base" }),
    [string]$LocalImage = $(if ($env:ARCBENCH_LOCAL_IMAGE) { $env:ARCBENCH_LOCAL_IMAGE } else { "arcbench-local-submit:latest" }),
    [string]$Platform = $env:ARCBENCH_LOCAL_PLATFORM
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Invoke-Docker {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Test-LocalImage {
    param([Parameter(Mandatory = $true)][string]$Image)
    & docker image inspect $Image *> $null
    return $LASTEXITCODE -eq 0
}

if ($MonorepoRoot) {
    $MonorepoRoot = (Resolve-Path -LiteralPath $MonorepoRoot).Path
    $RunnerDockerfile = Join-Path $MonorepoRoot "backend\runner\Dockerfile"
    if (-not (Test-Path -LiteralPath $RunnerDockerfile -PathType Leaf)) {
        throw "ARCBENCH_MONOREPO_ROOT must point to the ARC-Bench website repository root. Missing: $RunnerDockerfile"
    }

    $BaseBuildArguments = @("build")
    if ($Platform) { $BaseBuildArguments += @("--platform", $Platform) }
    $BaseBuildArguments += @("-f", $RunnerDockerfile, "-t", $BaseImage, $MonorepoRoot)
    Invoke-Docker $BaseBuildArguments
    Invoke-Docker @("run", "--rm", "--entrypoint", "python3", $BaseImage, "/opt/arcbench/smoke_test.py")
}
elseif (-not (Test-LocalImage $BaseImage)) {
    throw @"
The base image '$BaseImage' is not available locally.
Either set ARCBENCH_MONOREPO_ROOT to the ARC-Bench website checkout, or pull/tag a published base image:

  docker pull <registry>/arcbench/runner:<tag>
  docker tag <registry>/arcbench/runner:<tag> $BaseImage
"@
}
else {
    Write-Host "Reusing existing base image: $BaseImage"
}

$LocalBuildArguments = @("build")
if ($Platform) { $LocalBuildArguments += @("--platform", $Platform) }
$LocalBuildArguments += @("--build-arg", "ARCBENCH_RUNNER_IMAGE=$BaseImage", "-f", (Join-Path $ScriptDir "Dockerfile"), "-t", $LocalImage, $ScriptDir)
Invoke-Docker $LocalBuildArguments
Invoke-Docker @("run", "--rm", "--entrypoint", "python3", $LocalImage, "-m", "py_compile", "/opt/arcbench/local_runner.py")

Write-Host "Built local competition image: $LocalImage"

