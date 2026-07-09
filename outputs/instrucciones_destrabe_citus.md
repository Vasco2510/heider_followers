# Instrucciones de Destrabe — Citus Cluster

**Propósito:** Resolver el bloqueo actual donde el coordinator Citus no puede conectar con los workers debido a autenticación (`fe_sendauth: no password supplied`). Tras estos pasos, el cluster Citus queda operativo y listo para cargar datos.

**Contexto técnico (buena práctica):** Los workers Citus usan `scram-sha-256` como método de autenticación por defecto. Al ejecutar `master_add_node()`, el coordinator intenta conectar sin enviar credenciales — no hay parámetro para password en esa función. En un entorno de desarrollo con red Docker aislada (`lab16_citus_net`), configurar `trust` en los workers es la práctica recomendada por la documentación oficial de Citus. No hay exposición a internet ni a otros contenedores.

---

## 1. Verificar estado actual de los contenedores

```bash
docker ps --filter "name=citus" --format "table {{.Names}}\t{{.Status}}"
```

**Output esperado:**
```
NAMES               STATUS
citus-worker1       Up X minutes (healthy)
citus-worker2       Up X minutes (healthy)
citus-coordinator   Up X seconds (healthy)
```

**Si algún worker no aparece saludable:** esperar 10-15 segundos más. Si persiste, revisar logs: `docker logs <container_name> --tail 20`.

---

## 2. Configurar trust authentication en los workers

**Motivo:** `master_add_node()` envía conexión sin password. `trust` permite al coordinator autenticarse sin credenciales en la red Docker interna.

### Worker 1

```bash
docker exec citus-worker1 bash -c \
  "echo 'host all all 0.0.0.0/0 trust' >> /var/lib/postgresql/data/pg_hba.conf \
   && psql -U postgres -c 'SELECT pg_reload_conf();'"
```

**Output esperado:**
```
 pg_reload_conf 
----------------
 t
(1 row)
```

`t` significa que PostgreSQL recargó la configuración sin errores. La línea `host all all 0.0.0.0/0 trust` ya está activa.

### Worker 2

```bash
docker exec citus-worker2 bash -c \
  "echo 'host all all 0.0.0.0/0 trust' >> /var/lib/postgresql/data/pg_hba.conf \
   && psql -U postgres -c 'SELECT pg_reload_conf();'"
```

**Output esperado:** mismo que worker 1.

**Si falla:** el problema más común es que `psql` no encuentre el usuario `postgres` (error `role "postgres" does not exist`). En ese caso usar `psql -U root` o el usuario que esté configurado. Para verificarlo:

```bash
docker inspect citus-worker1 --format '{{range .Config.Env}}{{println .}}{{end}}' | grep POSTGRES_USER
```

---

## 3. Agregar workers al coordinator

**Motivo:** Registrar los workers en el metadato de Citus para que el coordinator distribuya datos entre ellos.

```bash
docker exec citus-coordinator psql -U postgres -d news_analysis_pg \
  -c "SELECT master_add_node('worker1', 5432); \
      SELECT master_add_node('worker2', 5432);"
```

**Output esperado:**
```
 master_add_node 
-----------------
               1
(1 row)

 master_add_node 
-----------------
               2
(1 row)
```

**Errores posibles y qué significan:**

| Error | Causa | Solución |
|-------|-------|----------|
| `connection to the remote node postgres@workerX:5432 failed` | Worker no está listo o no se aplicó trust | Verificar health de workers, repetir paso 2 |
| `fe_sendauth: no password supplied` | Trust no se aplicó correctamente. Es el error que estamos destrabando. | Verificar que `pg_hba.conf` tenga la línea `host all all 0.0.0.0/0 trust` al final del archivo y `pg_reload_conf()` haya devuelto `t` |
| `node already added` | Worker ya estaba registrado (caso worker1 si init.sql lo ejecutó antes) | No es error crítico. Continuar al paso 4 |

---

## 4. Verificar workers activos

**Motivo:** Confirmar que ambos workers están registrados y accesibles antes de cargar datos.

```bash
docker exec citus-coordinator psql -U postgres -d news_analysis_pg \
  -c "SELECT * FROM master_get_active_worker_nodes();"
```

**Output esperado:**
```
  node_name  | node_port
-------------+-----------
 worker1     |      5432
 worker2     |      5432
(2 rows)
```

**Si aparece solo 1 worker:** repetir paso 3 para el que falta.

---

## 5. Verificar tabla distribuida

**Motivo:** Asegurar que la tabla `milei_news` existe (creada por `init.sql` al arrancar el coordinator) antes de cargar datos.

```bash
docker exec citus-coordinator psql -U postgres -d news_analysis_pg \
  -c "SELECT COUNT(*) FROM milei_news;"
```

**Output esperado (si el `init.sql` se ejecutó correctamente):**
```
 count
-------
     0
(1 row)
```
La tabla existe pero está vacía (aún no cargamos datos).

**Si la tabla no existe:**
```bash
docker exec citus-coordinator psql -U postgres -d news_analysis_pg \
  -c "CREATE TABLE IF NOT EXISTS milei_news (id SERIAL PRIMARY KEY, news_paper TEXT, section TEXT, title TEXT, summary TEXT, published TIMESTAMP, link TEXT, tags TEXT, credit TEXT); SELECT create_distributed_table('milei_news', 'section'); CREATE INDEX idx_milei_news_published ON milei_news (published); CREATE INDEX idx_milei_news_newspaper ON milei_news USING hash (news_paper);"
  -c "CREATE INDEX idx_milei_news_text ON milei_news USING GIN (to_tsvector('spanish', coalesce(title,'') || ' ' || coalesce(summary,'')));"
```

---

## 6. Cargar datos

**Motivo:** Insertar los 2,224 registros del dataset limpio en la tabla distribuida `milei_news`. Citus distribuye automáticamente las filas entre worker1 y worker2 según el hash de `section`.

```bash
python citus/scripts/load_data.py
```

**Output esperado:**
```
Conectando a Citus coordinator...
Conexion exitosa.

Cargando datos desde: Z:\26-1\BD2\lab16\dataset\processed\milei_news_clean.json
Registros a insertar: 2224
  Progreso: 500/2224 (22%)
  Progreso: 1000/2224 (45%)
  ...
Insercion completada en X.XXs
Insertados: 2224

=== Tabla stats ===
Filas totales: 2224
Secciones unicas: 70
Periodicos unicos: 20
```

**Errores posibles:**

| Error | Causa | Solución |
|-------|-------|----------|
| `Connection refused` | Coordinator no está corriendo | `docker ps` para verificar, `docker compose up -d` si falta |
| `relation "milei_news" does not exist` | Tabla no creada | Ejecutar el CREATE TABLE del paso 5 |
| `psycopg2.OperationalError` | Puerto o credencial incorrecta | Verificar `localhost:5432`, user `postgres` |

---

## 7. Verificar distribución entre workers (pgAdmin)

En pgAdmin:
- Servidor: `localhost:5432`
- Database: `news_analysis_pg`
- Query:

```sql
SELECT nodename, nodeport, shardid, shardstate
FROM citus_shards
WHERE table_name::text = 'milei_news'
ORDER BY shardid;
```

**Output esperado:** 32 shards (por defecto) distribuidos entre los 2 workers (~16 cada uno).

---

## Resumen de outputs por paso

| Paso | Comando | Output clave |
|------|---------|-------------|
| 1 | `docker ps` | 3 containers healthy |
| 2 | `pg_reload_conf()` | `t` |
| 3 | `master_add_node` | `1`, luego `2` |
| 4 | Workers activos | 2 filas: worker1:5432, worker2:5432 |
| 5 | COUNT de tabla | 0 (vacía) |
| 6 | `load_data.py` | 2224 insertados |
| 7 | `citus_shards` | 32 shards entre 2 workers |

---

## Comprobación de seguridad: ¿es seguro trust en desarrollo?

| Preocupación | Realidad |
|-------------|----------|
| ¿Alguien externo puede conectarse? | No. `trust` aplica solo a conexiones dentro de la red `lab16_citus_net`. Los workers no exponen puertos al host (`5433`, `5434` sí, pero requieren llegar al contenedor) |
| ¿Otros contenedores Docker pueden acceder? | Solo los que están en `lab16_citus_net`. MongoDB está en `lab16_mongo_net` — redes separadas, sin acceso |
| ¿En producción haríamos esto? | No. En producción se usa `md5` + `.pgpass` o certificados SSL. Esto es un laboratorio de prueba en entorno local |
| ¿Es revertible? | Sí. La línea `host all all 0.0.0.0/0 trust` se puede eliminar de `pg_hba.conf` y recargar |

---

## Post-destrabe: lo que sigue

Una vez Citus esté cargado:

1. Verificar en pgAdmin que los datos están distribuidos
2. Abrir `citus/notebooks/citus_analysis.ipynb` en VS Code
3. Ejecutar todas las celdas (detecta conexión automáticamente y corre Q1-Q5 con EXPLAIN ANALYZE)
4. Capturar screenshots de EXPLAIN ANALYZE para P8/P10
5. Nos avisas cuando esté listo para que yo redacte el informe final