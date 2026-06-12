$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = Split-Path -Parent $PSScriptRoot
$toolsRoot = Join-Path $root "tools"
$target = Join-Path $toolsRoot "tectonic"
$extract = Join-Path $target "extract"

New-Item -ItemType Directory -Force -Path $target | Out-Null

$resolvedToolsRoot = [System.IO.Path]::GetFullPath($toolsRoot)
$resolvedExtract = [System.IO.Path]::GetFullPath($extract)
if (-not $resolvedExtract.StartsWith($resolvedToolsRoot)) {
  throw "Ruta de extraccion invalida: $resolvedExtract"
}

$headers = @{ "User-Agent" = "OverLeaf-Local" }
$release = Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/tectonic-typesetting/tectonic/releases/latest"
$asset = $release.assets |
  Where-Object { $_.name -like "*x86_64-pc-windows-msvc.zip" } |
  Select-Object -First 1

if (-not $asset) {
  $asset = $release.assets |
    Where-Object { $_.name -like "*x86_64-pc-windows-gnu.zip" } |
    Select-Object -First 1
}

if (-not $asset) {
  throw "No se encontro un binario de Tectonic para Windows x64 en el release $($release.tag_name)."
}

$zipPath = Join-Path $env:TEMP $asset.name
Write-Host "Descargando $($asset.name)..."
Invoke-WebRequest -Headers $headers -Uri $asset.browser_download_url -OutFile $zipPath

if (Test-Path -LiteralPath $extract) {
  Remove-Item -LiteralPath $extract -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $extract | Out-Null
Expand-Archive -LiteralPath $zipPath -DestinationPath $extract -Force

$exe = Get-ChildItem -LiteralPath $extract -Recurse -Filter "tectonic.exe" | Select-Object -First 1
if (-not $exe) {
  throw "No se encontro tectonic.exe dentro del ZIP descargado."
}

Copy-Item -Path (Join-Path $exe.DirectoryName "*") -Destination $target -Recurse -Force
Remove-Item -LiteralPath $extract -Recurse -Force

$tectonic = Join-Path $target "tectonic.exe"
Write-Host "Instalado en $tectonic"
& $tectonic --version
