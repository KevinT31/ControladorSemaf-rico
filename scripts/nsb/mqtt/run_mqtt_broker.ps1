# Levanta el broker Mosquitto local con la config de laboratorio.
# Uso: .\run_mqtt_broker.ps1          # dev (1883, loopback, sin TLS)
#      .\run_mqtt_broker.ps1 -Tls     # TLS+mTLS (8883; requiere certs generados)
param(
    [switch]$Tls
)
$ErrorActionPreference = "Continue"

$mosquitto = (Get-Command mosquitto -ErrorAction SilentlyContinue).Source
if (-not $mosquitto) {
    $candidato = "C:\Program Files\mosquitto\mosquitto.exe"
    if (Test-Path $candidato) { $mosquitto = $candidato }
}
if (-not $mosquitto) {
    Write-Error "mosquitto no encontrado. Instale con: winget install EclipseFoundation.Mosquitto"
    exit 1
}

$confDir = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\config\nsb\mosquitto")
Set-Location $confDir   # las rutas del .conf son relativas al cwd del broker

if ($Tls) {
    $requeridos = @("certs\ca.crt", "certs\server.crt", "certs\server.key",
                    "acl.conf")
    $faltantes = @($requeridos | Where-Object { -not (Test-Path $_) })
    if ($faltantes.Count -gt 0) {
        Write-Error "TLS incompleto; faltan: $($faltantes -join ', '). Genere primero: scripts\nsb\mqtt\gen_lab_certs.ps1"
        exit 1
    }
    & $mosquitto -c mosquitto.tls.conf -v
} else {
    Write-Host "MODO DEV sin TLS (solo loopback). Para TLS use -Tls." -ForegroundColor Yellow
    & $mosquitto -c mosquitto.dev.conf -v
}
exit $LASTEXITCODE
