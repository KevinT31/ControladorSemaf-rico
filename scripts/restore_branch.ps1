Set-StrictMode -Version Latest

# Script para restaurar rama backup y rebasarla sobre origin/main
Set-Location -Path "c:\Users\kevin\OneDrive\Desktop\ControladorSemaforicoTFC2"

$backup = git for-each-ref --sort=-committerdate --format='%(refname:short)' refs/heads/backup-main* | Select-Object -First 1
if (-not $backup) {
    Write-Host "NO_BACKUP_FOUND"
    exit 0
}

$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$restore = "restore-local-$ts"

Write-Host "CHECKOUT_FROM:$backup -> $restore"
git checkout -b $restore $backup

Write-Host "FETCH_ORIGIN"
git fetch origin

Write-Host "REBASE_START: origin/main"
git rebase origin/main
$rc = $LASTEXITCODE
if ($rc -ne 0) {
    Write-Host "REBASE_FAILED:$rc"
    git status --porcelain
    git status
    exit 0
}

# Aplicar parche si existe
$patch = Get-ChildItem -Path . -Filter "backup-changes-*.patch" -Name -ErrorAction SilentlyContinue | Select-Object -First 1
if ($patch) {
    Write-Host "APPLY_PATCH:$patch"
    git apply --index $patch
    if ($LASTEXITCODE -ne 0) {
        Write-Host "APPLY_PATCH_FAILED"
        exit 0
    }
    git add -A
    git commit -m "Restore uncommitted changes from $patch"
}

Write-Host "RESTORE_DONE:$restore"
Write-Host "GIT_STATUS_PORCELAIN:"; git status --porcelain
Write-Host "LATEST_COMMITS:"; git log --oneline -n 8

exit 0
