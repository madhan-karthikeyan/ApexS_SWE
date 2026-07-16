param(
    [string]$DumpPath = "tawos\raw\TAWOS.sql",
    [string]$MySqlExe = "mysql",
    [string]$Host = "127.0.0.1",
    [int]$Port = 3306,
    [string]$Database = "TAWOS_DB",
    [string]$User = "root",
    [switch]$CreateDatabase = $true
)

$resolvedDump = Resolve-Path -LiteralPath $DumpPath -ErrorAction Stop
$dumpForMysql = $resolvedDump.Path -replace "\\", "/"

if ($CreateDatabase) {
    & $MySqlExe "--host=$Host" "--port=$Port" "--user=$User" "--password" "-e" "CREATE DATABASE IF NOT EXISTS $Database;"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create or verify database '$Database'."
    }
}

& $MySqlExe "--host=$Host" "--port=$Port" "--user=$User" "--password" $Database "-e" "source $dumpForMysql"
if ($LASTEXITCODE -ne 0) {
    throw "TAWOS import failed."
}

Write-Host "Imported TAWOS dump into database '$Database' from '$($resolvedDump.Path)'."
