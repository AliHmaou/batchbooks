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

def capture_html_screenshot(html_path, output_png_path):
    """Prend une capture d'écran adaptative d'un fichier HTML local avec Selenium."""
    print("--> Initialisation du navigateur headless pour la capture HTML...")
    try:
        from selenium import webdriver
        from selenium.common.exceptions import TimeoutException, WebDriverException
        from selenium.webdriver.chrome.service import Service as ChromeService
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
    except ImportError:
        print("ERREUR: 'selenium' et 'webdriver-manager' sont requis.", file=sys.stderr)
        print("Veuillez les installer avec : pip install selenium webdriver-manager", file=sys.stderr)
        return

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--hide-scrollbars")
    # La taille de la fenêtre sera définie dynamiquement

    driver = None
    try:
        print("--> Vérification/téléchargement du WebDriver...")
        try:
            service = ChromeService(ChromeDriverManager().install())
        except Exception as e:
            print("ERREUR CRITIQUE: Impossible de télécharger ou d'installer le WebDriver pour Chrome.", file=sys.stderr)
            print(f"Détail de l'erreur : {e}", file=sys.stderr)
            print("Vérifiez votre connexion internet ou la configuration de votre pare-feu.", file=sys.stderr)
            return

        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(Path(html_path).resolve().as_uri())

        print("--> Attente du chargement du contenu interactif...")
        wait = WebDriverWait(driver, 20) # Timeout augmenté à 20 secondes

        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                header = f.read(4096)

            if 'plotly' in header:
                print("--> Détecté : Plotly. Attente du conteneur du graphique.")
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".svg-container, .main-svg, .plotly-graph-div")))
            elif 'folium' in header or 'leaflet' in header:
                print("--> Détecté : Folium/Leaflet. Attente des tuiles de la carte.")
                wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "leaflet-tile-loaded")))
            elif 'altair' in header or 'vega' in header:
                print("--> Détecté : Altair/Vega. Attente du canvas.")
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "canvas")))
            elif 'bokeh' in header:
                print("--> Détecté : Bokeh. Attente du canvas.")
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "bk-canvas")))
            else:
                print("--> Type de HTML non reconnu, pause de sécurité (3s).")
                time.sleep(3)
        except TimeoutException:
            print("AVERTISSEMENT: Le contenu interactif n'a pas été détecté dans le temps imparti.", file=sys.stderr)
            print("--> Utilisation d'une pause de sécurité étendue (5s).", file=sys.stderr)
            time.sleep(5)

        time.sleep(1.5) # Pause supplémentaire pour le rendu final

        print("--> Ajustement dynamique de la taille de la fenêtre...")
        try:
            # On mesure la taille du contenu de la page
            size = driver.execute_script("""
                return {
                    width: document.body.scrollWidth,
                    height: document.body.scrollHeight
                }
            """)
            width = size['width'] + 20  # Ajout d'une petite marge
            height = size['height'] + 20
            
            print(f"--> Contenu détecté : {size['width']}x{size['height']}. Redimensionnement à {width}x{height}.")
            driver.set_window_size(width, height)
            time.sleep(0.5) # Laisse le temps au navigateur de redessiner

        except Exception as e:
            print(f"AVERTISSEMENT: Impossible d'ajuster la taille dynamiquement. Utilisation de 1600x1200. Erreur: {e}", file=sys.stderr)
            driver.set_window_size(1600, 1200)

        driver.save_screenshot(output_png_path)
        print(f"--> Capture d'écran sauvegardée dans : {output_png_path}")

    except WebDriverException as e:
        print(f"ERREUR WebDriver: {e}", file=sys.stderr)
        print("Assurez-vous que Google Chrome est installé et accessible.", file=sys.stderr)
    except Exception as e:
        print(f"ERREUR inattendue lors de la capture d'écran : {e}", file=sys.stderr)
    finally:
        if driver:
            driver.quit()


def center_html_content(html_path):
    """Injecte du CSS pour améliorer l'affichage, sans forcer un centrage qui pourrait nuire à la capture."""
    print(f"--> Ajustement CSS pour : {html_path}")
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Style plus simple: assure un fond blanc et un minimum de padding.
        # Ne force plus le centrage flexbox qui peut casser la mesure de la taille.
        style_wrapper = """
<style>
    body {
        background-color: #ffffff; /* Fond blanc pour la capture */
        margin: 0;
        padding: 10px; /* Un peu d'espace autour */
    }
</style>
"""
        if '</head>' in content:
            content = content.replace('</head>', f'{style_wrapper}</head>', 1)
        else:
            content = f"<head>{style_wrapper}</head>" + content

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("--> CSS ajusté avec succès.")

    except Exception as e:
        print(f"AVERTISSEMENT: N'a pas pu ajuster le CSS. Erreur: {e}", file=sys.stderr)


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
# On importe les modules nécessaires pour l'export au cas où
try:
    from bokeh.io import save as bokeh_save
except ImportError:
    bokeh_save = None

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
        print(f"--> Détecté : Plotly. Sauvegarde HTML et PNG.")
        # 1. Sauvegarde HTML pour l'interactivité
        print(f"--> Sauvegarde HTML dans : {OUTPUT_HTML_NAME}")
        final_object.write_html(OUTPUT_HTML_NAME, include_plotlyjs='cdn')
        # 2. Sauvegarde PNG pour l'aperçu statique
        try:
            print(f"--> Tentative de sauvegarde PNG directe dans : {OUTPUT_IMAGE_NAME}")
            final_object.write_image(OUTPUT_IMAGE_NAME, scale=3, width=1200, height=800)
            print(f"--> Image Plotly sauvegardée avec succès.")
        except Exception as e:
            print(f"AVERTISSESEMENT: La sauvegarde directe en PNG a échoué (kaleido est-il installé?). L'image statique ne sera pas générée.", file=sys.stderr)
            print(f"   Erreur: {e}", file=sys.stderr)
    elif 'folium.folium.Map' in object_type:
        print(f"--> Détecté : Folium. Sauvegarde HTML dans : {OUTPUT_HTML_NAME}")
        final_object.save(OUTPUT_HTML_NAME)
        # On crée un fichier marqueur pour que le script de post-traitement sache qu'il s'agit de Folium
        with open(f"{OUTPUT_HTML_NAME}.is_folium", "w") as f:
            f.write("true")
    elif 'altair.vegalite' in object_type and hasattr(final_object, 'save'):
        print(f"--> Détecté : Altair. Sauvegarde HTML dans : {OUTPUT_HTML_NAME}")
        final_object.save(OUTPUT_HTML_NAME)
    elif 'bokeh.plotting' in object_type and bokeh_save is not None:
        print(f"--> Détecté : Bokeh. Sauvegarde HTML dans : {OUTPUT_HTML_NAME}")
        bokeh_save(final_object, filename=OUTPUT_HTML_NAME, title="")
    elif 'matplotlib.figure.Figure' in object_type:
        print(f"--> Détecté : Matplotlib. Sauvegarde dans : {OUTPUT_IMAGE_NAME}")
        final_object.savefig(OUTPUT_IMAGE_NAME, dpi=300, bbox_inches='tight')
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

        # POST-TRAITEMENT : capture d'écran pour Folium uniquement
        if dest_html_path.exists():
            folium_marker_path = Path(f"{dest_html_path}.is_folium")
            if folium_marker_path.exists():
                print("--> Fichier HTML Folium détecté. Lancement de la capture d'écran.")
                center_html_content(str(dest_html_path))
                capture_html_screenshot(str(dest_html_path), str(dest_png_path))
                folium_marker_path.unlink() # Nettoyage du marqueur
            else:
                print(f"--> Fichier HTML {dest_html_path.name} trouvé, mais ce n'est pas une carte Folium. Capture d'écran sautée.")
        else:
            print("--> Aucun fichier HTML trouvé, pas de capture d'écran nécessaire.")

        # Si tout réussit, on déplace le notebook exécuté et on supprime l'original
        PUBLISHED_NOTEBOOK_FOLDER.mkdir(parents=True, exist_ok=True)
        shutil.move(str(temp_notebook_path), str(dest_notebook_path))
        notebook_path.unlink()
        print(f"Le notebook '{notebook_path.name}' a été traité et déplacé vers '{dest_notebook_path}'.")

    except subprocess.CalledProcessError as e:
        print(f"ERREUR lors de l'exécution de {notebook_path.name}.", file=sys.stderr)
        print("--- STDOUT ---")
        print(e.stdout)
        print("--- STDERR ---", file=sys.stderr)
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
