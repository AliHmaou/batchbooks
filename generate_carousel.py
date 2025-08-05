import json
import os
from pathlib import Path
import re

# --- Configuration ---
NOTEBOOK_FOLDER = Path("./published/notebooks")
OUTPUT_HTML_FILE = Path("./published/index.html")
# Automatically detect repo from git remote
GIT_REMOTE_URL = os.popen('git config --get remote.origin.url').read().strip()
# Extract user/repo from https://github.com/user/repo.git or git@github.com:user/repo.git
match = re.search(r'github\.com[/:]([\w-]+/[\w-]+)', GIT_REMOTE_URL)
if match:
    GITHUB_REPO = match.group(1).replace('.git', '')
else:
    # Fallback if the regex fails
    print("Warning: Could not determine GitHub repo from git remote. Using a placeholder.")
    GITHUB_REPO = "YOUR_USER/YOUR_REPO"


def get_notebook_title(notebook_path):
    """Extracts the title from the first markdown cell of a notebook."""
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for cell in data['cells']:
                if cell['cell_type'] == 'markdown':
                    # Find the first line that starts with '#'
                    for line in cell['source']:
                        if line.strip().startswith('#'):
                            # Remove '#' and extra whitespace
                            return line.strip().lstrip('#').strip()
    except (IOError, json.JSONDecodeError, KeyError) as e:
        print(f"Error reading or parsing {notebook_path}: {e}")
    return "Untitled Report" # Default title

def generate_html_gallery():
    """Generates the HTML file with the notebook gallery."""
    notebooks = sorted(NOTEBOOK_FOLDER.glob('*.ipynb'))
    
    items_html = ""
    for notebook_path in notebooks:
        thumbnail_path = notebook_path.with_suffix('.png')
        if not thumbnail_path.exists():
            print(f"Skipping {notebook_path.name}: corresponding PNG not found.")
            continue

        title = get_notebook_title(notebook_path)
        colab_url = f"https://colab.research.google.com/github/{GITHUB_REPO}/blob/main/{notebook_path}"
        
        # The path should be relative to the index.html file
        relative_thumbnail_path = thumbnail_path.relative_to(OUTPUT_HTML_FILE.parent).as_posix()
        html_preview_path = thumbnail_path.with_suffix('.html')
        
        # Check if an HTML preview exists for this notebook
        has_html_preview = html_preview_path.exists()
        
        # The path for the iframe should be relative to the index.html file
        relative_html_path = html_preview_path.relative_to(OUTPUT_HTML_FILE.parent).as_posix()

        click_action = ""
        if has_html_preview:
            click_action = f"openHtmlModal('{relative_html_path}')"
        else:
            click_action = f"openImageModal('{relative_thumbnail_path}')"

        items_html += f"""
        <div class="gallery-item" onclick="{click_action}" title="{title}">
            <img src="{relative_thumbnail_path}" alt="{title}" loading="lazy">
            <div class="title-overlay">
                <div class="overlay-content">
                    <h3>{title}</h3>
                    <div class="item-actions">
                        <a href="{colab_url}" target="_blank" class="colab-link" onclick="event.stopPropagation();">
                            <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
                        </a>
                    </div>
                </div>
            </div>
        </div>
        """

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Made with ❤️ and with duckit</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #1a1a1a;
            color: #f0f0f0;
            margin: 0;
            padding: 40px;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 20px; /* Adjusted margin */
            color: #e0e0e0;
        }}
        .controls {{
            text-align: center;
            margin-bottom: 40px;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 25px;
        }}
        .gallery-item {{
            position: relative;
            overflow: hidden;
            border-radius: 12px;
            background-color: #2c2c2c;
            box-shadow: 0 8px 20px rgba(0,0,0,0.4);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            cursor: pointer;
        }}
        .gallery-item:hover {{
            transform: translateY(-8px);
            box-shadow: 0 12px 30px rgba(0,0,0,0.6);
        }}
        .gallery-item img {{
            width: 100%;
            height: auto;
            display: block;
            aspect-ratio: 4 / 3;
            object-fit: cover;
            transition: transform 0.3s ease;
        }}
        .gallery-item:hover img {{
            transform: scale(1.05);
        }}
        .title-overlay {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0) 100%);
            color: white;
            padding: 20px;
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.3s ease, transform 0.3s ease;
            display: flex;
            align-items: flex-end;
            pointer-events: none; /* Allow clicks to pass through to the parent */
        }}
        .gallery-item:hover .title-overlay {{
            opacity: 1;
            transform: translateY(0);
        }}
        .overlay-content {{
            width: 100%;
        }}
        .overlay-content h3 {{
            margin: 0 0 10px 0;
            font-size: 1.1rem;
            font-weight: 600;
        }}
        .item-actions {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .colab-link img {{
            height: 24px;
            width: 150px;
        }}
        /* Modal styles */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0; top: 0;
            width: 100%; height: 100%;
            background-color: rgba(0,0,0,0.8);
            align-items: center;
            justify-content: center;
        }}
        .modal-content {{
            /* The container can be flexible */
        }}
        .modal-content img {{
            width: auto;
            height: auto;
            max-width: 90vw;
            max-height: 90vh;
            object-fit: contain;
        }}
        .html-modal-content {{
            width: 90%;
            height: 90%;
            background-color: #1c1c1c;
            border-radius: 10px;
            overflow: hidden;
        }}
        .html-modal-content iframe {{
            width: 100%;
            height: 100%;
            border: none;
        }}
        .close-button {{
            position: absolute;
            top: 20px;
            right: 35px;
            color: #f1f1f1;
            font-size: 40px;
            font-weight: bold;
            transition: 0.3s;
            cursor: pointer;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            font-size: 0.9rem;
            color: #888;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Made with ❤️ and with duckit</h1>
        <div class="gallery">{items_html}</div>
        <div class="footer">
             <p>
                Made with ❤️ and with duckit
            </p>
        </div>
    </div>

    <!-- Image Modal -->
    <div id="image-modal" class="modal" onclick="closeImageModal()">
        <span class="close-button" onclick="closeImageModal()">&times;</span>
        <div class="modal-content" onclick="event.stopPropagation()">
            <img id="modal-image">
        </div>
    </div>

    <!-- HTML Content Modal -->
    <div id="html-modal" class="modal" onclick="closeHtmlModal()">
        <span class="close-button" onclick="closeHtmlModal()">&times;</span>
        <div class="html-modal-content" onclick="event.stopPropagation()">
            <iframe id="html-iframe" src=""></iframe>
        </div>
    </div>

    <script>
        function openImageModal(src) {{
            document.getElementById('modal-image').src = src;
            document.getElementById('image-modal').style.display = 'flex';
        }}

        function closeImageModal() {{
            document.getElementById('image-modal').style.display = 'none';
            document.getElementById('modal-image').src = '';
        }}

        function openHtmlModal(src) {{
            document.getElementById('html-iframe').src = src;
            document.getElementById('html-modal').style.display = 'flex';
        }}

        function closeHtmlModal() {{
            document.getElementById('html-modal').style.display = 'none';
            document.getElementById('html-iframe').src = ''; // Stop content
        }}

        // Close modals with the Escape key
        document.addEventListener('keydown', function(event) {{
            if (event.key === "Escape") {{
                closeImageModal();
                closeHtmlModal();
            }}
        }});
    </script>
</body>
</html>
""".replace("{{", "{{").replace("}}", "}}").replace('{items_html}', items_html)

    with open(OUTPUT_HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Successfully generated gallery at: {OUTPUT_HTML_FILE}")

if __name__ == "__main__":
    if GITHUB_REPO == "YOUR_USER/YOUR_REPO":
        print("Could not automatically determine GitHub repository.")
        print("Please edit generate_carousel.py and set the GITHUB_REPO variable manually.")
    else:
        generate_html_gallery()
