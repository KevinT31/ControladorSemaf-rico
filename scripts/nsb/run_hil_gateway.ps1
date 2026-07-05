# Arranca el HIL Gateway (SUMO + servidor TCP step-synchronous).
# Requiere el escenario nsb-cruz generado y SUMO_HOME configurado.
# Uso: .\run_hil_gateway.ps1 [-Config config\nsb\gateway.yaml]
param(
    [string]$Config = "config\nsb\gateway.yaml"
)
$ErrorActionPreference = "Continue"  # exes nativos loguean a stderr; el control es $LASTEXITCODE
Set-Location (Join-Path $PSScriptRoot "..\..\Diseño Software")

if (-not $env:SUMO_HOME) {
    Write-Error "SUMO_HOME no definido: instala SUMO y define la variable."
    exit 1
}
$escenario = "integracion-sumo\escenarios\nsb-cruz\nsb_cruz.sumocfg"
if (-not (Test-Path $escenario)) {
    Write-Host "Escenario nsb-cruz no encontrado; generándolo..."
    python "integracion-sumo\escenarios\nsb-cruz\generar_escenario.py"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
python -m nsb gateway --config $Config
exit $LASTEXITCODE
