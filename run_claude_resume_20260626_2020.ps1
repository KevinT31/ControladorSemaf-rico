$ProjectPath = 'C:\Users\P5PractTI\Desktop\OverLeaf_Local'
$LogPath = Join-Path $ProjectPath 'claude_resume_20260626_2020.log'

$Prompt = @'
Continúa exactamente desde donde quedó el trabajo anterior antes de que se agotara la ventana de contexto.

Proyecto:
C:\Users\P5PractTI\Desktop\OverLeaf_Local

Antes de modificar cualquier archivo:
1. Revisa el estado actual del proyecto con git status.
2. Revisa los cambios existentes con git diff.
3. Revisa archivos de contexto si existen: CLAUDE.md, CONTINUAR_CLAUDE.md, README.md, notas, TODOs o archivos recientemente modificados.
4. No rehagas trabajo ya aplicado.
5. No descartes cambios existentes.
6. No borres contenido útil.
7. Continúa con la tarea pendiente más lógica según el estado actual del proyecto.
8. Si hay instrucciones previas dentro del proyecto, respétalas.
9. Si modificas main.tex, mainV3.tex, mainV4.tex o archivos relacionados con la tesis, mantén el estilo académico y la coherencia del documento.
10. Al terminar, crea o actualiza un archivo llamado CONTINUAR_CLAUDE.md con:
   - Qué hiciste.
   - Qué archivos modificaste.
   - Qué quedó pendiente.
   - Qué comandos debo ejecutar para verificar.
   - Qué prompt debería usar si necesito continuar después.

Trabaja de forma autónoma y segura dentro del proyecto.
'@

function Write-Log {
    param([string]$Message)

    $Message | Out-File -LiteralPath $LogPath -Append -Encoding utf8
}

$exitCode = 0

try {
    Set-Location -LiteralPath $ProjectPath -ErrorAction Stop
    "Inicio: $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz'))" |
        Out-File -LiteralPath $LogPath -Encoding utf8

    Write-Log ''
    Write-Log '=== git status ==='
    & git status 2>&1 | Out-File -LiteralPath $LogPath -Append -Encoding utf8
    $gitStatusExitCode = $LASTEXITCODE
    Write-Log "Código de salida de git status: $gitStatusExitCode"

    Write-Log ''
    Write-Log '=== git diff --stat ==='
    & git diff --stat 2>&1 | Out-File -LiteralPath $LogPath -Append -Encoding utf8
    $gitDiffExitCode = $LASTEXITCODE
    Write-Log "Código de salida de git diff --stat: $gitDiffExitCode"

    Write-Log ''
    Write-Log '=== Claude Code ==='
    $claudeCommand = Get-Command claude -ErrorAction SilentlyContinue
    if ($null -eq $claudeCommand) {
        Write-Log 'ERROR: Claude Code no está instalado o el comando claude no está disponible en PATH para esta tarea programada.'
        $exitCode = 127
    }
    else {
        Write-Log "Ejecutable detectado: $($claudeCommand.Source)"
        & $claudeCommand.Source --dangerously-skip-permissions -c -p $Prompt 2>&1 |
            Out-File -LiteralPath $LogPath -Append -Encoding utf8
        $exitCode = $LASTEXITCODE
        Write-Log "Código de salida de Claude Code: $exitCode"
    }
}
catch {
    try {
        Write-Log "ERROR NO CONTROLADO: $($_.Exception.Message)"
    }
    catch {
        # Si ni siquiera puede escribirse el log, PowerShell conservará el fallo en el historial de la tarea.
    }
    $exitCode = 1
}
finally {
    try {
        Write-Log ''
        Write-Log "Finalización: $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz'))"
        Write-Log "Código de salida final: $exitCode"
    }
    catch {
        # No reemplazar el código de salida original por un fallo al cerrar el log.
    }
}

exit $exitCode
