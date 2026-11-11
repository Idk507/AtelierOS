param([string]$PostgresBin = 'C:\Program Files\PostgreSQL\18\bin')
$ErrorActionPreference = 'Stop'
$workspace = Split-Path $PSScriptRoot -Parent
$localRoot = Join-Path $workspace '.local'
$dataPath = Join-Path $localRoot 'postgres-test'
New-Item -ItemType Directory -Force -Path $localRoot | Out-Null
if (-not (Test-Path (Join-Path $dataPath 'PG_VERSION'))) {
    & (Join-Path $PostgresBin 'initdb.exe') -D $dataPath -U atelier_test -A trust --encoding=UTF8 --locale=C
    if ($LASTEXITCODE -ne 0) { throw 'Test cluster initialization failed' }
}
& (Join-Path $PostgresBin 'pg_ctl.exe') -D $dataPath status | Out-Null
if ($LASTEXITCODE -ne 0) {
    & (Join-Path $PostgresBin 'pg_ctl.exe') -D $dataPath -l (Join-Path $localRoot 'postgres-test.log') -o '-h 127.0.0.1 -p 55439' -w start
    if ($LASTEXITCODE -ne 0) { throw 'Test cluster startup failed' }
}
$env:PGHOST = '127.0.0.1'
$env:PGPORT = '55439'
$env:PGUSER = 'atelier_test'
$exists = & (Join-Path $PostgresBin 'psql.exe') -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname = 'atelier_test'"
if ($LASTEXITCODE -ne 0) { throw 'Test server connection failed' }
if ($exists -ne '1') {
    & (Join-Path $PostgresBin 'createdb.exe') atelier_test
    if ($LASTEXITCODE -ne 0) { throw 'Test database creation failed' }
}
Write-Output 'Disposable loopback-only PostgreSQL ready on 127.0.0.1:55439/atelier_test. Never use this trust-auth cluster for real data.'
