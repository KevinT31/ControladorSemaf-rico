# Genera la PKI de LABORATORIO para MQTT+TLS (spec §28): CA propia, cert de
# servidor (broker Mosquitto) y un cert de cliente por nodo (CN = node_id,
# usado como identidad/usuario en la ACL del broker).
#
# SOLO PARA LABORATORIO. Las claves van a config/nsb/mosquitto/certs/
# (directorio ignorado por git — jamás commitear claves privadas).
#
# Uso (desde cualquier directorio):
#   .\scripts\nsb\mqtt\gen_lab_certs.ps1
#   .\scripts\nsb\mqtt\gen_lab_certs.ps1 -Nodes nsb-node-01 -Observers nsb-observer -ServerSans 192.168.1.50
#   .\scripts\nsb\mqtt\gen_lab_certs.ps1 -Force        # regenera la CA (rotación)
param(
    [string[]]$Nodes = @("nsb-node-01", "nsb-pi-01"),
    [string[]]$Observers = @("nsb-observer"),
    [string[]]$ServerSans = @(),      # IPs/DNS extra del broker (p. ej. IP LAN para la Pi)
    [int]$DiasCa = 730,
    [int]$Dias = 365,
    [switch]$Force
)
$ErrorActionPreference = "Stop"

if ($DiasCa -lt 1 -or $Dias -lt 1) {
    Write-Error "DiasCa y Dias deben ser enteros >= 1."
    exit 1
}
$identidades = @($Nodes) + @($Observers)
if ($identidades.Count -eq 0) {
    Write-Error "Debe declarar al menos un nodo u observador."
    exit 1
}
if (($identidades | Select-Object -Unique).Count -ne $identidades.Count) {
    Write-Error "Nodes y Observers no pueden contener identidades duplicadas."
    exit 1
}
foreach ($identidad in $identidades) {
    if ($identidad -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$') {
        Write-Error "Identidad MQTT invalida: $identidad"
        exit 1
    }
}

# --- localizar openssl (Git para Windows lo incluye) -----------------------
$openssl = (Get-Command openssl -ErrorAction SilentlyContinue).Source
if (-not $openssl) {
    foreach ($candidato in @("C:\Program Files\Git\mingw64\bin\openssl.exe",
                             "C:\Program Files\Git\usr\bin\openssl.exe")) {
        if (Test-Path $candidato) { $openssl = $candidato; break }
    }
}
if (-not $openssl) {
    Write-Error "openssl no encontrado. Instale Git para Windows u OpenSSL y reintente."
    exit 1
}
# Un OPENSSL_CONF heredado roto (p. ej. de PostgreSQL ODBC) tumba todo openssl
if ($env:OPENSSL_CONF -and -not (Test-Path $env:OPENSSL_CONF)) {
    Write-Host "OPENSSL_CONF apunta a ruta inexistente ($env:OPENSSL_CONF); se ignora." -ForegroundColor Yellow
    Remove-Item Env:OPENSSL_CONF
}

$raiz = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
$dir = Join-Path $raiz "config\nsb\mosquitto\certs"
New-Item -ItemType Directory -Force $dir | Out-Null
Set-Location $dir

function Invoke-OpenSsl {
    param([string[]]$Argumentos)
    & $openssl @Argumentos
    if ($LASTEXITCODE -ne 0) {
        Write-Error "openssl fallo (exit $LASTEXITCODE): $($Argumentos -join ' ')"
        exit 2
    }
}

# --- CA de laboratorio ------------------------------------------------------
if ((Test-Path "ca.key") -and (Test-Path "ca.crt") -and -not $Force) {
    Write-Host "CA existente conservada (use -Force para rotarla)." -ForegroundColor Yellow
} else {
    if ($Force -and (Test-Path "ca.key")) {
        Write-Host "ROTACION: regenerando CA — todos los certs firmados dejan de valer." -ForegroundColor Yellow
    }
    Invoke-OpenSsl @("genrsa", "-out", "ca.key", "2048")
    Invoke-OpenSsl @("req", "-x509", "-new", "-key", "ca.key", "-sha256",
                     "-days", "$DiasCa", "-out", "ca.crt",
                     "-subj", "/CN=nsb-lab-ca")
    Write-Host "CA de laboratorio: ca.crt (valida $DiasCa dias)"
}

# --- Certificado del broker (SAN: localhost + IPs declaradas) ---------------
$san = @("DNS:localhost", "IP:127.0.0.1")
foreach ($extra in $ServerSans) {
    if ($extra -match '^\d{1,3}(\.\d{1,3}){3}$') { $san += "IP:$extra" }
    else { $san += "DNS:$extra" }
}
Set-Content -Path "server_ext.cnf" -Encoding ascii -Value @(
    "subjectAltName=$($san -join ',')",
    "extendedKeyUsage=serverAuth"
)
Invoke-OpenSsl @("genrsa", "-out", "server.key", "2048")
Invoke-OpenSsl @("req", "-new", "-key", "server.key", "-out", "server.csr",
                 "-subj", "/CN=localhost")
Invoke-OpenSsl @("x509", "-req", "-in", "server.csr", "-CA", "ca.crt",
                 "-CAkey", "ca.key", "-CAcreateserial", "-out", "server.crt",
                 "-days", "$Dias", "-sha256", "-extfile", "server_ext.cnf")
Write-Host "Broker: server.crt (SAN: $($san -join ', '))"

# --- Certificados de cliente por nodo (CN = node_id → identidad ACL) --------
Set-Content -Path "client_ext.cnf" -Encoding ascii -Value "extendedKeyUsage=clientAuth"
foreach ($nodo in $identidades) {
    Invoke-OpenSsl @("genrsa", "-out", "$nodo.key", "2048")
    Invoke-OpenSsl @("req", "-new", "-key", "$nodo.key", "-out", "$nodo.csr",
                     "-subj", "/CN=$nodo")
    Invoke-OpenSsl @("x509", "-req", "-in", "$nodo.csr", "-CA", "ca.crt",
                     "-CAkey", "ca.key", "-CAcreateserial", "-out", "$nodo.crt",
                     "-days", "$Dias", "-sha256", "-extfile", "client_ext.cnf")
    Write-Host "Cliente: $nodo.crt (CN=$nodo)"
}

# ACL coherente con las identidades generadas. Se enumeran los escritores:
# un pattern con %u también daría write a los observadores.
$acl = @(
    "# Generado por scripts/nsb/mqtt/gen_lab_certs.ps1",
    "# Nodos: escritura solo en su prefijo; observadores: lectura global."
)
foreach ($nodo in $Nodes) {
    $acl += ""
    $acl += "user $nodo"
    $acl += "topic write nsb/$nodo/#"
}
foreach ($observador in $Observers) {
    $acl += ""
    $acl += "user $observador"
    $acl += "topic read nsb/#"
}
Set-Content -LiteralPath (Join-Path $dir "..\acl.conf") -Encoding ascii -Value $acl

Remove-Item -Force "*.csr", "server_ext.cnf", "client_ext.cnf" -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "Certificados en: $dir" -ForegroundColor Green
Write-Host "Para la Pi copie SOLO: ca.crt + <nodo>.crt + <nodo>.key (deploy_pi.ps1 lo hace)."
exit 0
