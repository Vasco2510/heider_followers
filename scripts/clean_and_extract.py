import os
import re
import json
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

DATASET_DIR = str(Path(__file__).resolve().parents[1] / "dataset")
OUTPUT_DIR = os.path.join(DATASET_DIR, "processed")
CATEGORIES = ["Argentina", "World"]

os.makedirs(OUTPUT_DIR, exist_ok=True)

PREFIX_REMOVER = re.compile(
    r'^(ediciones\s*-\s*|secciones\s*-\s*|titulares\s*-\s*|multimedia\s*-\s*)',
    re.IGNORECASE
)

SECTION_NORMALIZE = {
    "últimas noticias": "Últimas noticias",
    "ultimasnoticias": "Últimas noticias",
    "últimasnoticias": "Últimas noticias",
    "ultimas_noticias": "Últimas noticias",
    "último momento": "Último momento",
    "ultimomomento": "Último momento",
    "política": "Política",
    "política ": "Política",
    " política": "Política",
    "economía": "Economía",
    "economía ": "Economía",
    " economía": "Economía",
    "deportes": "Deportes",
    "deportes ": "Deportes",
    "sociedad": "Sociedad",
    "sociedad ": "Sociedad",
    "espectáculos": "Espectáculos",
    "opinión": "Opinión",
    "opinión ": "Opinión",
    "tecnología": "Tecnología",
    "elmundo": "El Mundo",
    "el mundo": "El Mundo",
    "el mundo ": "El Mundo",
    "internacional": "Internacional",
    "internaciona": "Internacional",
    "conosur": "Cono Sur",
    "el país": "El País",
    "elpaís": "El País",
    "el país ": "El País",
    "el país  ": "El País",
    "país y mundo": "País y Mundo",
    "país y mund": "País y Mundo",
    "país y mund ": "País y Mundo",
    "el país y el mundo": "El País y el Mundo",
    "el país y el mundo ": "El País y el Mundo",
    "ciencia": "Ciencia",
    "salud": "Salud",
    "negocios": "Negocios",
    "finanzas": "Finanzas",
    "lifestyle": "Lifestyle",
    "policiales": "Policiales",
    "policiales ": "Policiales",
    "policía": "Policía",
    "actualidad": "Actualidad",
    "actualidad ": "Actualidad",
    "portada": "Portada",
    "cultura": "Cultura",
    "especiales": "Especiales",
    "mund": "Mundo",
    "municipios": "Municipios",
    "nacional": "Nacional",
    "misiones": "Misiones",
    "la provincia": "La Provincia",
    "psicología": "Psicología",
    "tecnología/o":"Tecnología",
    "energía": "Energía",
}

all_recovered = []
total_files = 0
parsed_files = 0
failed_files = 0

print("Iniciando fase de recuperación agresiva de JSONs...")

for category in CATEGORIES:
    category_path = os.path.join(DATASET_DIR, category)
    if not os.path.exists(category_path):
        print(f"  [SKIP] {category_path} no existe")
        continue

    for root, dirs, files in os.walk(category_path):
        folder_section = os.path.basename(root)

        for file in files:
            if not file.endswith('.json'):
                continue

            total_files += 1
            file_path = os.path.join(root, file)

            raw_content = ""
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                        raw_content = f.read()
                    break
                except Exception:
                    continue

            if not raw_content.strip():
                failed_files += 1
                continue

            raw_content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', raw_content)

            try:
                data = json.loads(raw_content, strict=False)
                parsed_files += 1
            except json.JSONDecodeError:
                try:
                    if raw_content.strip().startswith('[') and not raw_content.strip().endswith(']'):
                        data = json.loads(raw_content.strip() + ']', strict=False)
                        parsed_files += 1
                    else:
                        raise ValueError()
                except Exception:
                    failed_files += 1
                    continue

            if isinstance(data, dict):
                items = [data]
            elif isinstance(data, list):
                items = data
            else:
                failed_files += 1
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue

                raw_section = item.get("section") or folder_section
                sec_clean = raw_section.strip().lower()
                sec_clean = PREFIX_REMOVER.sub('', sec_clean).strip()

                if sec_clean in SECTION_NORMALIZE:
                    sec_clean = SECTION_NORMALIZE[sec_clean]
                else:
                    sec_clean = sec_clean.title().strip()

                raw_summary = item.get("summary", "")
                clean_summary = ""
                if raw_summary:
                    try:
                        clean_summary = BeautifulSoup(raw_summary, "html.parser").get_text()
                    except Exception:
                        clean_summary = str(raw_summary)

                raw_date = item.get("published", "")
                iso_date = None
                if raw_date:
                    try:
                        parsed_date = date_parser.parse(str(raw_date))
                        iso_date = parsed_date.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        iso_date = None

                doc = {
                    "news_paper": (item.get("news_paper") or "").strip(),
                    "section": sec_clean,
                    "title": str(item.get("title", "")).strip(),
                    "summary": clean_summary.strip(),
                    "published": iso_date,
                    "link": (item.get("link") or "").strip(),
                    "tags": str(item.get("tags", "")).strip(),
                    "credit": str(item.get("credit", "")).strip(),
                }
                all_recovered.append(doc)

df = pd.DataFrame(all_recovered)
before = len(df)
df.drop_duplicates(subset=["link", "title"], keep="first", inplace=True)
dupes = before - len(df)

output_file = os.path.join(OUTPUT_DIR, "milei_news_clean.json")
df.to_json(output_file, orient="records", force_ascii=False, indent=2)

csv_file = os.path.join(OUTPUT_DIR, "milei_news_clean.csv")
df.to_csv(csv_file, index=False, encoding="utf-8")

print(f"\nTotal archivos JSON evaluados:  {total_files}")
print(f"Archivos procesados con exito:  {parsed_files} ({parsed_files/total_files*100:.1f}%)")
print(f"Archivos descartados/corruptos: {failed_files} ({failed_files/total_files*100:.1f}%)")
print(f"Registros recuperados:         {before}")
print(f"Duplicados eliminados:         {dupes}")
print(f"Registros unicos finales:       {len(df)}")
print(f"\nSecciones unicas finales:       {df['section'].nunique()}")
print(f"Noticias sin fecha:            {df['published'].isna().sum()}")
print(f"Noticias sin summary:          {(df['summary'] == '').sum()}")

if df['news_paper'].nunique() > 0:
    print(f"\nPeriodicos:                    {df['news_paper'].nunique()}")
    print(df['news_paper'].value_counts().to_string())

print(f"\nArchivos generados:")
print(f"  JSON: {output_file}")
print(f"  CSV:  {csv_file}")