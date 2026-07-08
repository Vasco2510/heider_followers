# BD2 Lab 16 — MongoDB Distribuido vs Citus

Build-and-run lab. Most code exists as of Fase 1; notebooks and informe.md remain.

## First-read files

Before doing anything, read these (in order):
1. `outputs/sistema_trabajo.md` — full plan, phases, responsibilities, file tree
2. `outputs/informe_data.md` — dataset analysis, problems found, cleaning actions
3. `outputs/configs/guia_rapida.md` — ports, credentials, connection strings

## Agent vs Human responsibilities

| Task | Who | Why |
|------|-----|-----|
| Write docker-compose, scripts, notebooks, .md reports | **IA (DeepSeek)** | Code generation |
| Execute Docker, run scripts, capture screenshots, run notebooks, convert .md → PDF | **Human** | Requires local machine, UI, Docker |
| Dataset download | **Human** (already done) | Needs auth / browser |

## Dataset state

- Source: 24,102 JSON files in `dataset/` nested as `country/outlet/section/date.json`
- Parsed: 8,385 files → 9,781 news items (34.8% hit rate; 65% unparseable)
- Problems: encoding corruption / 106 section values to normalize to ~50 / dates in multiple formats / 409 empty summaries
- Cleaning needed before loading: re-try unparseable files with tolerant parser, normalize `section` (strip + unify), parse dates with `dateutil`, fix encoding

## Required deliverables (files to create)

| File | Where |
|------|-------|
| MongoDB docker-compose | `mongodb/docker-compose.yml` |
| MongoDB load+clean script | `mongodb/scripts/load_data.py` |
| MongoDB sharding+indexes | `mongodb/scripts/init-sharding.js` |
| MongoDB notebook | `mongodb/notebooks/mongo_analysis.ipynb` |
| Citus docker-compose | `citus/docker-compose.yml` |
| Citus init SQL | `citus/scripts/init.sql` |
| Citus load script | `citus/scripts/load_data.py` |
| Citus notebook | `citus/notebooks/citus_analysis.ipynb` |
| Final report | `outputs/informe.md` (→ human converts to PDF) |
| Screenshots | `outputs/screenshots/` + per-system folders |

## Queries (Q1–Q5)

| # | Type | MongoDB | Citus |
|---|------|---------|-------|
| Q1 | Multi-term text search | `$text` + `$meta textScore` | `to_tsvector` + `ts_rank` |
| Q2 | Exclusion search | `$text` with `-term` | `to_tsquery('!term')` |
| Q3 | Top 10 by date | `sort({published:-1}).limit(10)` | `ORDER BY published DESC LIMIT 10` |
| Q4 | Group by shard key | `$group` by `section` | `GROUP BY section` (local) |
| Q5 | Group by non-shard key | `$group` by `news_paper` | `GROUP BY news_paper` (scatter/gather) |

## Critical constraints

- **Shard key:** `section` in both systems (choose hash vs range)
- **Indexes MongoDB:** simple on `published`, hash on `news_paper`, text on `title`+`summary`
- **Indexes Citus:** GIN on `to_tsvector('spanish', title||' '||summary)`, BTree on `published`, hash on `news_paper`
- **Language:** Spanish for text search
- **Analysis:** `explain("executionStats")` (Mongo) + `EXPLAIN ANALYZE` (Citus) on every query; record times in pandas
- **Compass:** verify `sh.status()`, shard distribution, chunks
- **pgAdmin:** verify workers, distributed tables

## Evaluation (P1–P12)

Answer all 12 in order in `outputs/informe.md`. Each needs evidence (screenshots, tables, explain extracts). Full rubric in `lab_mongo.pdf`.