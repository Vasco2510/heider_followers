sh.addShard("shard1rs/shard1:27018");
sh.addShard("shard2rs/shard2:27020");

db = db.getSiblingDB("news_analysis");

sh.enableSharding("news_analysis");

db.createCollection("milei_news");

sh.shardCollection("news_analysis.milei_news", { section: "hashed" });

db.milei_news.createIndex({ published: 1 });
db.milei_news.createIndex({ news_paper: "hashed" });
db.milei_news.createIndex(
  { title: "text", summary: "text" },
  { default_language: "spanish" }
);

print("=== Sharding status ===");
sh.status();

print("\n=== Indexes ===");
db.milei_news.getIndexes().forEach(printjson);