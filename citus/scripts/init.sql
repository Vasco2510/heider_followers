-- BD2 Lab — Parte II: Citus en PostgreSQL
-- Ejecutar en el coordinator DESPUÉS de que los 3 contenedores estén healthy:
--   docker exec citus-coordinator psql -U postgres -d news_analysis_pg -f /scripts/init.sql
-- (o usar citus/scripts/setup_cluster.ps1 que hace todo el flujo)

-- 1. Habilitar extensión Citus (la imagen citusdata/citus ya la crea, esto es idempotente)
CREATE EXTENSION IF NOT EXISTS citus;

-- 2. Registrar los 2 workers (idempotente: citus_add_node ignora nodos ya registrados en Citus 11+)
SELECT citus_add_node('worker1', 5432);
SELECT citus_add_node('worker2', 5432);

-- 3. Esquema relacional de la tabla milei_news
--    NOTA: en Citus toda PK/constraint UNIQUE debe incluir la columna de distribución,
--    por eso la PK es compuesta (id, section).
DROP TABLE IF EXISTS milei_news;
CREATE TABLE milei_news (
    id BIGSERIAL,
    news_paper TEXT,
    section TEXT NOT NULL,
    title TEXT,
    summary TEXT,
    published TIMESTAMP,
    link TEXT,
    tags TEXT,
    credit TEXT,
    PRIMARY KEY (id, section)
);

-- 4. Distribuir la tabla por section con estrategia HASH.
--    Justificación (P7): section tiene ~70 valores con distribución muy sesgada;
--    hash reparte los valores entre shards sin necesidad de definir rangos manuales.
SELECT create_distributed_table('milei_news', 'section');

-- 5. Índices requeridos por el enunciado
-- Índice GIN para búsqueda textual en español sobre title + summary
CREATE INDEX IF NOT EXISTS idx_milei_news_text ON milei_news USING GIN (
    to_tsvector('spanish', coalesce(title, '') || ' ' || coalesce(summary, ''))
);
-- Índice B+Tree sobre published
CREATE INDEX IF NOT EXISTS idx_milei_news_published ON milei_news (published);
-- Índice Hash sobre news_paper
CREATE INDEX IF NOT EXISTS idx_milei_news_newspaper ON milei_news USING hash (news_paper);

-- 6. Verificación (evidencia para P6/P7)
SELECT * FROM citus_get_active_worker_nodes();
SELECT nodename, count(*) AS shards
FROM citus_shards
WHERE table_name::text = 'milei_news'
GROUP BY nodename;
