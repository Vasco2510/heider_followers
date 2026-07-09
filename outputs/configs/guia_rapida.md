# Guía Rápida de Configuración

## MongoDB (Sharding)

### docker-compose.yml
```yaml
# Puerto mongos: 27017
# Puerto config server: 27019
# Puerto shard1: 27018
# Puerto shard2: 27020
# Red: lab16_net
```

### Conexión
```bash
# Host local (mongos)
mongodb://localhost:27017

# MongoDB Compass
Connection String: mongodb://localhost:27017
Database: news_analysis
Collection: milei_news
```

### Comandos útiles
```javascript
// Ver estado del cluster (ejecutar en mongos)
sh.status()

// Ver distribución de chunks
db.milei_news.getShardDistribution()

// Ver stats de colección
db.milei_news.stats()
```

---

## Citus (PostgreSQL)

### docker-compose.yml
```yaml
# Puerto coordinator: 5435 (el 5432 del host lo ocupa un PostgreSQL 17 local)
# Puerto worker1: 5433
# Puerto worker2: 5434
# DB name: news_analysis_pg
# User: postgres / Password: postgres
# Red: citus_net
```

### Conexión
```bash
# Host local (coordinator)
host=localhost port=5435 dbname=news_analysis_pg user=postgres password=postgres

# pgAdmin
Host: localhost
Port: 5435
Database: news_analysis_pg
Username: postgres
Password: postgres
```

### Comandos útiles
```sql
-- Ver workers activos
SELECT * FROM citus_get_active_worker_nodes();

-- Ver distribución de shards
SELECT * FROM citus_shards;

-- Ver tamaño de tabla
SELECT * FROM citus_table_sizes;
```

---

## Credenciales por defecto

| Sistema | Usuario | Password | Puerto |
|---------|---------|----------|--------|
| MongoDB | - | - | 27017 (mongos) |
| Citus Coordinator | postgres | postgres | 5435 |
| Citus Worker 1 | postgres | postgres | 5433 |
| Citus Worker 2 | postgres | postgres | 5434 |

## Redes Docker

| Sistema | Network name |
|---------|--------------|
| MongoDB | `lab16_mongo_net` |
| Citus | `lab16_citus_net` |

## Archivos de script

| Archivo | Propósito |
|---------|-----------|
| `mongodb/docker-compose.yml` | Cluster MongoDB (mongos + config + 2 shards) |
| `mongodb/scripts/load_data.py` | Carga y limpieza del dataset en MongoDB |
| `mongodb/scripts/init-sharding.js` | Habilitar sharding + crear índices |
| `citus/docker-compose.yml` | Cluster Citus (coordinator + 2 workers) |
| `citus/scripts/init.sql` | Workers + DDL + tabla distribuida + índices (ejecutar tras healthchecks) |
| `citus/scripts/setup_cluster.ps1` | Setup automatizado: up + wait + init.sql + verificación |
| `citus/scripts/load_data.py` | Carga del dataset en Citus |

## Comandos de ejecución (orden)

```powershell
# 0. Entorno virtual (una sola vez)
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 1. Limpieza del dataset (requiere dataset crudo en dataset/)
.venv\Scripts\python.exe scripts/clean_and_extract.py

# 2. Levantar MongoDB cluster
cd mongodb; docker compose up -d
# Esperar ~30s a que se inicialicen los replica sets y sharding

# 3. Verificar cluster MongoDB
docker exec mongo-mongos mongosh --eval "sh.status()"
# Abrir Compass -> mongodb://localhost:27017 -> news_analysis.milei_news

# 4. Cargar datos en MongoDB
.venv\Scripts\python.exe mongodb/scripts/load_data.py

# 5. Levantar y configurar Citus (up + workers + tabla distribuida + índices)
powershell -ExecutionPolicy Bypass -File citus/scripts/setup_cluster.ps1

# 6. Verificar workers Citus (lo hace el script; comando manual:)
docker exec citus-coordinator psql -U postgres -d news_analysis_pg -c "SELECT * FROM citus_get_active_worker_nodes()"

# 7. Cargar datos en Citus
.venv\Scripts\python.exe citus/scripts/load_data.py

# 8. Ejecutar notebooks (abrir en VS Code con extensión Jupyter)
# mongodb/notebooks/mongo_analysis.ipynb
# citus/notebooks/citus_analysis.ipynb
```

## Notas

- MongoDB no requiere autenticación por defecto
- Citus usa autenticación por confianza (trust) en red interna
- Los archivos JSON del dataset están en `dataset/`; el dataset limpio en `dataset/processed/`
- Los notebooks Jupyter se ejecutan desde VS Code con extensión Jupyter
- Los screenshots se almacenan en `outputs/screenshots/` + subcarpetas por sistema