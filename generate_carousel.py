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
        
        relative_thumbnail_path = thumbnail_path.relative_to(OUTPUT_HTML_FILE.parent).as_posix()
        items_html += f"""
        <div class="gallery-item">
            <input type="checkbox" class="checkbox" data-notebook-path="{notebook_path}">
            <a href="{colab_url}" target="_blank" title="{title}">
                <img src="{relative_thumbnail_path}" alt="{title}" loading="lazy">
                <div class="title-overlay">{title}</div>
            </a>
        </div>
        """

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Notebook Reports</title>
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
            margin-bottom: 40px;
            color: #e0e0e0;
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
        }}
        .gallery-item:hover {{
            transform: translateY(-8px);
            box-shadow: 0 12px 30px rgba(0,0,0,0.6);
        }}
        .gallery-item a {{
            display: block;
            text-decoration: none;
            color: inherit;
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
            padding: 40px 20px 20px;
            font-size: 1.1rem;
            font-weight: 600;
            text-align: left;
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.3s ease, transform 0.3s ease;
        }}
        .gallery-item:hover .title-overlay {{
            opacity: 1;
            transform: translateY(0);
        }}
        .gallery-item .checkbox {{
            position: absolute;
            top: 15px;
            left: 15px;
            width: 28px;
            height: 28px;
            cursor: pointer;
            z-index: 10;
            -webkit-appearance: none;
            appearance: none;
            background-color: rgba(255, 255, 255, 0.7);
            border: 2px solid #333;
            border-radius: 6px;
            transition: all 0.2s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            display: none; /* Hidden by default */
        }}
        body.selection-mode-active .gallery-item .checkbox {{
            display: block;
        }}
        .gallery-item .checkbox:hover {{
            background-color: #fff;
        }}
        .gallery-item .checkbox:checked {{
            background-color: #007bff;
            border-color: #0056b3;
        }}
        .gallery-item .checkbox:checked::after {{
            content: '✔';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-size: 18px;
            font-weight: bold;
        }}
        .selection-panel {{
            background-color: #2c2c2c;
            padding: 25px;
            margin-top: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            display: none; /* Hidden by default */
        }}
        body.selection-mode-active .selection-panel {{
            display: block;
        }}
        .selection-panel h2 {{
            margin-top: 0;
            font-size: 1.5rem;
            color: #e0e0e0;
        }}
        #selected-files {{
            width: 100%;
            height: 150px;
            background-color: #1a1a1a;
            color: #f0f0f0;
            border: 1px solid #444;
            border-radius: 8px;
            padding: 10px;
            font-family: "SF Mono", "Fira Code", "Courier New", monospace;
            font-size: 0.9rem;
        }}
        #copy-button {{
            margin-top: 15px;
            padding: 12px 20px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: background-color 0.2s ease;
        }}
        #copy-button:hover {{
            background-color: #0056b3;
        }}
        #copy-button:disabled {{
            background-color: #555;
            cursor: not-allowed;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            font-size: 0.9rem;
            color: #888;
        }}
        .footer a {{
            color: #00aaff;
            text-decoration: none;
            margin: 0 5px;
        }}
        .footer a:hover {{
            text-decoration: underline;
        }}
        .github-link {{
            display: inline-block;
            margin-top: 10px;
            font-weight: bold;
        }}
        #activate-selection-mode {{
            cursor: pointer;
            margin-left: 10px;
            font-weight: bold;
            color: #00aaff;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Notebook Reports Gallery</h1>
        <div class="gallery">
            {items_html}
        </div>
        <div class="selection-panel">
            <h2>Selected Notebooks</h2>
            <textarea id="selected-files" readonly placeholder="Select notebooks using the checkbox to see their paths here..."></textarea>
            <button id="copy-button" disabled>Copy List</button>
        </div>
        <div class="footer">
            <p>
                Made with ❤️ by <a href="https://www.linkedin.com/in/ali-hmaou-6b7b73146/" target="_blank">Ali Hmaou</a>
                <span id="activate-selection-mode" style="cursor: pointer; color: #00aaff; margin-left: 15px;">- Select Mode</span>
            </p>
            <p class="github-link">
                <a href="https://github.com/{GITHUB_REPO}" target="_blank">View on GitHub</a>
            </p>
        </div>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', () => {{
            const checkboxes = document.querySelectorAll('.checkbox');
            const selectedFilesTextarea = document.getElementById('selected-files');
            const copyButton = document.getElementById('copy-button');
            const activateButton = document.getElementById('activate-selection-mode');
            const body = document.body;

            if (activateButton) {{
                activateButton.addEventListener('click', () => {{
                    body.classList.add('selection-mode-active');
                    activateButton.style.display = 'none';
                }});
            }}

            function updateSelectedFiles() {{
                const selectedNotebooks = Array.from(checkboxes)
                    .filter(cb => cb.checked)
                    .map(cb => cb.dataset.notebookPath);
                
                selectedFilesTextarea.value = selectedNotebooks.join('\\n');
                copyButton.disabled = selectedNotebooks.length === 0;
            }}

            checkboxes.forEach(checkbox => {{
                checkbox.addEventListener('change', updateSelectedFiles);
            }});

            copyButton.addEventListener('click', () => {{
                selectedFilesTextarea.select();
                document.execCommand('copy');
                copyButton.textContent = 'Copied!';
                setTimeout(() => {{
                    copyButton.textContent = 'Copy List';
                }}, 2000);
            }});
        }});
    </script>
</body>
</html>
    """

    with open(OUTPUT_HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Successfully generated gallery at: {OUTPUT_HTML_FILE}")

if __name__ == "__main__":
    if GITHUB_REPO == "YOUR_USER/YOUR_REPO":
        print("Could not automatically determine GitHub repository.")
        print("Please edit generate_carousel.py and set the GITHUB_REPO variable manually.")
    else:
        generate_html_gallery()
