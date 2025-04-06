import gradio as gr
from summarise import summarize_pdf
import os
from dotenv import load_dotenv

load_dotenv()

def gradio_summarize(pdf_file):
    """
    Summarize a PDF file for the Gradio interface.
    
    Args:
        pdf_file: Uploaded PDF file object from Grado.
    
    Returns:
        str: Summary of the PDF content.
    """
    if pdf_file is None:
        return "Please upload a PDF file."
    
    # Save the uploaded file temporarily
    temp_path = f"/tmp/{pdf_file.name.split('/')[-1]}"
    with open(temp_path, "wb") as f:
        f.write(pdf_file.read())
    
    try:
        # Generate summary
        summary = summarize_pdf(temp_path)
        return summary
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

# Define Gradio interface
interface = gr.Interface(
    fn=gradio_summarize,
    inputs=gr.File(label="Upload PDF"),
    outputs=gr.Textbox(label="Summary"),
    title="PDF Summarizer",
    description="Upload a PDF file to get a summary using LangChain."
)

if __name__ == '__main__':
    interface.launch(server_name="0.0.0.0", server_port=7860)