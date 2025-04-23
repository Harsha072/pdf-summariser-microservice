import gradio as gr
import requests
import os

# API endpoints
FLASK_API_URL_SUMMARIZE = os.getenv("FLASK_API_URL_SUMMARIZE", "http://localhost:5000/summarize")
FLASK_API_URL_ASK = os.getenv("FLASK_API_URL_ASK", "http://localhost:5000/ask")
FLASK_API_URL_UPLOAD = os.getenv("FLASK_API_URL_UPLOAD", "http://localhost:5000/upload")

def upload_pdf(filepath):
    """Uploads a PDF file to the Flask API for processing"""
    if not filepath:
        return None, "Error: No file provided"
    
    try:
        with open(filepath, "rb") as f:
            response = requests.post(FLASK_API_URL_UPLOAD, files={"file": f})
            response.raise_for_status()
        
        data = response.json()
        return (
            data.get("doc_id"), 
            f"✅ File processed successfully! {data.get('pages_processed', 0)} pages indexed."
        )
    except Exception as e:
        return None, f"Error: {str(e)}"

def summarize_pdf(doc_id):
    """Generates a summary of the uploaded PDF"""
    if not doc_id:
        return "Please upload a document first"
    
    try:
        response = requests.post(
            FLASK_API_URL_SUMMARIZE,
            json={"doc_id": doc_id}
        )
        response.raise_for_status()
        print(response)
        return response.json().get("answer", "No summary available")
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def ask_question(question, doc_id):
    """Asks a question about the uploaded PDF"""
    if not doc_id:
        return "Please upload a document first"
    if not question:
        return "Please enter a question"
    
    try:
        response = requests.post(
            FLASK_API_URL_ASK,
            json={
                "doc_id": doc_id,
                "question": question
            }
        )
        response.raise_for_status()
        return response.json().get("answer", "No answer available")
    except Exception as e:
        return f"Error getting answer: {str(e)}"

if __name__ == "__main__":
    with gr.Blocks(title="PDF AI Assistant") as interface:
        gr.Markdown("""
        # PDF Summarizer and Question Answering
        Upload a PDF document to get started. Once processed, you can generate a summary or ask questions about the content.
        """)
        
        # Store document ID in state
        doc_id = gr.State()
        
        # Upload Section
        with gr.Row():
            with gr.Column():
                pdf_input = gr.File(label="Upload PDF", type="filepath")
                upload_button = gr.Button("Upload Document", variant="primary")
            upload_status = gr.Textbox(label="Status", interactive=False, elem_id="status")
        
        # Tabs for Summary and Q&A
        with gr.Tabs():
            with gr.Tab("Summarize"):
                summary_output = gr.Markdown(label="Summary")
                summarize_button = gr.Button("Generate Summary", variant="primary")
                
            with gr.Tab("Ask Questions"):
                question_input = gr.Textbox(
                    label="Ask a Question",
                    placeholder="Type your question about the document here..."
                )
                answer_output = gr.Markdown(label="Answer")
                ask_button = gr.Button("Ask", variant="primary")
        
        # Event handling
        upload_button.click(
            fn=upload_pdf,
            inputs=[pdf_input],
            outputs=[doc_id, upload_status]
        )
        
        summarize_button.click(
            fn=summarize_pdf,
            inputs=[doc_id],
            outputs=[summary_output]
        )
        
        ask_button.click(
            fn=ask_question,
            inputs=[question_input, doc_id],
            outputs=[answer_output]
        )

    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True
    )