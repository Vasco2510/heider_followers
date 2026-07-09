# BD2 Lab — Parte II: Setup automatizado del cluster Citus
# Uso (desde la raiz del repo o desde citus/):
#   powershell -ExecutionPolicy Bypass -File citus/scripts/setup_cluster.ps1
#
# Hace: docker compose up -d -> espera healthchecks -> registra workers +
# crea tabla distribuida + indices (init.sql) -> muestra verificacion.

$ErrorActionPreference = "Stop"
$citusDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "=== 1/4 Levantando cluster Citus (coordinator + 2 workers) ===" -ForegroundColor Cyan
docker compose -f (Join-Path $citusDir "docker-compose.yml") up -d
if ($LASTEXITCODE -ne 0) { throw "docker compose up fallo" }

Write-Host "`n=== 2/4 Esperando a que los contenedores esten healthy ===" -ForegroundColor Cyan
$containers = @("citus-coordinator", "citus-worker1", "citus-worker2")
$deadline = (Get-Date).AddMinutes(3)
foreach ($c in $containers) {
    while ($true) {
        $status = docker inspect --format "{{.State.Health.Status}}" $c 2>$null
        if ($status -eq "healthy") { Write-Host "  $c : healthy"; break }
        if ((Get-Date) -gt $deadline) { throw "$c no llego a healthy en 3 minutos (estado: $status)" }
        Start-Sleep -Seconds 3
    }
}

# pg_isready pasa antes de que el entrypoint de la imagen termine de crear la
# extension citus; esperar a que exista en cada nodo evita una carrera.
Write-Host "  Esperando extension citus en cada nodo..."
foreach ($c in $containers) {
    while ($true) {
        # try/catch: durante el primer arranque postgres se reinicia y psql falla transitoriamente
        $ext = ""
        try { $ext = cmd /c "docker exec $c psql -U postgres -d news_analysis_pg -tAc `"SELECT 1 FROM pg_extension WHERE extname = 'citus'`" 2>nul" } catch {}
        if ("$ext".Trim() -eq "1") { Write-Host "  $c : extension citus lista"; break }
        if ((Get-Date) -gt $deadline) { throw "$c no tiene la extension citus tras 3 minutos" }
        Start-Sleep -Seconds 3
    }
}

Write-Host "`n=== 3/4 Ejecutando init.sql (workers + tabla distribuida + indices) ===" -ForegroundColor Cyan
docker exec citus-coordinator psql -U postgres -d news_analysis_pg -v ON_ERROR_STOP=1 -f /scripts/init.sql
if ($LASTEXITCODE -ne 0) { throw "init.sql fallo" }

Write-Host "`n=== 4/4 Verificacion (evidencia P6/P7) ===" -ForegroundColor Cyan
Write-Host "`n--- Workers activos ---"
docker exec citus-coordinator psql -U postgres -d news_analysis_pg -c "SELECT * FROM citus_get_active_worker_nodes();"
Write-Host "--- Distribucion de shards por worker ---"
docker exec citus-coordinator psql -U postgres -d news_analysis_pg -c "SELECT nodename, count(*) AS shards FROM citus_shards WHERE table_name::text = 'milei_news' GROUP BY nodename;"

Write-Host "`nCluster listo. Siguiente paso: cargar datos con" -ForegroundColor Green
Write-Host "  .venv\Scripts\python.exe citus/scripts/load_data.py" -ForegroundColor Green
