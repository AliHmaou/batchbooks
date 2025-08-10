import gradio as gr
import os
import subprocess
import sys
import io
import shutil
import zipfile
from pathlib import Path

# --- Import functions from existing scripts ---
sys.path.append(os.getcwd())
from process_notebook import process_notebook
from generate_carousel import generate_html_gallery

# --- Configuration ---
NOTEBOOK_FOLDER = Path("./notebooks")
PUBLISHED_FOLDER = Path("./published")
PUBLISHED_NOTEBOOKS_FOLDER = PUBLISHED_FOLDER / "notebooks"
GALLERY_ZIP_PATH = Path("./gallery.zip")

# --- Ensure directories exist ---
NOTEBOOK_FOLDER.mkdir(exist_ok=True)
PUBLISHED_FOLDER.mkdir(exist_ok=True)
PUBLISHED_NOTEBOOKS_FOLDER.mkdir(exist_ok=True)

def upload_and_process(file):
    """Saves an uploaded notebook and processes it immediately."""
    if file is None:
        return "No file uploaded.", None, None, gr.Button(visible=False), None

    # Save the uploaded file
    file_path = Path(file.name)
    target_path = NOTEBOOK_FOLDER / file_path.name
    shutil.copy(file_path, target_path)

    # Process the notebook
    log_output, image_path = run_processing(target_path)

    if image_path and Path(image_path).exists():
        return f"Processed '{target_path.name}'.", log_output, image_path, gr.Button(visible=True), str(target_path)
    else:
        return f"Processed '{target_path.name}' but image not found.", log_output, None, gr.Button(visible=False), None

def run_processing(notebook_path):
    """Wrapper function to run the notebook processing and capture output."""
    output_png_path = notebook_path.with_suffix('.png')
    
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    
    try:
        process_notebook(str(notebook_path))
    except Exception as e:
        print(f"An error occurred during processing: {e}", file=sys.stderr)
    finally:
        sys.stdout = old_stdout

    log_output = redirected_output.getvalue()

    if output_png_path.exists():
        return log_output, str(output_png_path)
    else:
        return log_output, None

def add_to_gallery(notebook_path_str):
    """Adds the processed notebook to the gallery and regenerates it."""
    if not notebook_path_str:
        return "No notebook to add.", None, gr.File(visible=False)

    notebook_path = Path(notebook_path_str)
    
    # Define source and destination paths
    files_to_copy = [
        notebook_path,
        notebook_path.with_suffix('.html'),
        notebook_path.with_suffix('.png')
    ]
    
    for src_path in files_to_copy:
        if src_path.exists():
            shutil.copy(src_path, PUBLISHED_NOTEBOOKS_FOLDER / src_path.name)

    # Regenerate gallery
    log_output, html_content, _ = run_gallery_generation()
    
    return f"'{notebook_path.name}' added to gallery.", html_content, gr.File(visible=False)

def run_gallery_generation():
    """Wrapper function to run the gallery generation."""
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    
    try:
        generate_html_gallery()
        html_path = PUBLISHED_FOLDER / "index.html"
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        return redirected_output.getvalue(), html_content, gr.File(value=str(html_path), visible=True)

    except Exception as e:
        print(f"An error occurred during gallery generation: {e}", file=sys.stderr)
        return redirected_output.getvalue(), None, gr.File(visible=False)
    finally:
        sys.stdout = old_stdout

def package_gallery():
    """Creates a zip archive of the published gallery."""
    with zipfile.ZipFile(GALLERY_ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(PUBLISHED_FOLDER):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(PUBLISHED_FOLDER)
                zipf.write(file_path, arcname)
    
    return f"Gallery packaged into '{GALLERY_ZIP_PATH}'", gr.File(value=str(GALLERY_ZIP_PATH), visible=True)


with gr.Blocks() as demo:
    gr.Markdown("# Duckit Admin - Streamlined Workflow")
    
    # State to hold the path of the last processed notebook
    processed_notebook_path = gr.State()

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 1. Upload & Process Notebook")
            notebook_upload_button = gr.UploadButton("Click to Upload a Notebook", file_types=[".ipynb"])
            upload_status = gr.Textbox(label="Status", interactive=False)
            
            gr.Markdown("### 2. Review Output")
            process_output = gr.Textbox(label="Processing Logs", lines=10, interactive=False)
            image_preview = gr.Image(label="Image Preview", type="filepath")
            
            gr.Markdown("### 3. Add to Gallery")
            add_gallery_button = gr.Button("Add to Gallery", visible=False)
            gallery_add_status = gr.Textbox(label="Status", interactive=False)

        with gr.Column(scale=2):
            gr.Markdown("### 4. Gallery Preview & Packaging")
            html_preview = gr.HTML(label="Live Gallery Preview")
            
            package_button = gr.Button("Package Gallery for Deployment")
            package_status = gr.Textbox(label="Packaging Status", interactive=False)
            download_button = gr.File(label="Download Packaged Gallery", interactive=False, visible=False)

    # Wire up the components
    notebook_upload_button.upload(
        upload_and_process,
        inputs=notebook_upload_button,
        outputs=[upload_status, process_output, image_preview, add_gallery_button, processed_notebook_path]
    )
    
    add_gallery_button.click(
        add_to_gallery,
        inputs=processed_notebook_path,
        outputs=[gallery_add_status, html_preview, download_button]
    )

    package_button.click(
        package_gallery,
        outputs=[package_status, download_button]
    )
    
    # Initial gallery load
    def initial_load():
        _, html_content, _ = run_gallery_generation()
        return html_content

    demo.load(initial_load, outputs=html_preview)


if __name__ == "__main__":
    demo.launch(allowed_paths=[str(PUBLISHED_FOLDER), str(NOTEBOOK_FOLDER)])
