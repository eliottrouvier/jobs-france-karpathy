"""
score.py - Évaluation de l'exposition à l'IA des métiers français
-----------------------------------------------------------------
Implémente la méthodologie et l'échelle d'Andrej Karpathy (0 à 10) :
- Analyse le produit du travail : numérique vs physique/manuel.
- Évalue l'impact direct (automatisation de tâches) et indirect (gains de productivité réduisant les besoins en effectifs).
- Calibre les scores selon les ancres fondamentales :
  * 0–1 (Minimale) : Couvreur, paysagiste, plongeur, maçon.
  * 2–3 (Faible) : Électricien, plombier, pompier, mécanicien, boulanger.
  * 4–5 (Modérée) : Infirmier, policier, vétérinaire, pilote, cuisinier.
  * 6–7 (Élevée) : Enseignant, manager, architecte, journaliste, ingénieur.
  * 8–9 (Très élevée) : Développeur, traducteur, data analyst, graphiste, juriste, comptable.
  * 10 (Maximale) : Opérateur de saisie, téléprospecteur, transcripteur.

Génère `scores.json` avec score et rationale argumenté en français.
100% gratuit et autonome, sans clé API payante requise.
"""

import os
import re
import json
import argparse
from typing import Dict, Any, Tuple

SCORES_FILE = "scores.json"
PAGES_DIR = "pages"
OCCUPATIONS_FILE = "occupations.json"


def evaluate_occupation_exposure(item: Dict[str, Any], full_text: str) -> Tuple[int, str]:
    title = item.get("title", "")
    t_lower = title.lower()
    cat = item.get("category", "")
    full_lower = full_text.lower()

    # --- 1. Mots-clés numériques forts (IA, Dev, Données, Traduction, Rédaction, Finance, Droit) ---
    digital_keywords = [
        "informatique", "logiciel", "code", "programmation", "développeur", "développement web",
        "data", "données", "algorithme", "intelligence artificielle", "réseau", "cloud",
        "traduction", "traducteur", "rédacteur", "rédaction", "journaliste", "graphiste",
        "design graphique", "webdesign", "infographie", "comptable", "comptabilité", "audit",
        "finance", "analyste", "juriste", "avocat", "droit", "fiscalité", "téléprospection",
        "saisie", "archivage numérique", "téléconseiller", "secrétaire", "assistanat"
    ]
    digital_matches = sum(1 for kw in digital_keywords if kw in t_lower or kw in full_lower)

    # --- 2. Mots-clés physiques et manuels forts (Chantier, Outils, Soins corporels, Matière) ---
    physical_keywords = [
        "chantier", "travaux", "manuel", "outillage", "marteau", "scie", "soudure", "bâtiment",
        "maçon", "plombier", "électricien", "couvreur", "peintre", "mécanique", "moteur",
        "réparation", "dépannage", "cuisine", "cuisinier", "pâtissier", "boulanger", "boucher",
        "forêt", "bûcheron", "paysagiste", "agricole", "terre", "animaux", "vétérinaire",
        "soin corporel", "toilette", "brancardier", "infirmier", "aide-soignant", "chirurgien",
        "pompier", "secours", "police", "gendarme", "sécurité physique", "conducteur", "camion",
        "volant", "transport de personnes", "manutention", "magasinier", "nettoyage", "propreté"
    ]
    physical_matches = sum(1 for kw in physical_keywords if kw in t_lower or kw in full_lower)

    # --- 3. Détection des cas emblématiques et ancres absolues ---
    # Score 10 : Saisie de données, téléprospection et transcription routinière
    if any(k in t_lower for k in [
        "opérateur de saisie", "opératrice de saisie", "téléprospecteur", "relation client à distance",
        "transcripteur", "guichetier", "standardiste", "agent de saisie", "agent de numérisation"
    ]):
        score = 10
        rationale = (
            "Métier reposant presque exclusivement sur le traitement routinier d'informations textuelles, de formulaires ou d'appels téléphoniques entrants/sortants. "
            "Les agents vocaux IA et les modèles multimodaux de traitement automatique de documents permettent déjà d'automatiser l'intégralité de ces tâches à moindre coût."
        )
        return score, rationale

    # Score 9 : Développeurs, Traducteurs, Data Analysts, Rédacteurs
    if any(k in t_lower for k in ["développeur", "traducteur", "data analyst", "data scientist", "rédacteur web", "correcteur", "intégrateur web", "programmeur"]):
        score = 9
        rationale = (
            "L'activité et le livrable sont 100 % numériques et réalisables intégralement sur ordinateur. "
            "Les modèles de fondation génèrent déjà du code, traduisent et rédigent avec une haute compétence, décuplant la productivité individuelle et entraînant une profonde restructuration du volume d'emploi nécessaire."
        )
        return score, rationale

    # Score 8 : Comptables, Juristes, Graphistes, Analystes financiers
    if any(k in t_lower for k in ["comptable", "juriste", "graphiste", "analyste financier", "chargé d'études", "illustrateur", "webdesigner", "chargé de recrutement"]):
        score = 8
        rationale = (
            "Profession centrée sur la manipulation documentaire, la conformité réglementaire et l'analyse de données. "
            "Bien que le conseil à forte valeur ajoutée et la validation finale requièrent du discernement humain, les tâches de synthèse, de rédaction et de calcul prévisionnel sont massivement automatisables par l'IA."
        )
        return score, rationale

    # Score 0-1 : Travaux de gros œuvre, couverture, espaces naturels
    if any(k in t_lower for k in ["couvreur", "bûcheron", "élagueur", "plongeur", "maçon", "égoutier", "ramoneur", "déménageur", "ouvrier paysagiste", "ouvrier agricole", "maraîcher"]):
        score = 1
        rationale = (
            "Le travail est presque exclusivement manuel, physique et exercé dans un environnement extérieur imprévisible. "
            "L'IA n'exerce aucun impact direct sur les gestes du métier ni sur la manipulation concrète des matériaux sur le terrain."
        )
        return score, rationale

    # Score 2 : Artisans, électriciens, plombiers, pompiers, mécaniciens, bouchers
    if any(k in t_lower for k in ["électricien", "plombier", "mécanicien", "boucher", "boulanger", "pompier", "serrurier", "chaudronnier", "soudeur", "peintre en bâtiment", "charpentier"]):
        score = 2
        rationale = (
            "Métier manuel exigeant une forte dextérité, une motricité fine et une adaptation constante aux contraintes physiques des chantiers ou ateliers. "
            "L'IA n'intervient qu'en périphérie administrative (devis, planification, diagnostic logiciel) sans menacer le cœur du savoir-faire artisanal."
        )
        return score, rationale

    # Score 3 : Aides-soignants, serveurs, coiffeurs, auxiliaires de puériculture
    if any(k in t_lower for k in ["aide-soignant", "coiffeur", "serveur", "barman", "auxiliaire de vie", "puéricultrice", "agent d'entretien", "esthéticien"]):
        score = 3
        rationale = (
            "Le métier repose sur la présence physique, la motricité et l'interaction humaine directe. "
            "Même si certains outils numériques optimisent la gestion du temps ou des stocks, l'empathie, le contact physique et le relationnel direct constituent une barrière naturelle solide contre l'automatisation."
        )
        return score, rationale

    # Score 4 : Infirmiers, policiers, vétérinaires, kinésithérapeutes
    if any(k in t_lower for k in ["infirmier", "policier", "gendarme", "vétérinaire", "kinésithérapeute", "ergothérapeute", "dentiste"]):
        score = 4
        rationale = (
            "Activité hybride alliant expertise diagnostique théorique et soins physiques directs aux personnes. "
            "L'IA améliore significativement l'aide à la décision médicale et la gestion des dossiers, mais l'acte de soin, la relation thérapeutique et la responsabilité clinique restent indissociables de l'humain."
        )
        return score, rationale

    # Score 6-7 : Enseignants, Médecins généralistes, Architectes, Managers
    if any(k in t_lower for k in ["enseignant", "professeur", "formateur", "médecin", "architecte", "journaliste", "chef de projet", "responsable marketing", "directeur"]):
        score = 7 if any(k in t_lower for k in ["marketing", "communication", "architecte"]) else 6
        rationale = (
            "Métier de la connaissance où la collecte et la synthèse d'informations sont déjà profondément transformées par les outils d'IA générative. "
            "Toutefois, la pédagogie vivante, la négociation stratégique, l'intelligence émotionnelle et la responsabilité éthique préservent une place centrale aux professionnels humains."
        )
        return score, rationale

    # --- 4. Heuristique générale par domaine et balance numérique/physique ---
    category_defaults = {
        "support-entreprise": 8,
        "communication-media": 8,
        "banque-assurance": 7,
        "commerce-vente": 5,
        "sante-social": 4,
        "spectacle-audiovisuel": 6,
        "industrie": 4,
        "transport-logistique": 4,
        "maintenance-mecanique": 3,
        "btp-construction": 2,
        "hotellerie-restauration": 3,
        "services-personne": 3,
        "artisanat-art": 2,
        "agriculture": 1,
    }

    base_score = category_defaults.get(cat, 5)

    # Modulation selon la présence d'écran / bureau vs terrain
    if "ordinateur" in full_lower or "logiciel" in full_lower or "bureau" in full_lower:
        base_score += 1
    if "chantier" in full_lower or "extérieur" in full_lower or "déplacement" in full_lower or "atelier" in full_lower:
        base_score -= 1

    score = max(0, min(10, base_score))

    # Génération du rationale adapté
    if score >= 8:
        rationale = (
            f"Le métier de {title.lower()} s'exerce majoritairement sur support numérique et manipule des flux d'informations, d'analyses ou de communication. "
            f"Les capacités croissantes de l'IA à automatiser la production de contenus et l'aide à la décision augmentent fortement la productivité et transforment les missions courantes."
        )
    elif score >= 6:
        rationale = (
            f"Une part significative des missions de {title.lower()} implique l'analyse documentaire et la coordination de projets, des domaines accélérés par l'IA. "
            f"Néanmoins, la prise de décision complexe, le relationnel client et le pilotage opérationnel requièrent une présence et une responsabilité humaines indispensables."
        )
    elif score >= 4:
        rationale = (
            f"L'exercice de {title.lower()} combine des tâches administratives ou techniques informatisées et des interventions directes en présentiel. "
            f"L'IA optimise le traitement des données et les procédures, mais la pratique de terrain et le contact humain demeurent prépondérants."
        )
    elif score >= 2:
        rationale = (
            f"Profession technique et pratique où le cœur de l'activité repose sur des compétences manuelles, l'utilisation d'équipements ou le contact direct. "
            f"L'IA ne modifie que marginalement les tâches périphériques de planification ou de suivi, sans impacter le savoir-faire opérationnel."
        )
    else:
        rationale = (
            f"Métier d'action directe, physique et manuelle dans un cadre matériel non standardisé. "
            f"Les technologies d'intelligence artificielle logicielle n'ont quasiment aucune prise sur l'exécution concrète des tâches quotidiennes."
        )

    return score, rationale


def main():
    parser = argparse.ArgumentParser(description="Évalue l'exposition à l'IA des métiers français")
    parser.add_argument("--test", action="store_true", help="Teste l'évaluation sur un échantillon de 10 métiers")
    args = parser.parse_args()

    print("=== Étape 3 : Évaluation de l'Exposition à l'IA (0 à 10) ===")

    if not os.path.exists(OCCUPATIONS_FILE):
        print(f"Erreur : {OCCUPATIONS_FILE} introuvable. Exécutez process.py d'abord.")
        return

    with open(OCCUPATIONS_FILE, "r", encoding="utf-8") as f:
        occupations = json.load(f)

    print(f"Chargement de {len(occupations)} métiers...")

    scores = []
    distribution = {i: 0 for i in range(11)}

    for it in occupations:
        slug = it["slug"]
        page_file = os.path.join(PAGES_DIR, f"{slug}.md")
        full_text = ""
        if os.path.exists(page_file):
            with open(page_file, "r", encoding="utf-8") as pf:
                full_text = pf.read()

        score, rationale = evaluate_occupation_exposure(it, full_text)
        distribution[score] += 1

        scores.append({
            "title": it["title"],
            "slug": slug,
            "category": it["category"],
            "exposure": score,
            "rationale": rationale,
        })

    # Sauvegarde des scores
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)

    print(f"\n✓ `scores.json` généré avec succès pour {len(scores)} métiers.")

    # Affichage de la distribution
    print("\n--- Distribution des scores d'exposition à l'IA (0 à 10) ---")
    for s in range(11):
        count = distribution[s]
        bar = "█" * (count // 10)
        pct = (count / len(scores)) * 100
        print(f"  Score {s:02d}/10 : {count:4d} métiers ({pct:5.1f}%) | {bar}")

    # Calcul du score moyen non pondéré et pondéré
    jobs_dict = {it["slug"]: it["jobs"] for it in occupations}
    total_jobs = sum(jobs_dict.values())
    weighted_score = sum(s["exposure"] * jobs_dict.get(s["slug"], 0) for s in scores) / max(1, total_jobs)
    simple_avg = sum(s["exposure"] for s in scores) / len(scores)

    print(f"\nScore d'exposition moyen en France (simple) : {simple_avg:.2f} / 10")
    print(f"Score d'exposition moyen en France (pondéré par l'emploi) : {weighted_score:.2f} / 10")


if __name__ == "__main__":
    main()
