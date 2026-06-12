param(
  [string]$Date = "20260617",
  [string[]]$Class,
  [string[]]$DetailFile,
  [string]$ListFile,
  [switch]$Download,
  [int]$Limit = 0
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$arguments = @(
  "compose",
  "exec",
  "backend",
  "python",
  "-m",
  "app.cli.import_cr12306",
  "--date",
  $Date
)

if ($Download) {
  $arguments += "--download"
}

foreach ($item in $Class) {
  $arguments += "--class"
  $arguments += $item
}

$hostDataDir = Join-Path $repoRoot "data\cr12306"

function Resolve-ImportPath {
  param([string]$PathValue)

  if (Test-Path -LiteralPath $PathValue) {
    New-Item -ItemType Directory -Force $hostDataDir | Out-Null
    $fileName = Split-Path -Leaf $PathValue
    $destination = Join-Path $hostDataDir $fileName
    Copy-Item -LiteralPath $PathValue -Destination $destination -Force
    return "/app/data/cr12306/$fileName"
  }

  return $PathValue
}

foreach ($item in $DetailFile) {
  $arguments += "--detail-file"
  $arguments += (Resolve-ImportPath $item)
}

if ($ListFile) {
  $arguments += "--list-file"
  $arguments += (Resolve-ImportPath $ListFile)
}

if ($Limit -gt 0) {
  $arguments += "--limit"
  $arguments += $Limit.ToString()
}

Push-Location $repoRoot
try {
  docker @arguments
}
finally {
  Pop-Location
}
