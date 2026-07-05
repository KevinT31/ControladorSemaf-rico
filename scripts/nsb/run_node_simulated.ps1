# Arranca el nodo NSB en Windows con actuador simulado (fuente manual).
# Uso: .\run_node_simulated.ps1 [-Mode tsc-emulated] [-Escenario congestion_ns] [-Pasos 40]
param(
    [string]$Mode = "tsc-emulated",
    [string]$Escenario = "congestion_ns",
    [int]$Pasos = 40
)
$ErrorActionPreference = "Continue"  # exes nativos loguean a stderr; el control es $LASTEXITCODE
Set-Location (Join-Path $PSScriptRoot "..\..\Diseño Software")
python -m nsb run --source manual --mode $Mode --escenario $Escenario --pasos $Pasos --render
exit $LASTEXITCODE
