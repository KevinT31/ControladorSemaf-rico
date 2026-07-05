# "CI local" de NSB: suite completa + smoke de imports + demos clave.
# Falla (exit != 0) ante el primer problema; no oculta errores.
$ErrorActionPreference = "Continue"  # exes nativos loguean a stderr; el control es $LASTEXITCODE
Set-Location (Join-Path $PSScriptRoot "..\..\Diseño Software")

Write-Host "=== 1/4 imports Windows ==="
python -c "import nsb, nsb.node, nsb.hil.gateway, nsb.actuation.gpio, nsb.cli.main; print('imports OK')"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== 2/4 pytest (unit+golden+integration+property+sumo) ==="
python -m pytest tests -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== 3/4 demos criticas ==="
foreach ($id in 6, 7, 8, 10, 12) {
    python -m nsb demo --id $id
    if ($LASTEXITCODE -ne 0) { Write-Error "DEMO $id fallo"; exit 2 }
}

Write-Host "=== 4/4 replay determinista por CLI ==="
$tmp = Join-Path $env:TEMP "nsb_verify"
New-Item -ItemType Directory -Force $tmp | Out-Null
python -m nsb record --escenario uniforme --pasos 15 --out "$tmp\v.jsonl"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m nsb run --source replay --input "$tmp\v.jsonl" --mode advisory
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "VERIFICACION COMPLETA: OK"
exit 0
