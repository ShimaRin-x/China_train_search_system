param(
  [string[]]$File,
  [string]$Source = "openstreetmap",
  [switch]$Download,
  [string]$Bbox = "17,73,54.5,136.5",
  [string]$OverpassUrl,
  [string]$Output = "data/osm/osm_railway_stations.json",
  [switch]$AreaQuery,
  [switch]$MatchOnly,
  [switch]$OverwriteExistingLocation,
  [switch]$NoBboxFilter
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$hostDataDir = Join-Path $repoRoot "data\osm"

$arguments = @(
  "compose",
  "exec",
  "backend",
  "python",
  "-m",
  "app.cli.import_osm_stations",
  "--source",
  $Source
)

function Resolve-ImportPath {
  param([string]$PathValue)

  if (Test-Path -LiteralPath $PathValue) {
    New-Item -ItemType Directory -Force $hostDataDir | Out-Null
    $fileName = Split-Path -Leaf $PathValue
    $destination = Join-Path $hostDataDir $fileName
    Copy-Item -LiteralPath $PathValue -Destination $destination -Force
    return "/app/data/osm/$fileName"
  }

  return $PathValue
}

foreach ($item in $File) {
  $arguments += "--file"
  $arguments += (Resolve-ImportPath $item)
}

if ($Download) {
  $arguments += "--download"
  $arguments += "--bbox"
  $arguments += $Bbox
  $arguments += "--output"
  $outputPath = $Output -replace "\\", "/"
  if (-not $outputPath.StartsWith("/app/")) {
    $outputPath = "/app/$outputPath"
  }
  $arguments += $outputPath
}

if ($AreaQuery) {
  $arguments += "--area-query"
}

if ($OverpassUrl) {
  $arguments += "--overpass-url"
  $arguments += $OverpassUrl
}

if ($MatchOnly) {
  $arguments += "--match-only"
}

if ($OverwriteExistingLocation) {
  $arguments += "--overwrite-existing-location"
}

if ($NoBboxFilter) {
  $arguments += "--no-bbox-filter"
}

Push-Location $repoRoot
try {
  docker @arguments
}
finally {
  Pop-Location
}
