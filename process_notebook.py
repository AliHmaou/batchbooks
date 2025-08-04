import sys
import json
import subprocess
import time
import textwrap
from pathlib import Path

# --- Configuration ---
FINAL_OBJECT_VARIABLE_NAME = "dataviz"  # Nouvelle convention
NOTEBOOK_FOLDER = Path("./notebooks")

def capture_folium_map(html_path, output_png_path):
    """Prend une capture d'écran d'un fichier HTML local avec Selenium."""
    print("--> Initialisation du navigateur headless pour la capture de la carte Folium...")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service as ChromeService
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
    except ImportError:
        print("ERREUR: 'selenium' et 'webdriver-manager' sont requis pour exporter Folium.", file=sys.stderr)
        print("Veuillez les installer avec : pip install selenium webdriver-manager", file=sys.stderr)
        return

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1600,1200") # Taille de la fenêtre virtuelle
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--hide-scrollbars")

    driver = None
    try:
        # webdriver-manager va télécharger et gérer le driver pour nous
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Ouvre le fichier HTML local en utilisant un URI de fichier
        driver.get(Path(html_path).resolve().as_uri())
        
        # Attente robuste que les tuiles de la carte soient chargées
        print("--> Attente du chargement des tuiles de la carte...")
        wait = WebDriverWait(driver, 15) # Attendre jusqu'à 15 secondes
        wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "leaflet-tile-loaded")))
        time.sleep(0.5) # Petite pause supplémentaire pour le rendu final
        
        driver.save_screenshot(output_png_path)
        print(f"--> Capture d'écran de la carte sauvegardée dans : {output_png_path}")
        
    except Exception as e:
        print(f"ERREUR lors de la capture d'écran avec Selenium : {e}", file=sys.stderr)
        print("Assurez-vous que Google Chrome est installé sur le système.", file=sys.stderr)
    finally:
        if driver:
            driver.quit()
        # Nettoyage du fichier HTML temporaire
        Path(html_path).unlink(missing_ok=True)


def create_export_cell(output_image_name, temp_html_name):
    """Crée le code source pour la cellule d'exportation de manière robuste."""
    # On injecte les variables au début du code de la cellule.
    # On utilise repr() pour s'assurer que les chaînes sont correctement échappées.
    injected_variables = f"""
# --- Variables injectées par le script ---
FINAL_OBJECT_VARIABLE_NAME = {repr(FINAL_OBJECT_VARIABLE_NAME)}
OUTPUT_IMAGE_NAME = {repr(output_image_name)}
TEMP_HTML_NAME = {repr(temp_html_name)}
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
        print(f"--> Détecté : Folium. Sauvegarde HTML dans : {TEMP_HTML_NAME}")
        final_object.save(TEMP_HTML_NAME)
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
    """Modifie, exécute et nettoie un notebook."""
    notebook_path = Path(notebook_path_str)
    output_png_path = notebook_path.with_suffix('.png')

    # --- VÉRIFICATION D'EXISTENCE ---
    if output_png_path.exists():
        print(f"L'image {output_png_path.name} existe déjà. Saut du traitement.")
        return

    print("-" * 50)
    print(f"Traitement du notebook : {notebook_path}")

    base_name = notebook_path.stem
    # Le notebook et le HTML temporaires sont créés à la racine pour l'exécution
    temp_notebook_path = Path(f"temp_{base_name}.ipynb")
    temp_html_path = Path(f"_temp_{base_name}.html")

    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb_content = json.load(f)

    # On passe les chemins complets à la cellule d'exportation
    nb_content['cells'].append(create_export_cell(str(output_png_path), str(temp_html_path)))

    with open(temp_notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb_content, f)

    try:
        print(f"Lancement de l'exécution de {temp_notebook_path}...")
        subprocess.run(
            [sys.executable, '-m', 'jupyter', 'nbconvert', '--execute',
             '--to', 'notebook', '--inplace', str(temp_notebook_path), '--allow-errors'],
            check=True, capture_output=True, text=True)
        print("Exécution terminée.")

        # POST-TRAITEMENT pour Folium
        if temp_html_path.exists():
            capture_folium_map(str(temp_html_path), str(output_png_path))
        else:
            print("Aucun fichier HTML temporaire trouvé, pas de post-traitement Folium nécessaire.")

    except subprocess.CalledProcessError as e:
        print(f"ERREUR lors de l'exécution de {notebook_path}.", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
    finally:
        temp_notebook_path.unlink(missing_ok=True)
        print(f"Nettoyage du fichier temporaire : {temp_notebook_path}")

if __name__ == "__main__":
    notebooks_to_run = [p for p in NOTEBOOK_FOLDER.glob('*.ipynb')
                        if not p.name.startswith(('temp_', '_temp_'))]

    if not notebooks_to_run:
        print("Aucun notebook .ipynb trouvé pour le traitement.")
    else:
        for notebook in notebooks_to_run:
            process_notebook(str(notebook))
    
    print("-" * 50)
    print("Batch terminé.")
