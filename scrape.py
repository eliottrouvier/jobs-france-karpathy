"""
scrape.py - Collecte des données ouvertes du marché de l'emploi en France
-------------------------------------------------------------------------
Télécharge et met en cache les données publiques officielles :
1. Onisep Idéo-Fiches Métiers (XML exhaustif de plus de 1 100 métiers)
2. Onisep Idéo-Métiers (JSON avec correspondances ROME 4.0 et domaines)
3. France Travail ROME 4.0 (Arborescence officielle des 14 domaines et fiches métiers)
"""

import os
import zipfile
import httpx

RAW_DIR = "raw_data"
os.makedirs(RAW_DIR, exist_ok=True)

URLS = {
    "onisep_fiches_zip": "https://api.opendata.onisep.fr/downloads/5fe0808a2da6f/5fe0808a2da6f.zip",
    "onisep_metiers_json": "https://api.opendata.onisep.fr/downloads/5fa5949243f97/5fa5949243f97.json",
    "rome_arborescence_xlsx": "https://www.francetravail.org/files/live/sites/peorg/files/documents/Statistiques-et-analyses/Open-data/ROME/rome-arborescence-principale-juin-2026.xlsx",
}


def download_file(url: str, dest_path: str, description: str):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
        print(f"[CACHE] {description} déjà présent : {dest_path} ({os.path.getsize(dest_path) / (1024*1024):.2f} Mo)")
        return

    print(f"[DOWNLOAD] Téléchargement de {description}...")
    headers = {"User-Agent": "Mozilla/5.0 (compatible; JobsFrance/1.0; +https://github.com/eliottrouvier/jobs-france-karpathy)"}
    
    with httpx.Client(timeout=60.0, follow_redirects=True, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(resp.content)
            
    print(f"-> Sauvegardé avec succès : {dest_path} ({len(resp.content) / (1024*1024):.2f} Mo)")


def extract_zip(zip_path: str, extract_dir: str):
    with zipfile.ZipFile(zip_path, 'r') as z:
        for filename in z.namelist():
            target = os.path.join(extract_dir, filename)
            if not os.path.exists(target):
                print(f"[EXTRACT] Extraction de {filename}...")
                z.extract(filename, extract_dir)
            else:
                print(f"[CACHE] Fichier extrait déjà présent : {filename}")


def main():
    print("=== Étape 1 : Collecte Open Data France Travail & Onisep ===")
    
    # 1. Onisep Fiches Métiers XML (Zip)
    onisep_zip = os.path.join(RAW_DIR, "onisep_fiches_metiers.zip")
    download_file(URLS["onisep_fiches_zip"], onisep_zip, "Onisep Idéo-Fiches Métiers XML (Archive)")
    extract_zip(onisep_zip, RAW_DIR)

    # 2. Onisep Métiers JSON
    onisep_json = os.path.join(RAW_DIR, "onisep_metiers.json")
    download_file(URLS["onisep_metiers_json"], onisep_json, "Onisep Idéo-Métiers JSON")

    # 3. France Travail ROME 4.0 Arborescence XLSX
    rome_xlsx = os.path.join(RAW_DIR, "rome_arborescence.xlsx")
    download_file(URLS["rome_arborescence_xlsx"], rome_xlsx, "France Travail ROME 4.0 (Arborescence XLSX)")

    print("\n✓ Toutes les données ouvertes ont été collectées avec succès dans le dossier `raw_data/`.")


if __name__ == "__main__":
    main()
