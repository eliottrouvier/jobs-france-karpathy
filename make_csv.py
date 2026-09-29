"""
make_csv.py - Génération et exportation du tableau de synthèse occupations.csv
-----------------------------------------------------------------------------
Exporte l'ensemble des 1 124 métiers français sous forme tabulaire CSV
avec identifiants ROME, salaires, effectifs, perspectives et diplômes.
"""

import csv
import json
import os

OCCUPATIONS_JSON = "occupations.json"
OCCUPATIONS_CSV = "occupations.csv"


def main():
    if not os.path.exists(OCCUPATIONS_JSON):
        print(f"Erreur : {OCCUPATIONS_JSON} introuvable. Exécutez process.py d'abord.")
        return

    with open(OCCUPATIONS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(OCCUPATIONS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "title", "slug", "rome_code", "category", "category_name",
            "median_pay_annual", "num_jobs", "outlook_pct", "outlook_desc",
            "entry_education", "url"
        ])
        for it in data:
            writer.writerow([
                it["title"],
                it["slug"],
                it.get("rome_code", ""),
                it["category"],
                it.get("category_name", ""),
                it["pay"],
                it["jobs"],
                it["outlook"],
                it["outlook_desc"],
                it["education"],
                it["url"]
            ])

    print(f"✓ {OCCUPATIONS_CSV} généré avec succès ({len(data)} métiers).")


if __name__ == "__main__":
    main()
