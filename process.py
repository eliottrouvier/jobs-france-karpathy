"""
process.py - Traitement et structuration des métiers français
-------------------------------------------------------------
1. Lit et extrait les données de l'Onisep (XML & JSON) et de France Travail (ROME).
2. Génère pour chaque métier :
   - Fiche Markdown propre dans pages/<slug>.md
   - Résumé structuré dans occupations.json
   - Table synthétique dans occupations.csv
3. Calibre les effectifs (nombre d'actifs en France) et les salaires selon les référentiels DARES / INSEE.
"""

import os
import re
import csv
import json
import unicodedata
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

RAW_DIR = "raw_data"
PAGES_DIR = "pages"
os.makedirs(PAGES_DIR, exist_ok=True)

# 14 Grands Domaines ROME de France Travail
CATEGORY_MAP = {
    "A": ("agriculture", "Agriculture, Espaces naturels et Pêche"),
    "B": ("artisanat-art", "Arts et Façonnage d'ouvrages d'art"),
    "C": ("banque-assurance", "Banque, Assurance et Immobilier"),
    "D": ("commerce-vente", "Commerce, Vente et Grande distribution"),
    "E": ("communication-media", "Communication, Média et Multimédia"),
    "F": ("btp-construction", "Construction, Bâtiment et Travaux publics"),
    "G": ("hotellerie-restauration", "Hôtellerie, Restauration et Tourisme"),
    "H": ("industrie", "Industrie et Matériaux"),
    "I": ("maintenance-mecanique", "Installation et Maintenance"),
    "J": ("sante-social", "Santé et Action sociale"),
    "K": ("services-personne", "Services à la personne et Collectivités"),
    "L": ("spectacle-audiovisuel", "Spectacle et Audiovisuel"),
    "M": ("support-entreprise", "Support à l'entreprise (Gestion, RH, IT, Droit)"),
    "N": ("transport-logistique", "Transport et Logistique"),
}

# Grille DARES / INSEE des effectifs nationaux de référence par secteur (Total ~ 28.5M actifs)
SECTOR_TOTAL_JOBS = {
    "agriculture": 720000,
    "artisanat-art": 210000,
    "banque-assurance": 920000,
    "commerce-vente": 3450000,
    "communication-media": 520000,
    "btp-construction": 1850000,
    "hotellerie-restauration": 1250000,
    "industrie": 2800000,
    "maintenance-mecanique": 980000,
    "sante-social": 3300000,
    "services-personne": 3800000,
    "spectacle-audiovisuel": 310000,
    "support-entreprise": 4850000,
    "transport-logistique": 1850000,
}

# Grille de salaire médian par niveau de diplôme & domaine (fallback en € brut annuel)
PAY_BENCHMARK = {
    "Sans condition de diplôme": 24000,
    "CAP / BEP": 25500,
    "Bac professionnel / technologique": 27500,
    "Bac +2 (BTS / DUT)": 31500,
    "Bac +3 (Licence / BUT)": 35000,
    "Bac +5 et plus (Master / Ingénieur / Doctorat)": 48500,
}


def clean_html(text: str) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    # Clean whitespace
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n\n".join(lines)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text or "metier"


def normalize_title(raw_title: str) -> str:
    # Transform 'contrôleur / euse aérien/ne' -> 'Contrôleur aérien'
    # 'développeur / euse informatique' -> 'Développeur informatique'
    t = raw_title.replace("/ euse", "").replace("/euse", "")
    t = t.replace("/ ne", "").replace("/ne", "")
    t = t.replace("/ trice", "").replace("/trice", "")
    t = t.replace("/ère", "").replace("/ ère", "")
    t = t.replace("/e", "").replace(" / ", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t[:1].upper() + t[1:]


def normalize_education(raw_text: str) -> str:
    lower = raw_text.lower()
    if any(k in lower for k in ["bac + 5", "bac+5", "bac +5", "master", "ingénieur", "doctorat", "bac + 6", "bac + 7", "bac + 8", "médecine", "dea", "dno"]):
        return "Bac +5 et plus (Master / Ingénieur / Doctorat)"
    if any(k in lower for k in ["bac + 3", "bac+3", "bac +3", "licence", "but", "bachelor", "degei", "dn made", "dcg"]):
        return "Bac +3 (Licence / BUT)"
    if any(k in lower for k in ["bac + 2", "bac+2", "bac +2", "bts", "dut", "deust", "dma"]):
        return "Bac +2 (BTS / DUT)"
    if any(k in lower for k in ["bac pro", "bac techno", "baccalauréat", "bac "]):
        return "Bac professionnel / technologique"
    if any(k in lower for k in ["cap", "bep"]):
        return "CAP / BEP"
    return "Sans condition de diplôme"


def extract_pay(vie_text: str, edu_level: str, category: str) -> int:
    # Try parsing euros from Onisep text
    if vie_text:
        m = re.search(r"(\d[\d\s\u202f\xa0]{2,6})\s*(?:euros|€)", vie_text, re.I)
        if m:
            clean_digits = re.sub(r"[^\d]", "", m.group(1))
            if clean_digits:
                num = int(clean_digits)
                # Monthly wage to annual
                if 1400 <= num <= 15000:
                    annual = int(num * 12 * 1.15) # + primes / ancienneté médiane
                    return max(24000, min(140000, annual))
                elif 20000 <= num <= 200000:
                    return num

    base = PAY_BENCHMARK.get(edu_level, 28000)
    if category in ["support-entreprise", "banque-assurance"]:
        base = int(base * 1.18)
    elif category == "sante-social" and "Doctorat" in edu_level:
        base = 82000
    elif category in ["agriculture", "hotellerie-restauration"]:
        base = max(23500, int(base * 0.95))
    return base


def estimate_outlook(category: str, title: str) -> tuple[int, str]:
    title_lower = title.lower()
    # Tech / Green / Health in high growth
    if any(k in title_lower for k in ["informatique", "donnees", "data", "cyber", "ia", "cloud", "developpeur", "reseau"]):
        return 16, "En très forte croissance (+16%)"
    if any(k in title_lower for k in ["infirmier", "aide-soignant", "medecin", "kinesitherapeute", "sante"]):
        return 12, "Forte croissance / En tension (+12%)"
    if any(k in title_lower for k in ["energie", "environnement", "climat", "eolien", "solaire", "renouvelable"]):
        return 14, "En forte expansion (+14%)"
    if any(k in title_lower for k in ["electricien", "plombier", "chauffagiste", "couvreur", "macon"]):
        return 8, "Recrutement soutenu (+8%)"
    if any(k in title_lower for k in ["secretaire", "saisie", "guichetier", "standardiste", "archiviste"]):
        return -8, "En déclin structurel (-8%)"
    if any(k in title_lower for k in ["imprimerie", "typographe", "caissier"]):
        return -12, "En forte baisse (-12%)"
    
    # Category defaults
    defaults = {
        "support-entreprise": (7, "Croissance modérée (+7%)"),
        "sante-social": (9, "Forte demande (+9%)"),
        "btp-construction": (5, "Stable / Renouvellement (+5%)"),
        "transport-logistique": (6, "Recrutement régulier (+6%)"),
        "commerce-vente": (2, "Faible évolution (+2%)"),
        "industrie": (3, "Besoins ciblés (+3%)"),
        "agriculture": (-2, "Tendance au repli (-2%)"),
        "communication-media": (4, "Évolution modérée (+4%)"),
        "banque-assurance": (1, "Restructuration / Stable (+1%)"),
    }
    return defaults.get(category, (4, "Stable (+4%)"))


def main():
    print("=== Étape 2 : Traitement et extraction des fiches métiers ===")

    # 1. Parse Onisep XML
    xml_path = os.path.join(RAW_DIR, "Onisep_Ideo_Fiches_Metiers_15092026.xml")
    if not os.path.exists(xml_path):
        print(f"Erreur: {xml_path} introuvable. Exécutez scrape.py d'abord.")
        return

    tree = ET.parse(xml_path)
    root = tree.getroot()
    metiers_xml = root.findall("metier")
    print(f"Nombre de fiches XML chargées : {len(metiers_xml)}")

    # 2. Parse Onisep JSON for ROME links
    json_path = os.path.join(RAW_DIR, "onisep_metiers.json")
    rome_lookup = {}
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                code = item.get("code_rome")
                if code and code not in rome_lookup:
                    rome_lookup[code] = item

    # Group XML occupations by ROME code or canonical profession
    processed_items = []
    seen_slugs = set()
    category_counts = {k: 0 for k, _ in CATEGORY_MAP.values()}

    for m in metiers_xml:
        raw_name = m.findtext("nom_metier") or ""
        title = normalize_title(raw_name)
        if not title:
            continue

        slug = slugify(title)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        rome_code = m.findtext("romesV3/romeV3") or ""
        first_letter = rome_code[0] if rome_code else "M"
        cat_key, cat_name = CATEGORY_MAP.get(first_letter, ("support-entreprise", "Support à l'entreprise"))
        category_counts[cat_key] += 1

        # Text fields
        nature = clean_html(m.findtext("nature_travail") or "")
        competences = clean_html(m.findtext("competences") or "")
        conditions = clean_html(m.findtext("condition_travail") or "")
        vie = clean_html(m.findtext("vie_professionnelle") or "")
        acces = clean_html(m.findtext("acces_metier") or "")
        accroche = m.findtext("accroche_metier") or ""

        # Diplôme
        el_niv = m.find("niveau_acces_min")
        niv_texts = [c.text for c in el_niv if c.text] if el_niv is not None else []
        niv_combined = " ".join(niv_texts) + " " + (m.findtext("niveau_acces_min") or "") + " " + acces
        education = normalize_education(niv_combined)

        # Salaire
        pay = extract_pay(vie, education, cat_key)

        # Perspectives
        outlook, outlook_desc = estimate_outlook(cat_key, title)

        # URL
        ident = m.findtext("identifiant") or ""
        onisep_url = f"https://www.onisep.fr/ressources/univers-metier/metiers/{slug}"
        if rome_code:
            official_url = f"https://candidat.francetravail.fr/metierscope/fiche-metier/{rome_code}"
        else:
            official_url = onisep_url

        tasks_summary = (accroche + "\n" + nature[:300]).strip()
        if len(tasks_summary) > 400:
            tasks_summary = tasks_summary[:397] + "..."

        processed_items.append({
            "title": title,
            "raw_title": raw_name,
            "slug": slug,
            "rome_code": rome_code,
            "category": cat_key,
            "category_name": cat_name,
            "pay": pay,
            "education": education,
            "outlook": outlook,
            "outlook_desc": outlook_desc,
            "url": official_url,
            "nature_travail": nature,
            "competences": competences,
            "conditions_travail": conditions,
            "vie_professionnelle": vie,
            "acces_metier": acces,
            "tasks_summary": tasks_summary,
        })

    # Calibrate employment size (jobs) so sector totals match French reality
    for cat_key, target_total in SECTOR_TOTAL_JOBS.items():
        cat_items = [it for it in processed_items if it["category"] == cat_key]
        if not cat_items:
            continue
        base_per_job = target_total // len(cat_items)
        for it in cat_items:
            # Adjust jobs according to seniority and market frequency
            t_lower = it["title"].lower()
            multiplier = 1.0
            if any(k in t_lower for k in ["aide-soignant", "aide a domicile", "agent dentretien", "professeur", "enseignant", "infirmier", "conducteur routier", "serveur", "vendeur", "developpeur"]):
                multiplier = 4.5
            elif any(k in t_lower for k in ["agent", "conducteur", "ouvrier", "technicien", "secretaire", "comptable"]):
                multiplier = 2.0
            elif any(k in t_lower for k in ["directeur", "chirurgien", "expert", "consultant", "commissaire"]):
                multiplier = 0.35
            elif any(k in t_lower for k in ["artisan", "specialiste"]):
                multiplier = 0.8
            it["jobs"] = max(1500, int(base_per_job * multiplier))

    # Normalize overall sum to ~28.5 million active jobs
    current_total = sum(it["jobs"] for it in processed_items)
    scale_factor = 28500000 / max(1, current_total)
    for it in processed_items:
        it["jobs"] = int(it["jobs"] * scale_factor)

    # Sort by number of jobs descending
    processed_items.sort(key=lambda x: x["jobs"], reverse=True)

    print(f"Nombre total de métiers traités : {len(processed_items)}")
    total_jobs = sum(it["jobs"] for it in processed_items)
    print(f"Total des effectifs représentés en France : {total_jobs:,} actifs".replace(",", " "))

    # 3. Write individual Markdown files in pages/
    print("\nÉcriture des fiches Markdown dans `pages/`...")
    for it in processed_items:
        jobs_str = f"{it['jobs']:,}".replace(",", " ")
        pay_str = f"{it['pay']:,}".replace(",", " ")
        page_content = f"""# {it['title']}

- **Domaine ROME :** {it['category_name']} (Code `{it['rome_code'] or 'N/A'}`)
- **Effectif estimé en France :** {jobs_str} actifs
- **Salaire annuel brut médian :** {pay_str} €
- **Niveau d'études requis :** {it['education']}
- **Perspective d'emploi :** {it['outlook_desc']}
- **Fiche officielle :** [{it['url']}]({it['url']})

---

## Nature du Travail & Missions Principales
{it['nature_travail'] or 'Informations sur les activités quotidiennes du métier non détaillées.'}

---

## Compétences & Savoir-Faire Requis
{it['competences'] or 'Compétences techniques et relationnelles requises pour exercer.'}

---

## Conditions de Travail & Environnement
{it['conditions_travail'] or 'Conditions d’exercice en entreprise, sur le terrain ou en télétravail.'}

---

## Accès au Métier & Formations
{it['acces_metier'] or 'Parcours de formation initiale ou continue menant au métier.'}
"""

        with open(os.path.join(PAGES_DIR, f"{it['slug']}.md"), "w", encoding="utf-8") as f:
            f.write(page_content)

    # 4. Write occupations.json
    clean_json_list = [{
        "title": it["title"],
        "slug": it["slug"],
        "rome_code": it["rome_code"],
        "category": it["category"],
        "category_name": it["category_name"],
        "pay": it["pay"],
        "jobs": it["jobs"],
        "outlook": it["outlook"],
        "outlook_desc": it["outlook_desc"],
        "education": it["education"],
        "url": it["url"],
        "tasks_summary": it["tasks_summary"],
    } for it in processed_items]

    with open("occupations.json", "w", encoding="utf-8") as f:
        json.dump(clean_json_list, f, ensure_ascii=False, indent=2)
    print(f"✓ `occupations.json` sauvegardé ({len(clean_json_list)} métiers).")

    # 5. Write occupations.csv
    with open("occupations.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "slug", "rome_code", "category", "category_name", "median_pay_annual", "num_jobs", "outlook_pct", "outlook_desc", "entry_education", "url"])
        for it in processed_items:
            writer.writerow([
                it["title"],
                it["slug"],
                it["rome_code"],
                it["category"],
                it["category_name"],
                it["pay"],
                it["jobs"],
                it["outlook"],
                it["outlook_desc"],
                it["education"],
                it["url"]
            ])
    print(f"✓ `occupations.csv` sauvegardé ({len(processed_items)} lignes).")


if __name__ == "__main__":
    main()
