db = db.getSiblingDB("news_analysis");

// Habilitar sharding en la base de datos
sh.enableSharding("news_analysis");

// Crear colección
db.createCollection("milei_news");

// Shard key: section (hash por cardinalidad moderada ~70 valores)
sh.shardCollection("news_analysis.milei_news", { section: "hashed" });

// Índices
db.milei_news.createIndex({ published: 1 });
db.milei_news.createIndex({ news_paper: "hashed" });
db.milei_news.createIndex(
  { title: "text", summary: "text" },
  { default_language: "spanish" }
);

print("=== Sharding status ===");
sh.status();

print("=== Indexes ===");
db.milei_news.getIndexes().forEach(printjson);