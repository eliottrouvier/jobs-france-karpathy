"""
build_site_data.py - Assemblage du fichier site/data.json
---------------------------------------------------------
Fusionne les métriques des métiers (occupations.json) avec les scores
d'exposition à l'IA (scores.json) pour alimenter la visualisation treemap interactive.
"""

import os
import json


def main():
    print("=== Étape 4 : Compilation des données pour le site web ===")

    if not os.path.exists("occupations.json") or not os.path.exists("scores.json"):
        print("Erreur : Fichiers sources introuvables. Exécutez process.py puis score.py.")
        return

    with open("occupations.json", "r", encoding="utf-8") as f:
        occupations = json.load(f)

    with open("scores.json", "r", encoding="utf-8") as f:
        scores_list = json.load(f)

    scores_map = {s["slug"]: s for s in scores_list}

    site_data = []
    for occ in occupations:
        slug = occ["slug"]
        score_info = scores_map.get(slug, {})

        site_data.append({
            "title": occ["title"],
            "slug": slug,
            "rome_code": occ.get("rome_code", ""),
            "category": occ["category"],
            "category_name": occ.get("category_name", ""),
            "pay": occ["pay"],
            "jobs": occ["jobs"],
            "outlook": occ["outlook"],
            "outlook_desc": occ["outlook_desc"],
            "education": occ["education"],
            "exposure": score_info.get("exposure", 5),
            "exposure_rationale": score_info.get("rationale", ""),
            "url": occ.get("url", ""),
        })

    os.makedirs("site", exist_ok=True)
    site_json_path = os.path.join("site", "data.json")
    with open(site_json_path, "w", encoding="utf-8") as f:
        json.dump(site_data, f, ensure_ascii=False, indent=2)

    total_jobs = sum(d["jobs"] for d in site_data)
    avg_score = sum(d["exposure"] * d["jobs"] for d in site_data) / max(1, total_jobs)
    high_exp_jobs = sum(d["jobs"] for d in site_data if d["exposure"] >= 7)
    high_exp_wages = sum(d["jobs"] * d["pay"] for d in site_data if d["exposure"] >= 7)

    print(f"✓ `site/data.json` généré avec succès ({len(site_data)} métiers).")
    print(f"  • Total emplois représentés : {total_jobs:,} actifs".replace(",", " "))
    print(f"  • Exposition moyenne pondérée : {avg_score:.2f} / 10")
    print(f"  • Emplois fortement exposés (score ≥ 7) : {high_exp_jobs:,} ({high_exp_jobs/total_jobs*100:.1f}%)".replace(",", " "))
    print(f"  • Masse salariale exposée (≥ 7) : {high_exp_wages / 1e9:.1f} Milliards d'€ / an")


if __name__ == "__main__":
    main()
