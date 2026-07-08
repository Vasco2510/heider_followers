-- Habilitar extensión Citus
CREATE EXTENSION IF NOT EXISTS citus;

-- Verificar workers activos (se añaden manualmente tras docker-compose up)
SELECT master_add_node('worker1', 5432);
SELECT master_add_node('worker2', 5432);

-- Crear tabla
CREATE TABLE IF NOT EXISTS milei_news (
    id SERIAL PRIMARY KEY,
    news_paper TEXT,
    section TEXT,
    title TEXT,
    summary TEXT,
    published TIMESTAMP,
    link TEXT,
    tags TEXT,
    credit TEXT
);

-- Convertir en tabla distribuida por section (hash)
SELECT create_distributed_table('milei_news', 'section');

-- Índices
CREATE INDEX idx_milei_news_published ON milei_news (published);
CREATE INDEX idx_milei_news_newspaper ON milei_news USING hash (news_paper);
CREATE INDEX idx_milei_news_text ON milei_news USING GIN (
    to_tsvector('spanish', coalesce(title, '') || ' ' || coalesce(summary, ''))
);

-- Verificar distribución
SELECT * FROM master_get_active_worker_nodes();
SELECT shardid, shardstate, nodename, nodeport FROM citus_shards WHERE table_name::text = 'milei_news';