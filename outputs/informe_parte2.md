# Parte II: Citus en PostgreSQL (P6–P10)

> Informe de la Parte II del Laboratorio "MongoDB Distribuido vs Citus — Análisis Comparativo".
> Dataset: *News Headlines About President Milei* — campos: `news_paper`, `section`, `title`, `summary`, `published`, `link`, `tags`.
>
> **Instrucciones de uso:** completar cada bloque `📷 EVIDENCIA` con los screenshots/extracts
> generados al ejecutar el cluster y el notebook `citus/notebooks/citus_analysis.ipynb`.

---

## P6: ¿Cómo quedó configurado el cluster Citus? (1 pt)

El cluster se orquesta con Docker Compose (`citus/docker-compose.yml`) usando la imagen oficial `citusdata/citus:12.1`:

| Nodo | Contenedor | Puerto host | Rol |
|------|-----------|-------------|-----|
| Coordinator | `citus-coordinator` | 5435 | Recibe queries, planifica y coordina la ejecución distribuida |
| Worker 1 | `citus-worker1` | 5433 | Almacena y procesa shards |
| Worker 2 | `citus-worker2` | 5434 | Almacena y procesa shards |

- Base de datos: `news_analysis_pg` (usuario/password: `postgres`/`postgres`).
- Extensión `citus` habilitada en los tres nodos (`CREATE EXTENSION IF NOT EXISTS citus`).
- Los workers se registran en el coordinator con `citus_add_node('worker1', 5432)` y `citus_add_node('worker2', 5432)` (ver `citus/scripts/init.sql`, automatizado por `citus/scripts/setup_cluster.ps1`).
- Verificación: `SELECT * FROM citus_get_active_worker_nodes();` debe listar ambos workers.

**📷 EVIDENCIA (pegar aquí):**
- Screenshot de `citus_get_active_worker_nodes()` mostrando los 2 workers activos (terminal o pgAdmin).
- Screenshot de pgAdmin conectado a `localhost:5435` / `news_analysis_pg`.

---

## P7: ¿Qué estrategia de distribución se eligió y cómo quedó la distribución de shards entre workers? (1 pt)

**Estrategia elegida: HASH sobre `section`** (`create_distributed_table('milei_news', 'section')` — hash es el método por defecto de Citus).

**Justificación:**
- `section` tiene cardinalidad media (~70 valores tras la normalización) con distribución **muy sesgada**: pocas secciones ("Política", "Economía", "Últimas noticias") concentran gran parte de las noticias.
- Con **rango** habría que definir manualmente los límites entre secciones (son cadenas de texto sin orden natural útil) y el sesgo produciría shards desbalanceados.
- Con **hash**, Citus crea 32 shards por defecto y asigna cada valor de `section` a un shard según su hash, repartiendo los shards en round-robin entre los 2 workers (16 y 16). Esto amortigua el sesgo sin configuración manual.
- Además, la misma clave (`section`) se usa como shard key en MongoDB (Parte I), lo que hace la comparación P11 justa.

**Limitación conocida:** el hash distribuye *valores* de section, no *filas*; una sección muy dominante sigue cayendo entera en un solo shard. Es el mismo trade-off que en MongoDB con hashed shard key.

Verificación de la distribución:

```sql
SELECT nodename, count(*) AS shards
FROM citus_shards
WHERE table_name::text = 'milei_news'
GROUP BY nodename;

-- Filas por worker (tras la carga):
SELECT nodename, sum(shard_size) AS bytes
FROM citus_shards
WHERE table_name::text = 'milei_news'
GROUP BY nodename;
```

**📷 EVIDENCIA (pegar aquí):**
- Screenshot de la distribución de shards por worker (salida de `setup_cluster.ps1` o pgAdmin).
- Opcional: conteo de filas por worker tras la carga.

---

## P8: ¿Cómo funciona el índice GIN para búsqueda textual? ¿ts_rank usa TF-IDF? ¿Cómo se compara con el índice invertido de MongoDB? (2 pts)

### Funcionamiento del índice GIN

GIN (*Generalized Inverted Index*) es un **índice invertido**: para cada *lexema* (término normalizado por el stemmer de `to_tsvector('spanish', ...)`) almacena la lista de tuplas (posting list) que lo contienen.

- **Preprocesamiento:** `to_tsvector('spanish', title || ' ' || summary)` tokeniza, elimina *stop words* en español y aplica **stemming** (Snowball español): "inflación", "inflacionario" → `inflacion`.
- **Estructura:** un B-tree de lexemas cuyas hojas apuntan a *posting lists* comprimidas de TIDs; las listas grandes se almacenan como *posting trees*.
- **Consulta:** `@@ to_tsquery('spanish', 'dolar & inflacion')` busca cada lexema en el índice e **interseca** las posting lists — no escanea la tabla (Bitmap Index Scan en el plan).

### ¿ts_rank usa TF-IDF?

**No exactamente.** `ts_rank` se basa en la **frecuencia del término en el documento** (componente TF) ponderada por la posición/etiqueta del lexema (pesos A/B/C/D) y opcionalmente normalizada por la longitud del documento — pero **no incorpora IDF** (frecuencia inversa en el corpus). `ts_rank_cd` añade *cover density* (proximidad entre términos). Un TF-IDF real requeriría extensiones o cálculo manual.

### Comparación con el índice de texto de MongoDB

| Aspecto | Citus/PostgreSQL (GIN) | MongoDB (text index) |
|---|---|---|
| Estructura | Índice invertido (B-tree de lexemas + posting lists) | Índice invertido sobre términos stemmed |
| Stemming | Snowball por idioma (`spanish`) | Snowball por idioma (`default_language: spanish`) |
| Ranking | `ts_rank`: TF + pesos por campo, **sin IDF** | `textScore`: variante TF-IDF simplificada por campo |
| Sintaxis de consulta | Álgebra booleana completa: `&`, `\|`, `!`, `<->` (frase) | Lista de términos, frases con comillas, exclusión con `-` |
| Ejecución distribuida | El coordinator reenvía la query a cada shard; cada worker usa su GIN local y el coordinator mezcla y re-ordena | mongos hace scatter-gather a los shards; cada shard usa su índice de texto local y mongos mezcla por textScore |

**📷 EVIDENCIA (pegar aquí):**
- Extract del `EXPLAIN ANALYZE` de Q1 desde el notebook, señalando el nodo `Bitmap Index Scan on idx_milei_news_text` dentro de las *tasks* del `Custom Scan (Citus Adaptive)`.

---

## P9: ¿Cuáles son los tiempos de Q1–Q5 en Citus? ¿Qué tipo de consulta es más eficiente? (2 pts)

Tiempos medidos por el notebook (`citus/notebooks/citus_analysis.ipynb`, sección P9), que también los exporta a `outputs/citus_tiempos.csv`.

| Query | Descripción | Tiempo (ms) |
|-------|-------------|-------------|
| Q1 | Búsqueda textual multi-término (`ts_rank`) | *(completar)* |
| Q2 | Búsqueda con exclusión (`!Twitter`) | *(completar)* |
| Q3 | Top 10 por fecha (`ORDER BY published DESC LIMIT 10`) | *(completar)* |
| Q4 | `GROUP BY section` (clave de distribución) | *(completar)* |
| Q5 | `GROUP BY news_paper` (atributo no particionado) | *(completar)* |

**Análisis (ajustar con los datos reales):**
- Se espera que **Q3** sea la más rápida: usa el índice B+Tree sobre `published` en cada shard y solo mezcla 10 filas por task en el coordinator.
- **Q4** debería superar a **Q5**: al agrupar por la clave de distribución, cada grupo vive completo en un shard y la agregación se completa localmente; en Q5 cada worker produce agregados parciales por `news_paper` que el coordinator debe re-agrupar (scatter/gather).
- **Q1/Q2** dependen del GIN: son eficientes frente a un scan secuencial, pero pagan el cálculo de `ts_rank` y el re-ordenamiento global por relevancia en el coordinator.

**📷 EVIDENCIA (pegar aquí):**
- Screenshot de la tabla pandas y del gráfico de barras generados por el notebook.

---

## P10: ¿Cómo Citus distribuye y paraleliza cada tipo de consulta? ¿Se detecta overhead de coordinación? (2 pts)

En los `EXPLAIN ANALYZE` de **todas** las queries aparece el nodo **`Custom Scan (Citus Adaptive)`** con **`Task Count: 32`**: el coordinator reescribe la consulta en 32 *tasks* (una por shard) y las ejecuta en paralelo sobre los 2 workers (16 shards cada uno). Cada task es SQL normal de PostgreSQL corriendo contra el shard local (`milei_news_102xxx`), con sus índices locales.

**Cómo se distribuye cada tipo de consulta:**

- **Q1/Q2 (búsqueda textual):** cada task hace `Bitmap Index Scan` sobre el GIN local de su shard y ordena parcialmente por `ts_rank`; el coordinator mezcla las filas candidatas de las 32 tasks y aplica el `Sort` global por relevancia. Overhead: el ordenamiento final y el cálculo de rank no se pueden delegar del todo.
- **Q3 (top-N por fecha):** Citus hace *push-down* del `ORDER BY published DESC LIMIT 10` a cada task (cada shard devuelve máximo 10 filas usando su B+Tree local) y el coordinator mezcla 320 filas como máximo. Overhead mínimo.
- **Q4 (GROUP BY `section`, clave de distribución):** agregación **completamente local**. Como cada valor de `section` vive entero en un único shard, cada task devuelve grupos ya finales y el plan del coordinator es solo `Sort → Custom Scan` — **no hay re-agregación arriba del Custom Scan**. Es el caso ideal del particionamiento. Medido: el coordinator recibió apenas 1,298 bytes (70 grupos finales); tiempo total 25.0 ms.
- **Q5 (GROUP BY `news_paper`, atributo no particionado):** agregación en **dos fases**. Cada task calcula `count(*)` parcial por `news_paper`, y en el plan del coordinator aparece un **`HashAggregate` por encima del Custom Scan** con `Group Key: remote_scan.news_paper` y `sum(remote_scan.cnt)` — la re-agregación de los parciales. Medido: viajaron 107 filas parciales (2,077 bytes) que el coordinator redujo a 20 grupos; tiempo total 38.2 ms.

**Overhead de coordinación — sí, se detecta y se cuantifica:** en Q4 la task individual tardó **0.21 ms** y en Q5 **0.24 ms**, pero los tiempos totales fueron **25 ms y 38 ms**: más del 99% del tiempo es coordinación (planificar y despachar 32 tasks, conexiones a workers, recolección y merge), no procesamiento de datos. Con solo 2,224 filas el paralelismo no compensa ese costo fijo — un PostgreSQL sin distribuir sería más rápido. La comparación Q4 (25 ms, sin re-agregación) vs Q5 (38 ms, con re-agregación y más tuplas transferidas) muestra además el costo extra de agrupar por un atributo que no es la clave de distribución: **+52% de tiempo**.

**📷 EVIDENCIA (pegar aquí):**
- Extract de `EXPLAIN ANALYZE` de Q4: señalar `Custom Scan (Citus Adaptive)`, `Task Count: 32`, el `HashAggregate` **dentro** de la task, y que **no** hay agregación sobre el Custom Scan.
- Extract de `EXPLAIN ANALYZE` de Q5: señalar el `HashAggregate` con `Group Key: remote_scan.news_paper` **encima** del Custom Scan (la segunda fase) y el `sum(remote_scan.cnt)` en el Sort.
- Comparar en ambos: `Execution Time` de la task (~0.2 ms) vs `Execution Time` total (25–38 ms) → overhead de coordinación.

---

## Anexo: cómo reproducir

```powershell
# 1. Entorno (una sola vez)
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Dataset (una sola vez) — colocar el dataset crudo en dataset/ y limpiar
.venv\Scripts\python.exe scripts/clean_and_extract.py

# 3. Cluster Citus (levanta, registra workers, crea tabla distribuida + índices)
powershell -ExecutionPolicy Bypass -File citus/scripts/setup_cluster.ps1

# 4. Carga de datos
.venv\Scripts\python.exe citus/scripts/load_data.py

# 5. Notebook (seleccionar el kernel .venv en VS Code)
#    citus/notebooks/citus_analysis.ipynb  → ejecutar todo
```
