# BatchBooks: Galerie de Notebooks Automatisée

Ce projet transforme une collection de notebooks Jupyter en une galerie web élégante, hébergée sur GitHub Pages. Chaque notebook est automatiquement exécuté, sa visualisation principale est capturée sous forme d'image, et une galerie interactive est générée, offrant un aperçu visuel de chaque analyse.

[![GitHub Pages Deploy](https://github.com/AliHmaou/batchbooks/actions/workflows/main.yml/badge.svg)](https://github.com/AliHmaou/batchbooks/actions/workflows/main.yml)

## Fonctionnalités

- **Traitement par lots :** Exécute automatiquement tous les notebooks d'un dossier désigné.
- **Exportation de visualisations :** Capture les graphiques Plotly, Matplotlib et les cartes Folium sous forme d'images PNG.
- **Galerie web interactive :** Génère une page `index.html` avec une galerie des notebooks, incluant des miniatures, des titres et des liens pour les ouvrir dans Google Colab.
- **Déploiement continu :** Utilise GitHub Actions pour automatiser la mise à jour de la galerie à chaque `push` sur la branche `main`.

## Comment ça marche ?

Le projet s'articule autour de deux scripts Python principaux et d'un workflow GitHub Actions :

1.  `process_notebook.py` :
    -   Parcourt le dossier `notebooks/`.
    -   Pour chaque notebook, il injecte dynamiquement une cellule de code à la fin.
    -   Cette cellule, une fois exécutée, identifie la variable de visualisation (nommée `dataviz` par convention) et l'exporte en tant que fichier PNG dans le dossier `published/notebooks/`.
    -   Il gère les bibliothèques Plotly, Matplotlib et Folium.

2.  `generate_carousel.py` :
    -   Analyse le contenu du dossier `published/notebooks/`.
    -   Pour chaque couple `.ipynb`/`.png`, il extrait le titre du notebook (depuis la première cellule Markdown).
    -   Il génère la page `published/index.html` qui affiche les PNG sous forme de galerie.
    -   Chaque image de la galerie est un lien qui ouvre le notebook correspondant directement dans Google Colab, en utilisant le dépôt GitHub comme source.

3.  `.github/workflows/main.yml` :
    -   Ce workflow s'active à chaque `push` sur la branche `main`.
    -   Il configure un environnement Python et installe les dépendances listées dans `requirements.txt`.
    -   Il exécute séquentiellement `process_notebook.py` puis `generate_carousel.py`.
    -   Enfin, il déploie le contenu du dossier `published/` sur la branche `gh-pages`, ce qui le rend disponible via GitHub Pages.

## Utilisation

### Prérequis

- Un compte GitHub.
- Python 3.8+ et `pip`.

### Installation locale

1.  **Clonez le dépôt :**
    ```bash
    git clone https://github.com/AliHmaou/batchbooks.git
    cd batchbooks
    ```

2.  **Créez un environnement virtuel et installez les dépendances :**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Sur Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

### Ajouter un nouveau notebook

1.  **Créez votre notebook** (`.ipynb`) et placez-le dans le dossier `notebooks/`.
2.  **Assurez-vous que la visualisation finale** que vous souhaitez afficher dans la galerie est assignée à une variable nommée `dataviz`.
3.  **Ajoutez un titre** dans la première cellule Markdown de votre notebook (ex: `# Mon Analyse Incroyable`).
4.  **Poussez vos changements** sur GitHub :
    ```bash
    git add notebooks/mon_nouveau_notebook.ipynb
    git commit -m "Ajout du notebook : Mon Analyse Incroyable"
    git push origin main
    ```

Le workflow GitHub Actions s'occupera du reste. Après quelques minutes, votre nouvelle analyse apparaîtra dans la galerie sur votre site GitHub Pages.
