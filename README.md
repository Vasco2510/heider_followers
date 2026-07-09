# BD2 Lab 16 — MongoDB Sharding vs Citus

**Análisis comparativo de búsqueda textual distribuida** entre MongoDB Sharding y Citus (PostgreSQL distribuido) sobre un dataset de noticias sobre el presidente Javier Milei.

## Tabla de Contenidos

1. [Descripción del Proyecto](#descripcion-del-proyecto)
2. [Dataset](#dataset)
3. [Estructura del Repositorio](#estructura-del-repositorio)
4. [Requisitos](#requisitos)
5. [Instalación](#instalacion)
6. [Ejecución Paso a Paso](#ejecucion-paso-a-paso)
7. [Consultas de Referencia](#consultas-de-referencia-q1q5)
8. [Evaluación](#evaluacion-p1p12)
9. [Herramientas](#herramientas)
10. [Autores](#autores)

---

## Descripción del Proyecto

Se implementan dos sistemas de bases de datos distribuidas para analizar y comparar su rendimiento en búsqueda textual y agregaciones:

| Sistema | Stack | Particionamiento |
|---------|-------|-----------------|
| MongoDB | Sharding (mongos + config + 2 shards) | Hash sobre `section` |
| Citus | Coordinator + 2 Workers | Hash sobre `section` |

Ambos sistemas cargan el mismo dataset, ejecutan 5 consultas idénticas en lógica, y se analizan con sus respectivas herramientas de explicación de planes de ejecución (`explain("executionStats")` en MongoDB, `EXPLAIN ANALYZE` en Citus).

## Dataset

**"News Headlines About President Milei"**: 24,102 archivos JSON anidados en `dataset/` con la estructura `país/medio/sección/fecha.json`.

| Métrica | Valor |
|---------|-------|
| Archivos parseables | 8,387 (34.8%) |
| Noticias únicas extraídas | 2,224 |
| Secciones normalizadas | 106 → 70 |
| Periódicos distintos | 20 |
| Registros sin fecha | 0 |

> El detalle completo de la limpieza está en [`outputs/informe_data.md`](outputs/informe_data.md).

## Estructura del Repositorio

```
lab16/
├── AGENTS.md                             # Instrucciones para agentes IA
├── README.md                            # Este archivo
├── requirements.txt                       # Dependencias Python
├── lab_mongo.pdf                        # Enunciado original
├── dataset/
│   ├── processed/                       # Datos limpios (JSON + CSV)
│   └── (archivos JSON fuente)
├── scripts/
│   └── clean_and_extract.py             # Limpieza y extracción del dataset
├── outputs/
│   ├── configs/
│   │   └── guia_rapida.md               # Puertos, credenciales, conexiones
│   ├── screenshots/                   # Capturas de evidencia
│   ├── informe_data.md                # Análisis del dataset
│   ├── informe.md                     # Informe final P1-P12
│   ├── informe_parte2.md              # Parte II (Citus): P6-P10 con evidencia
│   └── sistema_trabajo.md               # Plan de trabajo detallado
├── mongodb/
│   ├── docker-compose.yml              # Cluster MongoDB Sharding
│   ├── scripts/
│   │   ├── init-sharding.js            # Habilitar sharding + índices
│   │   └── load_data.py               # Carga de datos
│   ├── notebooks/
│   │   └── mongo_analysis.ipynb       # Análisis Q1-Q5
│   └── screenshots/                   # Screenshots MongoDB
└── citus/
    ├── docker-compose.yml              # Cluster Citus
    ├── scripts/
    │   ├── init.sql                    # Workers + DDL + tabla distribuida + índices
    │   ├── setup_cluster.ps1           # Setup automatizado del cluster (Windows)
    │   └── load_data.py               # Carga de datos
    ├── notebooks/
    │   └── citus_analysis.ipynb       # Análisis Q1-Q5
    └── screenshots/                   # Screenshots Citus
```

## Requisitos

- **Docker** y **Docker Compose** (v2.x+)
- **Python** ≥ 3.10
- **MongoDB Compass** (opcional, para verificar sharding)
- **pgAdmin** (opcional, para verificar workers Citus)
- **VS Code** con extensión Jupyter (para notebooks)

## Instalación

```powershell
# 1. Clonar el repositorio
git clone <repo-url> lab16
cd lab16

# 2. Crear entorno virtual e instalar dependencias
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Colocar el dataset crudo en dataset/ (subcarpetas Argentina/ y World/) y limpiarlo
.venv\Scripts\python.exe scripts/clean_and_extract.py
```

> En VS Code, seleccionar el intérprete/kernel `.venv` para ejecutar los notebooks.

## Ejecución Paso a Paso

### Paso 1: Limpieza del Dataset
```bash
python scripts/clean_and_extract.py
```
Genera `dataset/processed/milei_news_clean.json` y `.csv`.

### Paso 2: MongoDB Sharding
```bash
cd mongodb
docker compose up -d
# Esperar ~30s a que se inicialicen replica sets y sharding
python scripts/load_data.py
```
Verificar con Compass: `mongodb://localhost:27017` → db `news_analysis`.

### Paso 3: Citus
```powershell
# Levanta el cluster, espera healthchecks, registra workers y crea tabla distribuida + índices
powershell -ExecutionPolicy Bypass -File citus/scripts/setup_cluster.ps1

# Cargar datos
.venv\Scripts\python.exe citus/scripts/load_data.py
```

Equivalente manual (si no se usa el script):
```bash
cd citus
docker compose up -d
# Esperar a que los 3 contenedores estén healthy (docker ps)
docker exec citus-coordinator psql -U postgres -d news_analysis_pg -v ON_ERROR_STOP=1 -f /scripts/init.sql
```
Verificar con pgAdmin: `localhost:5432`, db `news_analysis_pg`.

### Paso 4: Ejecutar Notebooks
Abrir en VS Code:
- `mongodb/notebooks/mongo_analysis.ipynb`
- `citus/notebooks/citus_analysis.ipynb`

Los notebooks funcionan en dos modos:
- **Sin cluster** → tablas/gráficos desde el JSON limpio
- **Con cluster** → ejecuta queries reales con `explain("executionStats")` / `EXPLAIN ANALYZE`

### Paso 5: Capturar Screenshots
- `sh.status()` en MongoDB Compass
- Workers activos en pgAdmin
- Extracts de explain/EXPLAIN ANALYZE desde los notebooks
- Distribución de chunks/shards

Guardar en `outputs/screenshots/`, `mongodb/screenshots/` y `citus/screenshots/`.

### Paso 6: Generar Informe Final
1. Completar `outputs/informe.md` con los resultados de los notebooks
2. Convertir a PDF (typora, pandoc, o similar)

## Consultas de Referencia (Q1–Q5)

| # | Tipo | MongoDB | Citus |
|---|------|---------|-------|
| Q1 | Búsqueda textual multi-término | `$text: { $search: "dolar inflacion" }` + `$meta textScore` | `to_tsvector @@ to_tsquery` + `ts_rank` |
| Q2 | Búsqueda con exclusión | `$text: { $search: "Milei -Twitter" }` | `to_tsquery('Milei & !Twitter')` |
| Q3 | Top 10 por fecha | `sort({published:-1}).limit(10)` | `ORDER BY published DESC LIMIT 10` |
| Q4 | GROUP BY shard key (section) | `$group` por `section` | `GROUP BY section` (local) |
| Q5 | GROUP BY no particionado (news_paper) | `$group` por `news_paper` | `GROUP BY news_paper` (scatter/gather) |

## Evaluación (P1–P12)

| # | Pregunta | Evidencia |
|---|---------|---------|
| P1 | Configuración del cluster MongoDB | Screenshot sh.status() + Compass |
| P2 | Limpieza del dataset | Tabla estadísticas |
| P3 | Estrategia de partición / balance de chunks | Análisis frecuencia secciones + Captura distribución chunks |
| P4 | Índice de texto (invertido, TF-IDF, stemming) | Extract explain("executionStats") |
| P5 | Tiempos Q1-Q5 MongoDB | Tabla pandas |
| P6 | Configuración cluster Citus | Screenshot workers activos |
| P7 | Estrategia distribución Citus | Justificación + screenshot |
| P8 | Índice GIN vs invertido MongoDB | Extract EXPLAIN ANALYZE |
| P9 | Tiempos Q1-Q5 Citus | Tabla pandas |
| P10 | Paralelización Citus (overhead coordinación) | Extract EXPLAIN ANALYZE (Custom Scan) |
| P11 | Comparativa Q1-Q5 ambos sistemas | Tabla/gráfico comparativo |
| P12 | Recomendación final | Síntesis técnica con evidencia |

## Herramientas

| Herramienta | Uso |
|-------------|-----|
| Docker Compose | Orquestación de clusters |
| MongoDB Compass | Verificación visual sharding |
| pgAdmin | Verificación workers Citus |
| VS Code | Edición + ejecución notebooks |
| Pandas | Análisis de datos y tablas |
| Matplotlib | Gráficos comparativos |

## Autores

- **DeepSeek (IA)** — Generación de scripts, docker-compose, notebooks, informes
- **Humano** — Ejecución Docker, captura de screenshots, revisión, conversión a PDF

---

*Base de Datos II — Prof. Heider Sanchez — 2026-1*