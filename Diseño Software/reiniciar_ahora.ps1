#!/usr/bin/env pwsh
<#
.SYNOPSIS
Reinicia el simulador autenticándose contra el backend local.
#>

$script = Join-Path $PSScriptRoot "reiniciar_simulador.py"
& python $script @args
exit $LASTEXITCODE
