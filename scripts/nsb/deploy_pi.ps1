# Despliega el nodo NSB a una Raspberry Pi 4B por SSH/SCP (OpenSSH de Win11).
#
# Copia nucleo/ + nsb/ + config/ + requirements-nsb-pi.txt + scripts de Pi a
# /home/pi/nsb-node/ — ruta ASCII DELIBERADA (D-04): el layout relativo se
# conserva y los imports no cambian; la "ñ" de "Diseño Software" no viaja.
# Si existen certificados del nodo, copia SOLO ca.crt + <NodeId>.crt/.key
# (jamás ca.key ni claves de otros nodos).
#
# ESTADO HONESTO: IMPLEMENTED / REQUIRES HARDWARE — sin Pi física este script
# no ha podido validarse end-to-end (D-11).
#
# Uso: .\scripts\nsb\deploy_pi.ps1 -PiHost 192.168.1.50
#      .\scripts\nsb\deploy_pi.ps1 -PiHost raspberrypi.local -User pi -NodeId nsb-pi-01
param(
    [Parameter(Mandatory = $true)][string]$PiHost,
    [string]$User = "pi",
    [string]$NodeId = "nsb-pi-01",
    [string]$Dest = "/home/pi/nsb-node"
)
$ErrorActionPreference = "Continue"  # exes nativos loguean a stderr; control por $LASTEXITCODE

foreach ($exe in @("ssh", "scp")) {
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) {
        Write-Error "$exe no encontrado. Habilite el cliente OpenSSH de Windows."
        exit 1
    }
}

$raiz = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$sw = Join-Path $raiz "Diseño Software"
$certsDir = Join-Path $raiz "config\nsb\mosquitto\certs"
$destino = "${User}@${PiHost}"

# --- Staging local sin __pycache__ (robocopy: exit < 8 es éxito) ------------
$staging = Join-Path $env:TEMP ("nsb-deploy-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Force $staging | Out-Null
foreach ($carpeta in @("nucleo", "nsb", "config")) {
    robocopy (Join-Path $sw $carpeta) (Join-Path $staging $carpeta) /E /XD __pycache__ /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) {
        Write-Error "robocopy fallo copiando $carpeta (exit $LASTEXITCODE)"
        exit 2
    }
}
Copy-Item (Join-Path $sw "requirements-nsb-pi.txt") $staging
robocopy (Join-Path $raiz "scripts\nsb\pi") (Join-Path $staging "scripts") /E /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { Write-Error "robocopy fallo copiando scripts de Pi"; exit 2 }

# Certificados del nodo (opcional): SOLO ca.crt + su par — nunca ca.key
$conCerts = $false
if ((Test-Path (Join-Path $certsDir "ca.crt")) -and
    (Test-Path (Join-Path $certsDir "$NodeId.crt")) -and
    (Test-Path (Join-Path $certsDir "$NodeId.key"))) {
    New-Item -ItemType Directory -Force (Join-Path $staging "certs") | Out-Null
    foreach ($f in @("ca.crt", "$NodeId.crt", "$NodeId.key")) {
        Copy-Item (Join-Path $certsDir $f) (Join-Path $staging "certs")
    }
    $conCerts = $true
} else {
    Write-Host "Sin certificados para $NodeId (MQTT deshabilitado en la Pi hasta generarlos)." -ForegroundColor Yellow
}

# --- Copia a la Pi -----------------------------------------------------------
Write-Host "Creando $Dest en $destino ..."
ssh $destino "mkdir -p '$Dest'"
if ($LASTEXITCODE -ne 0) { Write-Error "ssh fallo (exit $LASTEXITCODE). ¿Llave/host correctos?"; exit 3 }

$items = @("nucleo", "nsb", "config", "scripts", "requirements-nsb-pi.txt")
if ($conCerts) { $items += "certs" }
$rutas = $items | ForEach-Object { Join-Path $staging $_ }
Write-Host "Copiando: $($items -join ', ') ..."
scp -r @rutas "${destino}:$Dest/"
if ($LASTEXITCODE -ne 0) { Write-Error "scp fallo (exit $LASTEXITCODE)"; exit 3 }

ssh $destino "chmod 600 '$Dest'/certs/*.key 2>/dev/null; chmod +x '$Dest'/scripts/*.sh"
if ($LASTEXITCODE -ne 0) { Write-Error "ajuste de permisos fallo"; exit 3 }

Remove-Item -Recurse -Force $staging
Write-Host ""
Write-Host "Despliegue copiado a ${destino}:$Dest" -ForegroundColor Green
Write-Host "Siguiente paso EN LA PI:"
Write-Host "  cd $Dest && ./scripts/install_pi.sh          # venv + dependencias"
Write-Host "  ./scripts/run_node.sh                        # corrida manual"
Write-Host "  sudo ./scripts/install_systemd.sh            # servicio (opcional)"
exit 0
