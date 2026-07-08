# Sistema de Trabajo — BD2 Lab 16: MongoDB Sharding vs Citus

## Objetivo

Implementar y comparar búsqueda textual distribuida entre MongoDB (Sharding con 2 shards) y Citus PostgreSQL (2 workers), usando el dataset "News Headlines About President Milei". Generar informe PDF, 2 notebooks Jupyter, scripts Docker y screenshots.

## Fases del Proyecto

### Fase 0: Estado Actual
- Dataset inspeccionado: 9,781 noticias extraídas de 24,102 archivos JSON
- 65% de archivos no parseables (requieren estrategia de recuperación más tolerante)
- Problemas conocidos: encoding corrupto, 106 secciones que normalizar a ~50, fechas en múltiples formatos
- Ver `outputs/informe_data.md` para análisis completo

### Fase 1: Scripts de Infraestructura
- **IA genera:** `mongodb/docker-compose.yml`, `citus/docker-compose.yml`
- **IA genera:** scripts de limpieza y carga (`load_data.py` para ambos sistemas)
- **IA genera:** scripts de índices (`init-sharding.js`, `init.sql`)
- **Humano ejecuta:** `docker compose up -d` en cada carpeta
- **Humano ejecuta:** scripts de carga e índices
- **Humano captura:** `sh.status()`, workers activos, Compass/pgAdmin

### Fase 2: Notebooks de Análisis
- **IA genera:** `mongodb/notebooks/mongo_analysis.ipynb` (Q1-Q5 + explain + tiempos)
- **IA genera:** `citus/notebooks/citus_analysis.ipynb` (Q1-Q5 + EXPLAIN ANALYZE + tiempos)
- **Humano ejecuta:** ambos notebooks en VS Code
- **Humano captura:** screenshots de EXPLAIN/explain para cada query

### Fase 3: Informe Final
- **IA escribe:** `outputs/informe.md` responde P1-P12 con evidencia de los notebooks
- **Humano revisa:** contenido, corrige si necesario
- **Humano convierte:** informe.md → PDF final

## División de Responsabilidades

| Rol | Hace | No hace |
|-----|------|---------|
| **IA (DeepSeek)** | Escribir todo el código, scripts, notebooks, informes .md | Ejecutar Docker, descargar datasets, capturar screenshots, convertir a PDF |
| **Humano** | Descargar dataset, ejecutar Docker, ejecutar scripts, capturar screenshots en Compass/pgAdmin/terminal, ejecutar notebooks, revisar contenido, convertir a PDF | Escribir código de análisis, generar queries complejas |

## Estructura de Archivos

```
Z:\26-1\BD2\lab16\
├── AGENTS.md                    # Instrucciones rápidas para IA
├── lab_mongo.pdf               # Enunciado original
├── dataset/
│   └── (archivos JSON anidados)
├── outputs/
│   ├── configs/
│   │   └── guia_rapida.md       # Puertos, users, conexiones
│   ├── screenshots/             # Capturas de pantalla
│   ├── informe_data.md          # Análisis actual del dataset
│   ├── informe.md               # Informe final P1-P12 (en progreso)
│   └── sistema_trabajo.md       # Este archivo
├── mongodb/
│   ├── docker-compose.yml
│   ├── scripts/
│   │   ├── init-sharding.js
│   │   └── load_data.py
│   └── notebooks/
│       └── mongo_analysis.ipynb
├── citus/
│   ├── docker-compose.yml
│   ├── scripts/
│   │   ├── init.sql
│   │   └── load_data.py
│   └── notebooks/
│       └── citus_analysis.ipynb
└── README.md
```

## Consultas de Referencia (Q1-Q5)

| # | Tipo | Sistema | Notas |
|---|------|---------|-------|
| Q1 | Búsqueda textual múltiples términos | MongoDB: `$text` + `$meta textScore` / Citus: `to_tsvector` + `ts_rank` | Orden por relevancia descendente |
| Q2 | Búsqueda con exclusión | MongoDB: `$text` con `-termino` / Citus: `to_tsquery('!termino')` | Orden por fecha |
| Q3 | Top 10 por fecha | MongoDB: `sort({published:-1}).limit(10)` / Citus: `ORDER BY published DESC LIMIT 10` | Simple |
| Q4 | Agregación por shard key | MongoDB: `$group` por `section` / Citus: `GROUP BY section` | Local si section es shard key |
| Q5 | Agregación no particionada | MongoDB: `$group` por `news_paper` / Citus: `GROUP BY news_paper` | Scatter/gather, más caro |

## Evaluación (P1-P12)

Todas las preguntas deben responderse en orden en el informe, con evidencia:

| # | Tema | Evidencia |
|---|------|-----------|
| P1 | Config cluster MongoDB | Screenshot sh.status() + Compass |
| P2 | Limpieza dataset | Tabla stats (registros, nulos, distribución section) |
| P3 | Estrategia partición MongoDB | Análisis frecuencia secciones + distribución chunks |
| P4 | Índice texto MongoDB | Extract explain("executionStats") |
| P5 | Tiempos Q1-Q5 MongoDB | Tabla pandas |
| P6 | Configuración Citus | Screenshot workers activos |
| P7 | Distribución Citus | Justificación + screenshot |
| P8 | Índice GIN vs invertido MongoDB | Extract EXPLAIN ANALYZE |
| P9 | Tiempos Q1-Q5 Citus | Tabla pandas |
| P10 | Paralelización Citus | Extract EXPLAIN ANALYZE (Custom Scan) |
| P11 | Comparativa Q1-Q5 | Tabla/gráfico ambos sistemas |
| P12 | Recomendación final | Síntesis técnica |

## Quick Start para próxima IA

1. Leer `AGENTS.md` y `outputs/sistema_trabajo.md`
2. Revisar `outputs/informe_data.md` para entender el dataset
3. Leer `outputs/configs/guia_rapida.md` para conexiones
4. Verificar archivos existentes en `mongodb/` y `citus/`
5. Si faltan archivos, crearlos según lo especificado
6. Si el humano ya ejecutó scripts, revisar `outputs/screenshots/` para evidencia
7. Preguntar al humano solo si la información faltante no está en estos archivos

## Reconocimiento entre sesiones

Para retomar el trabajo, la IA debe:
- Verificar qué archivos existen en cada carpeta
- Leer el último informe generado
- Preguntar al humano: "¿Qué fase completaste? ¿Qué screenshots/resultados tienes?"
- No regenerar archivos que ya existen sin consultar