import json
import time
import psycopg2
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "dataset" / "processed" / "milei_news_clean.json"
DB_CONFIG = {
    "host": "localhost",
    "port": 5435,  # el 5432 del host lo ocupa un PostgreSQL 17 local
    "dbname": "news_analysis_pg",
    "user": "postgres",
    "password": "postgres",
}
BATCH_SIZE = 500

print("Conectando a Citus coordinator...")
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()
print("Conexion exitosa.\n")

if not DATA_FILE.exists():
    raise SystemExit(
        f"No existe {DATA_FILE}.\n"
        "Coloca el dataset en dataset/ y ejecuta primero: python scripts/clean_and_extract.py"
    )

print(f"Cargando datos desde: {DATA_FILE}")
with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Registros a insertar: {len(data)}")

# Truncate table for clean load
cursor.execute("TRUNCATE TABLE milei_news;")
conn.commit()

total = len(data)
inserted = 0
start = time.time()

for i in range(0, total, BATCH_SIZE):
    batch = data[i : i + BATCH_SIZE]
    values = []
    for doc in batch:
        published = doc.get("published")
        if published:
            try:
                published = datetime.strptime(published, "%Y-%m-%d %H:%M:%S")
            except:
                published = None
        values.append((
            doc.get("news_paper", ""),
            doc.get("section", ""),
            doc.get("title", ""),
            doc.get("summary", ""),
            published,
            doc.get("link", ""),
            doc.get("tags", ""),
            doc.get("credit", ""),
        ))

    args = ",".join(cursor.mogrify(
        "(%s,%s,%s,%s,%s,%s,%s,%s)", v
    ).decode() for v in values)

    cursor.execute(
        "INSERT INTO milei_news (news_paper, section, title, summary, published, link, tags, credit) VALUES " + args
    )
    conn.commit()
    inserted += len(batch)
    pct = (i + len(batch)) / total * 100
    print(f"  Progreso: {i + len(batch)}/{total} ({pct:.0f}%)", end="\r")

elapsed = time.time() - start
print(f"\n\nInsercion completada en {elapsed:.2f}s")
print(f"Insertados: {inserted}")

# Stats
cursor.execute("SELECT COUNT(*) FROM milei_news")
total_rows = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(DISTINCT section) FROM milei_news")
sections = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(DISTINCT news_paper) FROM milei_news")
papers = cursor.fetchone()[0]

print(f"\n=== Tabla stats ===")
print(f"Filas totales: {total_rows}")
print(f"Secciones unicas: {sections}")
print(f"Periodicos unicos: {papers}")

cursor.close()
conn.close()
print("\nListo.")