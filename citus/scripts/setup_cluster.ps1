param(
    [switch]$SkipVerification
)

Write-Host "=== BD2 Lab 16 — Setup del Cluster Citus ===" -ForegroundColor Cyan

# 1. Levantar servicios
Write-Host "[1/4] Levantando contenedores..." -ForegroundColor Yellow
docker compose -f "$PSScriptRoot\..\docker-compose.yml" up -d

# 2. Esperar healthchecks de los 3 nodos
Write-Host "[2/4] Esperando healthchecks..." -ForegroundColor Yellow
$healthcheckTimeout = 60
$interval = 5
$elapsed = 0

$containers = @("citus-coordinator", "citus-worker1", "citus-worker2")

foreach ($c in $containers) {
    $elapsed = 0
    Write-Host "  Esperando $c ..." -NoNewline
    while ($elapsed -lt $healthcheckTimeout) {
        $status = docker inspect --format='{{.State.Health.Status}}' $c 2>$null
        if ($status -eq "healthy") {
            Write-Host " healthy" -ForegroundColor Green
            break
        }
        Start-Sleep -Seconds $interval
        $elapsed += $interval
    }
    if ($elapsed -ge $healthcheckTimeout) {
        Write-Host " TIMEOUT" -ForegroundColor Red
        exit 1
    }
}

# 3. Ejecutar init.sql para crear tabla, distribuir e índices
Write-Host "[3/4] Ejecutando init.sql (tabla + workers + índices)..." -ForegroundColor Yellow
docker exec citus-coordinator psql -U postgres -d news_analysis_pg -f /scripts/init.sql
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR ejecutando init.sql" -ForegroundColor Red
    exit 1
}
Write-Host "  init.sql ejecutado correctamente" -ForegroundColor Green

# 4. Verificación
if (-not $SkipVerification) {
    Write-Host "[4/4] Verificando workers activos..." -ForegroundColor Yellow
    docker exec citus-coordinator psql -U postgres -d news_analysis_pg -c "SELECT * FROM citus_get_active_worker_nodes();"
    
    Write-Host "`nVerificando tabla distribuida..." -ForegroundColor Yellow
    docker exec citus-coordinator psql -U postgres -d news_analysis_pg -c "\d milei_news"
} else {
    Write-Host "[4/4] Verificación omitida (-SkipVerification)" -ForegroundColor Yellow
}

Write-Host "`n=== Cluster Citus listo ===" -ForegroundColor Cyan
Write-Host "Coordinator: localhost:5435  DB: news_analysis_pg  User: postgres"
Write-Host "Worker 1:    localhost:5433"
Write-Host "Worker 2:    localhost:5434"
Write-Host "`nSiguiente paso: python citus/scripts/load_data.py"