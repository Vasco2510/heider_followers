import os
import json
import sys
import time
from pymongo import MongoClient, InsertOne

DATA_FILE = r"Z:\26-1\BD2\lab16\dataset\processed\milei_news_clean.json"
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "news_analysis"
COLLECTION_NAME = "milei_news"
BATCH_SIZE = 500

print("Conectando a MongoDB via mongos...")
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=30000)
client.admin.command('ping')
print("Conexion exitosa.\n")

db = client[DB_NAME]
collection = db[COLLECTION_NAME]

print(f"Cargando datos desde: {DATA_FILE}")
with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Registros a insertar: {len(data)}")

# Convertir published string -> date object
from datetime import datetime
for doc in data:
    if doc.get("published"):
        try:
            doc["published"] = datetime.strptime(doc["published"], "%Y-%m-%d %H:%M:%S")
        except:
            doc["published"] = None

# Bulk insert en batches
total = len(data)
inserted = 0
errors = 0
start = time.time()

for i in range(0, total, BATCH_SIZE):
    batch = data[i : i + BATCH_SIZE]
    try:
        collection.insert_many(batch, ordered=False)
        inserted += len(batch)
    except Exception as e:
        errors += 1
    pct = (i + len(batch)) / total * 100
    print(f"  Progreso: {i + len(batch)}/{total} ({pct:.0f}%)", end="\r")

elapsed = time.time() - start
print(f"\n\nInsercion completada en {elapsed:.2f}s")
print(f"Insertados: {inserted} | Errores de batch: {errors}")

# Stats
print(f"\n=== Coleccion stats ===")
print(f"Documentos totales: {collection.count_documents({})}")
print(f"Secciones unicas: {len(collection.distinct('section'))}")
print(f"Periodicos unicos: {len(collection.distinct('news_paper'))}")

client.close()
print("\nListo.")