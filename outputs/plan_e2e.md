# Plan de Trabajo E2E — BD2 Lab 16

**MongoDB Sharding vs Citus — Análisis Comparativo de Búsqueda Textual Distribuida**

---

## 1. Fases del Proyecto

| Fase | Descripción | Estado | Responsable |
|------|-------------|--------|-------------|
| 0 | Setup del repositorio y documentación base | ✅ Completado | IA + Humano |
| 1 | Limpieza y extracción del dataset | ✅ Completado | IA + Humano |
| 2 | Infraestructura MongoDB | ✅ Completado | IA genera / Humano ejecuta |
| 3 | Carga de datos en MongoDB | ✅ Completado | IA genera / Humano ejecuta |
| 4 | Infraestructura Citus | ⏳ Pendiente | IA genera / Humano ejecuta |
| 5 | Carga de datos en Citus | ⏳ Pendiente | IA genera / Humano ejecuta |
| 6 | Ejecución de notebooks de análisis | ⏳ Pendiente | IA genera / Humano ejecuta |
| 7 | Captura de screenshots y evidencias | ⏳ Pendiente | Humano |
| 8 | Redacción del informe final (informe.md) | ⏳ Pendiente | IA |
| 9 | Revisión y conversión a PDF | ⏳ Pendiente | Humano |

---

## 2. Detalle por Fase

### Fase 0: Setup del Repositorio ✅

| Actividad | Estado | Evidencia |
|-----------|--------|-----------|
| Crear AGENTS.md | ✅ | `AGENTS.md` |
| Crear README.md | ✅ | `README.md` |
| Crear requirements.txt | ✅ | `requirements.txt` |
| Crear .gitignore | ✅ | `.gitignore` (heredero del repo base) |
| Crear outputs/plan/ | ✅ | `outputs/sistema_trabajo.md` |
| Crear guía rápida de config | ✅ | `outputs/configs/guia_rapida.md` |
| Configurar remote y push inicial | ✅ | `git push origin main` |

### Fase 1: Limpieza del Dataset ✅

| Actividad | Estado | Detalle |
|-----------|--------|---------|
| Inspeccionar estructura de archivos JSON | ✅ | 24,101 archivos, anidados como `país/medio/sección/fecha.json` |
| Analizar formato y encoding | ✅ | utf-8 / latin-1 / cp1252; 34.8% parseable |
| Implementar parser tolerante | ✅ | Fallback de encodings, eliminación de caracteres de control |
| Normalizar campo `section` | ✅ | 106 → 70 valores (strip, prefijos, mapeo explícito) |
| Parsear fechas con dateutil | ✅ | 0 registros sin fecha en el dataset final |
| Limpiar HTML en summaries | ✅ | BeautifulSoup para extraer texto plano |
| Deduplicar por (link, title) | ✅ | 9,784 → 2,224 registros únicos |
| Exportar dataset limpio | ✅ | `dataset/processed/milei_news_clean.json` y `.csv` |
| Documentar hallazgos | ✅ | `outputs/informe_data.md` |

**Script:** `scripts/clean_and_extract.py`

### Fase 2: Infraestructura MongoDB ✅

| Actividad | Estado | Detalle |
|-----------|--------|---------|
| Crear docker-compose MongoDB | ✅ | mongocfg (config server) + shard1 + shard2 + mongos |
| Inicializar replica sets | ✅ | cfgrs, shard1rs, shard2rs |
| Agregar shards al mongos | ✅ | `sh.addShard()` |
| Habilitar sharding en `news_analysis` | ✅ | `sh.enableSharding()` |
| Shard collection por `section` (hash) | ✅ | `sh.shardCollection()` |
| Crear índices | ✅ | published (simple), news_paper (hash), title+summary (text spanish) |
| Verificar cluster en Compass | ✅ | `mongodb://localhost:27017` → `news_analysis.milei_news` |

**Archivos:**
- `mongodb/docker-compose.yml`
- `mongodb/scripts/init-sharding.js`

### Fase 3: Carga de Datos en MongoDB ✅

| Actividad | Estado | Detalle |
|-----------|--------|---------|
| Conectar a mongos via pymongo | ✅ | `MongoClient("mongodb://localhost:27017")` |
| Bulk insert en batches de 500 | ✅ | `insert_many(ordered=False)` |
| Verificar documentos totales | ✅ | 2,224 documentos |
| Verificar secciones únicas | ✅ | 70 secciones |
| Verificar periódicos únicos | ✅ | 20 periódicos |

**Script:** `mongodb/scripts/load_data.py`

### Fase 4: Infraestructura Citus ⏳

| Actividad | Estado | Comando / Detalle |
|-----------|--------|-------------------|
| Crear docker-compose Citus | ✅ (script listo) | coordinator + worker1 + worker2 |
| Levantar servicios | ⏳ | `cd citus && docker compose up -d` |
| Agregar workers al coordinator | ⏳ | `SELECT master_add_node('worker1', 5432); master_add_node('worker2', 5432);` |
| Ejecutar init.sql | ⏳ | DDL, extensión citus, índices GIN/BTree/Hash |
| Verificar workers activos | ⏳ | `SELECT * FROM master_get_active_worker_nodes();` |

**Archivos:**
- `citus/docker-compose.yml`
- `citus/scripts/init.sql`

### Fase 5: Carga de Datos en Citus ⏳

| Actividad | Estado | Detalle |
|-----------|--------|---------|
| Conectar a Citus coordinator | ⏳ | `psycopg2.connect()` |
| Batch insert (500 registros) | ⏳ | `execute_values` o cursor.mogrify |
| Verificar filas totales | ⏳ | Esperado: 2,224 |
| Verificar distribución entre workers | ⏳ | `SELECT * FROM citus_shards;` |

**Script:** `citus/scripts/load_data.py`

### Fase 6: Ejecución de Notebooks ⏳

| Notebook | Queries | Explicación | Evidencia a capturar |
|----------|---------|-------------|---------------------|
| `mongodb/notebooks/mongo_analysis.ipynb` | Q1-Q5 | `explain("executionStats")` | executionStages, shards[], totalDocsExamined |
| `citus/notebooks/citus_analysis.ipynb` | Q1-Q5 | `EXPLAIN ANALYZE` | Custom Scan (Citus), Task Count, worker timelines |

**Queries a implementar:**

| # | Tipo | MongoDB | Citus |
|---|------|---------|-------|
| Q1 | Búsqueda textual multi-término | `$text: { $search: "dolar inflacion" }` + `$meta textScore` | `to_tsvector('spanish', ...) @@ to_tsquery('spanish', 'dolar & inflacion')` + `ts_rank` |
| Q2 | Búsqueda con exclusión | `$text: { $search: "Milei -Twitter" }` | `to_tsquery('spanish', 'Milei & !Twitter')` |
| Q3 | Top 10 por fecha | `sort({published:-1}).limit(10)` | `ORDER BY published DESC LIMIT 10` |
| Q4 | GROUP BY shard key (section) | `$group` por `section` | `GROUP BY section` (local a cada worker) |
| Q5 | GROUP BY no particionado (news_paper) | `$group` por `news_paper` | `GROUP BY news_paper` (scatter/gather) |

**Métricas a registrar por query:**
- Tiempo de ejecución (ms)
- Total de documentos examinados vs retornados
- Número de shards/workers involucrados
- Etapas del plan de ejecución

### Fase 7: Captura de Screenshots ⏳

| # | Captura | Sistema | Herramienta |
|---|---------|---------|-------------|
| P1 | `sh.status()` con shards activos | MongoDB | Compass / mongosh |
| P1 | Vista de colección en Compass | MongoDB | Compass |
| P3 | Distribución de chunks | MongoDB | `db.milei_news.getShardDistribution()` |
| P4 | Extracto de `explain("executionStats")` | MongoDB | Notebook |
| P6 | Workers activos en Citus | Citus | pgAdmin / psql |
| P7 | Distribución de shards entre workers | Citus | `citus_shards` |
| P8 | Extracto de `EXPLAIN ANALYZE` | Citus | Notebook |
| P10 | Plan de ejecución con Custom Scan (Citus) | Citus | Notebook |

**Carpetas de destino:**
- `outputs/screenshots/` — screenshots globales
- `mongodb/screenshots/` — específicos de MongoDB
- `citus/screenshots/` — específicos de Citus

### Fase 8: Redacción del Informe Final ⏳

**Estructura de `outputs/informe.md`:**

1. Portada (título, autores, fecha)
2. Metodología
3. Resultados MongoDB (P1-P5)
4. Resultados Citus (P6-P10)
5. Comparación (P11)
6. Conclusiones y recomendación (P12)
7. Anexos (screenshots, tablas completas)

**Formato de evidencia por pregunta:**
- P1: Tabla de configuración + screenshot
- P2: Tabla de estadísticas del dataset
- P3: Análisis de cardinalidad + screenshot de chunks
- P4: Extracto de explain + investigación documentada
- P5: Tabla pandas con tiempos Q1-Q5
- P6: Screenshot de workers
- P7: Justificación + screenshot de distribución
- P8: Extracto EXPLAIN ANALYZE + investigación
- P9: Tabla pandas con tiempos Q1-Q5
- P10: Extracto EXPLAIN ANALYZE con Custom Scan
- P11: Tabla/gráfico comparativo
- P12: Síntesis + recomendación

### Fase 9: Conversión a PDF ⏳

| Actividad | Responsable |
|-----------|-------------|
| Revisar contenido del informe.md | Humano |
| Corregir errores o inconsistencias | Humano + IA |
| Convertir .md a PDF (Typora, pandoc, o similar) | Humano |
| Subir PDF final al repositorio | Humano |

---

## 3. Buenas Prácticas Aplicadas

### Control de Versiones
- Commits atómicos por funcionalidad
- Mensajes descriptivos con prefijo semántico (`feat:`, `docs:`, `fix:`)
- Push después de cada hito completado

### Gestión de Dependencias
- `requirements.txt` con rangos flexibles (`>=X,<Y`)
- Sin versiones pinzadas para evitar conflictos

### Docker
- Healthchecks en todos los servicios
- `depends_on` con `condition: service_healthy` / `service_completed_successfully`
- Redes aisladas por sistema (`lab16_mongo_net`, `lab16_citus_net`)
- Volúmenes nombrados para persistencia de datos

### Código
- Separación de concerns: limpieza ≠ carga ≠ análisis
- Idempotencia: los scripts de carga truncan/reemplazan antes de insertar
- Detección automática de conexión en notebooks (modo offline/online)

---

## 4. Checkpoint Actual

```
Fase 0: ✅  Fase 1: ✅  Fase 2: ✅  Fase 3: ✅
Fase 4: ⏳  Fase 5: ⏳  Fase 6: ⏳  Fase 7: ⏳
Fase 8: ⏳  Fase 9: ⏳
```

**Siguiente paso inmediato:** Fase 4 — Agregar workers a Citus y cargar datos.

```bash
# En terminal:
docker exec citus-coordinator psql -U postgres -d news_analysis_pg \
  -c "SELECT master_add_node('worker1', 5432); SELECT master_add_node('worker2', 5432);"

# Luego:
python citus/scripts/load_data.py
```

---

## 5. Estructura de Archivos Actualizada

```
Z:\26-1\BD2\lab16\
├── AGENTS.md
├── README.md
├── requirements.txt
├── .gitignore
├── lab_mongo.pdf
├── dataset/
│   ├── processed/
│   │   ├── milei_news_clean.json
│   │   └── milei_news_clean.csv
│   └── (archivos fuente)
├── scripts/
│   └── clean_and_extract.py
├── outputs/
│   ├── configs/
│   │   └── guia_rapida.md
│   ├── plan_e2e.md              ← este archivo
│   ├── informe_data.md
│   ├── screenshots/
│   └── sistema_trabajo.md
├── mongodb/
│   ├── docker-compose.yml
│   ├── scripts/
│   │   ├── init-sharding.js
│   │   └── load_data.py
│   ├── notebooks/
│   │   └── mongo_analysis.ipynb
│   └── screenshots/
└── citus/
    ├── docker-compose.yml
    ├── scripts/
    │   ├── init.sql
    │   └── load_data.py
    ├── notebooks/
    │   └── citus_analysis.ipynb
    └── screenshots/
```

---

*Documento actualizado: Julio 2026*
*Próxima actualización: al completar la Fase 5 (Carga Citus)*
