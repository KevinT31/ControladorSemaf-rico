# Arranca el nodo NSB como cliente HIL (conecta al gateway).
# Uso: .\run_node_hil.ps1 [-Mode tsc-emulated] [-Config config\nsb\node.yaml]
param(
    [string]$Mode = "tsc-emulated",
    [string]$Config = "config\nsb\node.yaml"
)
$ErrorActionPreference = "Continue"  # exes nativos loguean a stderr; el control es $LASTEXITCODE
Set-Location (Join-Path $PSScriptRoot "..\..\Diseño Software")
python -m nsb run --config $Config --source sumo_hil --mode $Mode
exit $LASTEXITCODE
