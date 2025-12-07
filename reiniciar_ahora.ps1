#!/usr/bin/env pwsh
<#
.SYNOPSIS
Reinicia el simulador de tráfico de Lima con todas las 47 intersecciones
.DESCRIPTION
Envía una solicitud al backend para reinicializar el SimuladorLima con todos los datos actuales
#>

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  REINICIADOR DE SIMULADOR - PowerShell" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "📡 Enviando solicitud de reinicio al servidor..." -ForegroundColor Yellow
Write-Host "   URL: http://localhost:8000/api/simulacion/reiniciar" -ForegroundColor Gray
Write-Host "   Espera..." -ForegroundColor Gray

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/simulacion/reiniciar" `
        -Method POST `
        -ContentType "application/json" `
        -Body '{"escenario":"hora_pico_manana"}' `
        -TimeoutSec 10

    if ($response.StatusCode -eq 200) {
        Write-Host "`n✅ ÉXITO: Simulador reiniciado correctamente" -ForegroundColor Green
        Write-Host "   Ahora el backend tiene TODAS LAS 47 INTERSECCIONES cargadas" -ForegroundColor Green
        Write-Host "`n📊 Respuesta del servidor:" -ForegroundColor Green
        
        $data = $response.Content | ConvertFrom-Json
        Write-Host "   Mensaje: $($data.mensaje)" -ForegroundColor Green
        Write-Host "   Escenario: $($data.datos.escenario)" -ForegroundColor Green
        
        Write-Host "`n💡 Próximo paso:" -ForegroundColor Cyan
        Write-Host "   1. Abre o actualiza la interfaz web (F5)" -ForegroundColor Cyan
        Write-Host "   2. Deberías ver TODOS los marcadores brillando en el mapa" -ForegroundColor Cyan
        Write-Host "   3. Incluyendo: LV-003, LV-004, SJL-003-009, TR-001-003, SM-004, etc." -ForegroundColor Cyan
    }
    else {
        Write-Host "`n❌ ERROR: Respuesta inesperada del servidor (HTTP $($response.StatusCode))" -ForegroundColor Red
        Write-Host $response.Content -ForegroundColor Red
    }
}
catch {
    Write-Host "`n❌ ERROR DE CONEXIÓN" -ForegroundColor Red
    Write-Host "   No se pudo conectar con http://localhost:8000" -ForegroundColor Red
    Write-Host "   Asegúrate de que:" -ForegroundColor Yellow
    Write-Host "   • El servidor backend está corriendo" -ForegroundColor Yellow
    Write-Host "   • Está en http://localhost:8000" -ForegroundColor Yellow
    Write-Host "`n   Error: $($_.Exception.Message)" -ForegroundColor Gray
}

Write-Host "`n"
