import gradio as gr
import requests
import os

FLASK_API_URL = os.getenv("FLASK_API_URL", "http://flask-api:5000/summarize")

def summarize_pdf(filepath):
    try:
        with open(filepath, "rb") as f:
            response = requests.post(FLASK_API_URL, files={"file": f})
        return response.json().get("summary", "Error: No summary returned")
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    interface = gr.Interface(
        fn=summarize_pdf,
        inputs=gr.File(label="Upload PDF", type="filepath"),
        outputs=gr.Textbox(label="Summary"),
        title="PDF Summarizer",
        description="Upload a PDF to generate a summary"
    )
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True
    )