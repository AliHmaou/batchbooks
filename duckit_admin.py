import gradio as gr
import os
import subprocess
import sys
import io
from pathlib import Path

# --- Import functions from existing scripts ---
# We need to add the current directory to the path to import the other scripts
sys.path.append(os.getcwd())
from process_notebook import process_notebook
from generate_carousel import generate_html_gallery

# --- Configuration ---
NOTEBOOK_FOLDER = Path("./notebooks")

def get_available_notebooks():
    """Returns a list of notebook names in the notebooks folder."""
    if not NOTEBOOK_FOLDER.exists():
        return []
    return [f.name for f in NOTEBOOK_FOLDER.glob('*.ipynb')]

def upload_notebook(file):
    """Saves an uploaded notebook to the notebooks folder."""
    if file is None:
        return "No file uploaded.", gr.update(choices=get_available_notebooks())
    
    # The file object has a `name` attribute with the full path
    # We want to save it to our notebook folder
    file_path = Path(file.name)
    target_path = NOTEBOOK_FOLDER / file_path.name
    
    # Create the folder if it doesn't exist
    NOTEBOOK_FOLDER.mkdir(exist_ok=True)
    
    # Copy the file
    import shutil
    shutil.copy(file_path, target_path)
    
    return f"Notebook '{target_path.name}' uploaded successfully.", gr.update(choices=get_available_notebooks())

def run_processing(notebook_name):
    """Wrapper function to run the notebook processing and capture output."""
    if not notebook_name:
        return "Please select a notebook to process.", None
    
    notebook_path = NOTEBOOK_FOLDER / notebook_name
    output_png_path = notebook_path.with_suffix('.png').name
    # The process_notebook script saves the image in the notebook folder, let's construct the path
    image_path = NOTEBOOK_FOLDER / output_png_path
    
    # Redirect stdout to capture logs
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    
    try:
        process_notebook(str(notebook_path))
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
    finally:
        # Restore stdout
        sys.stdout = old_stdout

    log_output = redirected_output.getvalue()

    # Check if the image was created
    if image_path.exists():
        return log_output, str(image_path)
    else:
        # The image might be in the published folder, let's check there too
        published_image_path = Path("./published/notebooks") / output_png_path
        if published_image_path.exists():
            return log_output, str(published_image_path)
        return log_output, None

def run_gallery_generation():
    """Wrapper function to run the gallery generation and capture output."""
    # Redirect stdout to capture logs
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    
    try:
        generate_html_gallery()
        html_path = "./published/index.html"
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        return redirected_output.getvalue(), html_content, gr.File(value=html_path, visible=True)

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        return redirected_output.getvalue(), None, gr.File(visible=False)
    finally:
        # Restore stdout
        sys.stdout = old_stdout

with gr.Blocks() as demo:
    gr.Markdown("# Duckit Admin")
    
    with gr.Tab("Process Notebooks"):
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Upload Notebook")
                notebook_upload_button = gr.UploadButton("Click to Upload a Notebook", file_types=[".ipynb"])
                upload_status = gr.Textbox(label="Upload Status", interactive=False)
                
                gr.Markdown("### Process Notebook")
                notebook_dropdown = gr.Dropdown(choices=get_available_notebooks(), label="Select Notebook")
                process_button = gr.Button("Process")

            with gr.Column(scale=2):
                process_output = gr.Textbox(label="Output", lines=10, interactive=False)
                image_preview = gr.Image(label="Image Preview", type="filepath")

        notebook_upload_button.upload(upload_notebook, inputs=notebook_upload_button, outputs=[upload_status, notebook_dropdown])
        process_button.click(run_processing, inputs=notebook_dropdown, outputs=[process_output, image_preview])

    with gr.Tab("Generate Gallery"):
        gr.Markdown("Generate the `index.html` gallery page based on the notebooks in the `published/notebooks` directory.")
        gallery_button = gr.Button("Generate Gallery")
        gallery_output = gr.Textbox(label="Output", lines=10, interactive=False)
        
        with gr.Row():
            html_preview = gr.HTML(label="HTML Preview")
            download_button = gr.File(label="Download HTML", interactive=False, visible=False)

        gallery_button.click(run_gallery_generation, outputs=[gallery_output, html_preview, download_button])

if __name__ == "__main__":
    demo.launch(allowed_paths=["published"])
