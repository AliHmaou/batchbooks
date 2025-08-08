import sys
import json
import subprocess
import time
import textwrap
import shutil
from pathlib import Path

# --- Configuration ---
FINAL_OBJECT_VARIABLE_NAME = "dataviz"
ROOT_NOTEBOOK_FOLDER = Path(".")
PUBLISHED_NOTEBOOK_FOLDER = Path("./published/notebooks")

def capture_folium_map(html_path, output_png_path):
    """Prend une capture d'écran d'un fichier HTML local avec Playwright."""
    print("--> Initialisation du navigateur headless (Playwright) pour la capture de la carte Folium...")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERREUR: 'playwright' est requis pour exporter Folium.", file=sys.stderr)
        print("Veuillez l'installer avec : pip install playwright", file=sys.stderr)
        print("N'oubliez pas d'installer les navigateurs : playwright install", file=sys.stderr)
        return

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1600, "height": 1200})

            # Ouvre le fichier HTML local en utilisant un URI de fichier
            file_uri = Path(html_path).resolve().as_uri()
            print(f"--> Navigation vers : {file_uri}")
            page.goto(file_uri, wait_until="networkidle")

            # Attente robuste que les tuiles de la carte soient chargées
            print("--> Attente du chargement des tuiles de la carte (sélecteur .leaflet-tile-loaded)...")
            page.wait_for_selector(".leaflet-tile-loaded", state="visible", timeout=15000)
            time.sleep(0.5) # Petite pause supplémentaire pour le rendu final

            page.screenshot(path=output_png_path)
            print(f"--> Capture d'écran de la carte sauvegardée dans : {output_png_path}")

            browser.close()

    except Exception as e:
        print(f"ERREUR lors de la capture d'écran avec Playwright : {e}", file=sys.stderr)


def create_export_cell(output_image_name, output_html_name):
    """Crée le code source pour la cellule d'exportation de manière robuste."""
    # On injecte les variables au début du code de la cellule.
    # On utilise repr() pour s'assurer que les chaînes sont correctement échappées.
    injected_variables = f"""
# --- Variables injectées par le script ---
FINAL_OBJECT_VARIABLE_NAME = {repr(FINAL_OBJECT_VARIABLE_NAME)}
OUTPUT_IMAGE_NAME = {repr(output_image_name)}
OUTPUT_HTML_NAME = {repr(output_html_name)}
"""

    # La logique d'exportation est une chaîne de caractères brute.
    # Les f-strings à l'intérieur seront interprétées par le noyau Jupyter, pas par ce script.
    export_logic = r"""
# ===================================================================
# CELLULE INJECTÉE AUTOMATIQUEMENT (VERSION ROBUSTE)
# ===================================================================
import sys
import os

try:
    # On s'assure que le dossier de sortie existe
    output_dir = os.path.dirname(OUTPUT_IMAGE_NAME)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # On utilise globals().get() pour une récupération plus sûre
    final_object = globals().get(FINAL_OBJECT_VARIABLE_NAME)

    if final_object is None:
        # On lève une NameError pour être cohérent avec le code original
        raise NameError(f"name '{FINAL_OBJECT_VARIABLE_NAME}' is not defined")

    print(f"INFO: Variable '{FINAL_OBJECT_VARIABLE_NAME}' trouvée. Tentative d'exportation...")

    object_type = str(type(final_object))

    if 'plotly.graph_objs._figure.Figure' in object_type:
        print(f"--> Détecté : Plotly. Sauvegarde dans : {OUTPUT_IMAGE_NAME}")
        final_object.write_image(OUTPUT_IMAGE_NAME, scale=2, width=1200, height=800)
    elif 'matplotlib.figure.Figure' in object_type:
        print(f"--> Détecté : Matplotlib. Sauvegarde dans : {OUTPUT_IMAGE_NAME}")
        final_object.savefig(OUTPUT_IMAGE_NAME, dpi=300, bbox_inches='tight')
    elif 'folium.folium.Map' in object_type:
        print(f"--> Détecté : Folium. Sauvegarde HTML dans : {OUTPUT_HTML_NAME}")
        final_object.save(OUTPUT_HTML_NAME)
    else:
        print(f"AVERTISSEMENT: Type non supporté : {object_type}", file=sys.stderr)
except NameError:
    print(f"AVERTISSEMENT: Aucune variable '{FINAL_OBJECT_VARIABLE_NAME}' trouvée.", file=sys.stderr)
except Exception as e:
    print(f"ERREUR lors de l'exportation : {e}", file=sys.stderr)
"""
    export_code = textwrap.dedent(injected_variables) + textwrap.dedent(export_logic)

    return {
        "cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
        "source": export_code.splitlines(True)
    }

def process_notebook(notebook_path_str):
    """Modifie, exécute, et déplace un notebook du répertoire racine vers le dossier de publication."""
    notebook_path = Path(notebook_path_str)

    # Définir les chemins de destination dans `published/notebooks`
    dest_notebook_path = PUBLISHED_NOTEBOOK_FOLDER / notebook_path.name
    dest_png_path = dest_notebook_path.with_suffix('.png')
    dest_html_path = dest_notebook_path.with_suffix('.html')

    # --- VÉRIFICATION D'EXISTENCE ---
    if dest_png_path.exists():
        print(f"AVERTISSEMENT: L'image {dest_png_path.name} existe déjà dans la destination.")
        print(f"Le notebook '{notebook_path.name}' n'a pas été traité. Veuillez le renommer ou le supprimer.")
        return

    print("-" * 50)
    print(f"Traitement du notebook : {notebook_path.name}")

    base_name = notebook_path.stem
    temp_notebook_path = Path(f"temp_{base_name}.ipynb")

    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb_content = json.load(f)

    # La cellule d'exportation pointera directement vers la destination finale
    nb_content['cells'].append(create_export_cell(str(dest_png_path), str(dest_html_path)))

    with open(temp_notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb_content, f)

    try:
        print(f"Lancement de l'exécution de {temp_notebook_path.name}...")
        subprocess.run(
            [sys.executable, '-m', 'jupyter', 'nbconvert', '--execute',
             '--to', 'notebook', '--inplace', str(temp_notebook_path), '--allow-errors'],
            check=True, capture_output=True, text=True, encoding='utf-8')
        print("Exécution terminée.")

        # POST-TRAITEMENT pour Folium
        if dest_html_path.exists():
            capture_folium_map(str(dest_html_path), str(dest_png_path))
            dest_html_path.unlink() # Nettoyage du fichier HTML temporaire
        else:
            print("Aucun fichier HTML de Folium trouvé, pas de post-traitement nécessaire.")

        # Si tout réussit, on déplace le notebook exécuté et on supprime l'original
        PUBLISHED_NOTEBOOK_FOLDER.mkdir(parents=True, exist_ok=True)
        shutil.move(str(temp_notebook_path), str(dest_notebook_path))
        notebook_path.unlink()
        print(f"Le notebook '{notebook_path.name}' a été traité et déplacé vers '{dest_notebook_path}'.")

    except subprocess.CalledProcessError as e:
        print(f"ERREUR lors de l'exécution de {notebook_path.name}.", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        print(f"Le notebook original '{notebook_path.name}' a été laissé dans le répertoire racine pour inspection.", file=sys.stderr)
    finally:
        # Nettoie le fichier temporaire uniquement s'il existe encore (en cas d'échec)
        temp_notebook_path.unlink(missing_ok=True)


if __name__ == "__main__":
    # S'assurer que le dossier de publication existe
    PUBLISHED_NOTEBOOK_FOLDER.mkdir(parents=True, exist_ok=True)

    # Chercher les notebooks uniquement à la racine du projet
    notebooks_to_run = [p for p in ROOT_NOTEBOOK_FOLDER.glob('*.ipynb')
                        if not p.name.startswith(('temp_', '_temp_'))]

    if not notebooks_to_run:
        print("Aucun notebook .ipynb trouvé à la racine du projet pour le traitement.")
    else:
        print(f"Trouvé {len(notebooks_to_run)} notebook(s) à traiter...")
        for notebook in notebooks_to_run:
            process_notebook(str(notebook))
    
    print("-" * 50)
    print("Batch terminé.")
