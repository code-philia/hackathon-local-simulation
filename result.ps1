[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Workspace,
    [switch]$ShowTests
)

$ErrorActionPreference = "Stop"
$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCommand) {
    $PythonCommand = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $PythonCommand) {
    throw "Python 3 is required. Install Python 3.10+ and ensure python.exe or py.exe is on PATH."
}
$Python = $PythonCommand.Source
$PythonPrefix = @()
if ($PythonCommand.Name -eq "py.exe") { $PythonPrefix = @("-3") }
$Arguments = @((Join-Path $PSScriptRoot "local_submit.py"), "result", "--workspace", (Resolve-Path -LiteralPath $Workspace).Path)
if ($ShowTests) { $Arguments += "--show-tests" }
& $Python @PythonPrefix @Arguments
exit $LASTEXITCODE
