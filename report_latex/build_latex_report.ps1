param(
    [switch]$RefreshAssets,
    [string]$Python = "",
    [string]$Engine = "pdflatex"
)

$ErrorActionPreference = "Stop"
if (-not $Python) {
    $RepositoryPython = Join-Path (Split-Path -Parent $PSScriptRoot) ".venv/Scripts/python.exe"
    if (Test-Path -LiteralPath $RepositoryPython) {
        $Python = $RepositoryPython
    } else {
        $Python = (Get-Command python -ErrorAction Stop).Source
    }
}
$ScriptArguments = @("-B", (Join-Path $PSScriptRoot "build_latex_report.py"), "--engine", $Engine)
if ($RefreshAssets) {
    $ScriptArguments += "--refresh-assets"
}
& $Python @ScriptArguments
if ($LASTEXITCODE -ne 0) {
    throw "La compilation a échoué ; consulter report_latex/_build/."
}
