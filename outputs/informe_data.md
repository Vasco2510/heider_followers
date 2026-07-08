# Informe de Estado Actual del Dataset

## Resumen

| Métrica | Valor |
|---------|-------|
| Archivos JSON totales | 24,101 |
| Archivos parseables | 8,387 (34.8%) |
| Archivos corruptos/no-parseables | 15,714 (65.2%) |
| Noticias extraídas (pre-dedup) | 9,784 |
| Duplicados eliminados (link+title) | 7,560 |
| **Registros únicos finales** | **2,224** |
| Secciones únicas (raw → normalizadas) | 106 → 70 |
| Noticias sin fecha | 0 |
| Noticias sin summary | 121 (5.4%) |

## Estructura de campos por noticia (dataset limpio)

| Campo | Tipo | % completitud |
|-------|------|--------------|
| `news_paper` | string | 100% |
| `section` | string | 100% |
| `title` | string | 100% |
| `summary` | string | 94.6% |
| `published` | datetime | 100% |
| `link` | string | 100% |
| `tags` | string | ~57% |
| `credit` | string | ~31% |

## Problemas Encontrados y Acciones Tomadas

### 1. Archivos no parseables (65.2% → se mantiene)
Los archivos de la carpeta `World/` (TheWashingtonPost, TheGuardian, NYT, AlJazeera, etc.) y el 65% de los de Argentina no pasaron el parser incluso con estrategia tolerante (utf-8 → latin-1 → cp1252 con `errors='replace'` y `strict=False`). **Causa probable:** algunos archivos están truncados (cortados a mitad del JSON) o contienen caracteres de control binarios que rompen el parser de Python.

**Decisión:** Se acepta el subconjunto de 8,387 archivos parseables (2,224 registros únicos). Es suficiente para el laboratorio.

### 2. Encoding inconsistente
Aplicado `errors='replace'` en la lectura + `re.sub(r'[\x00-\x1F]')` para eliminar caracteres de control. Los caracteres acentuados corruptos en los JSON fuente (e.g. `Política` como `Pol�tica`) son un problema del dataset original que persiste en el output. MongoDB y PostgreSQL lo almacenan tal cual; las búsquedas textuales funcionan sobre los bytes disponibles.

### 3. Normalización de section (106 → 70)
Se aplicó:
- `strip()` en todos los valores
- Regex para remover prefijos: `ediciones -`, `secciones -`, `titulares -`, `multimedia -`
- Mapeo explícito `SECTION_NORMALIZE` con 50+ entradas (acentos, truncados, espacios)
- `title()` como fallback

**Resultado:** de 106 secciones raw a 70 distintas. Quedan ~20 valores raros (1-2 registros cada uno) que no se pudieron mapear automáticamente (e.g. `Metadata`, `Foja Cero`, `Informe de Domingo`).

### 4. Fechas (100% recuperadas)
Se usó `dateutil.parser.parse()` en lugar de `strptime()`. **0 registros sin fecha** en el dataset final.

### 5. Summaries vacíos
121 registros (5.4%) — se conservan como string vacío.

### 6. Duplicados masivos
Se eliminaron 7,560 duplicados por `(link, title)`. La alta tasa de duplicación se debe a que cada archivo diario contenía múltiples snapshots del mismo artículo (scraping repetido). **Solo 28 links** tenían duplicados verdaderos (mismo link, diferente título/versión).

## Distribución de periódicos (dataset final)

| Periódico | Noticias |
|-----------|----------|
| AmbitoFinanciero | 466 |
| Perfil | 393 |
| lapoliticaonline | 273 |
| Pagina12 | 266 |
| diariocronica | 224 |
| ElTerritorio | 165 |
| BigBangNews | 131 |
| Clarin | 115 |
| AgenciaTélam | 67 |
| ElPaís | 51 |
| NuevoDiarioWeb | 48 |
| LaNacion | 10 |
| otros (9 periódicos) | ~13 |

## Acciones de Limpieza Realizadas (script `scripts/clean_and_extract.py`)

| # | Acción | Implementado |
|---|--------|-------------|
| 1 | Reintentar parseo con encoding fallback (utf-8 → latin-1 → cp1252) | ✓ |
| 2 | Eliminar caracteres de control del JSON raw | ✓ |
| 3 | Auto-cerrar arrays JSON truncados | ✓ |
| 4 | Normalizar `section` (strip + prefijos + mapeo explícito) | ✓ |
| 5 | Parseo tolerante de fechas con `dateutil` | ✓ |
| 6 | Limpieza de HTML en `summary` con BeautifulSoup | ✓ |
| 7 | Dedup por `(link, title)` | ✓ |
| 8 | Exportar a JSON y CSV en `dataset/processed/` | ✓ |

## Acciones Pendientes

- Recuperar archivos World (solo ~20 registros de miles) — bajo valor para el análisis comparativo
- Post-procesar encoding de acentos corruptos si se requiere precisión en búsquedas textuales