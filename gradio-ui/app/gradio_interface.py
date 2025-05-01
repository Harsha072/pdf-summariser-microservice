import gradio as gr
import requests
import os
from typing import Tuple

BACKEND_URL = os.getenv("BACKEND_URL", "https://pdf-summariser-microservice.onrender.com")

# API endpoints
FLASK_API_URL_SUMMARIZE = f"{BACKEND_URL}/summarize"
FLASK_API_URL_ASK = f"{BACKEND_URL}/ask"
FLASK_API_URL_UPLOAD = f"{BACKEND_URL}/upload"
FLASK_API_URL_SAVE_SUMMARY = f"{BACKEND_URL}/save"
# Custom CSS for better styling
custom_css = """
.important-button {
    background: linear-gradient(45deg, #FF6B6B, #FF8E53) !important;
    border: none !important;
}
.important-button:hover {
    background: linear-gradient(45deg, #FF8E53, #FF6B6B) !important;
}
.processing-status {
    font-weight: bold;
    color: #4CAF50;
}
.error-status {
    font-weight: bold;
    color: #F44336;
}
"""

def upload_pdf(filepath: str) -> Tuple[str, str]:
    """Uploads a PDF file to the Flask API for processing"""
    if not filepath:
        return None, "❌ Error: No file provided"
    
    try:
        with open(filepath, "rb") as f:
            response = requests.post(
                FLASK_API_URL_UPLOAD, 
                files={"file": f},
                timeout=30
            )
            response.raise_for_status()
        
        data = response.json()
        return (
            data.get("doc_id"), 
            f"✅ {os.path.basename(filepath)} processed successfully! ({data.get('pages_processed', 0)} pages)"
        )
    except Exception as e:
        return None, f"❌ Error: {str(e)}"

def save_summary(doc_id: str, summary: str) -> str:
    """Saves the edited summary back to the backend."""
    if not doc_id:
        return "⚠️ Please upload a document first"
    if not summary.strip():
        return "⚠️ No summary to save"

    try:
        response = requests.post(
            FLASK_API_URL_SAVE_SUMMARY,
            json={"doc_id": doc_id, "summary": summary},
            timeout=10
        )
        response.raise_for_status()
        return "✅ Summary saved successfully!"
    except Exception as e:
        return f"❌ Error saving summary: {str(e)}"

def summarize_pdf(doc_id: str) -> str:
    """Generates a summary of the uploaded PDF"""
    if not doc_id:
        return "⚠️ Please upload a document first"
    
    try:
        response = requests.post(
            FLASK_API_URL_SUMMARIZE,
            json={"doc_id": doc_id},
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("answer", "No summary available")
    except Exception as e:
        return f"❌ Error generating summary: {str(e)}"

def ask_question(question: str, doc_id: str) -> str:
    """Asks a question about the uploaded PDF"""
    if not doc_id:
        return "⚠️ Please upload a document first"
    if not question.strip():
        return "⚠️ Please enter a question"
    
    try:
        response = requests.post(
            FLASK_API_URL_ASK,
            json={
                "doc_id": doc_id,
                "question": question
            },
            timeout=15
        )
        response.raise_for_status()
        answer = response.json().get("answer", "No answer available")
        sources = response.json().get("sources", [])
        if sources:
            answer += "\n\n📚 Sources:\n- " + "\n- ".join(sources)
        return answer
    except Exception as e:
        return f"❌ Error getting answer: {str(e)}"

if __name__ == "__main__":
    with gr.Blocks(title="PDF AI Assistant", css=custom_css) as interface:
        gr.Markdown("""
        # 📄 Ask PDF
        Upload a PDF document to generate summaries and ask questions
        """)

        with gr.Row():
            with gr.Column(scale=2):
                # Upload Section
                with gr.Group():
                    gr.Markdown("### 1. Upload Document")
                    pdf_input = gr.File(
                        label="Drag PDF here",
                        file_types=[".pdf"],
                        type="filepath"
                    )
                    upload_button = gr.Button(
                        "Process Document",
                        variant="primary",
                        elem_classes="important-button"
                    )
                    upload_status = gr.Textbox(
                        label="Status",
                        interactive=False,
                        elem_classes="processing-status"
                    )
                    doc_id = gr.State()

            with gr.Column(scale=3):
                # Summary Section
                with gr.Tab("📝 Summary"):
                    with gr.Group():
                        gr.Markdown("### 2. Generate & Edit Summary")
                        with gr.Row():
                            summarize_button = gr.Button(
                                "Generate Summary",
                                variant="primary"
                            )
                            save_button = gr.Button(
                                "Save Summary",
                                visible=True
                            )
                        summary_output = gr.Textbox(
                            label="Document Summary",
                            lines=12,
                            interactive=True,
                            placeholder="Summary will appear here..."
                        )
                        save_status = gr.Textbox(
                            label="Save Status",
                            visible=False
                        )

                # Q&A Section
                with gr.Tab("❓ Ask Questions"):
                    with gr.Group():
                        gr.Markdown("### 3. Ask About the Document")
                        question_input = gr.Textbox(
                            label="Your Question",
                            placeholder="What are the key findings in this document?",
                            lines=3
                        )
                        ask_button = gr.Button(
                            "Get Answer",
                            variant="primary"
                        )
                        answer_output = gr.Textbox(
                            label="Answer",
                            interactive=False,
                            lines=8
                        )

        # Event Handling
        upload_button.click(
            fn=upload_pdf,
            inputs=[pdf_input],
            outputs=[doc_id, upload_status]
        ).then(
            fn=lambda: gr.Button(visible=True),
            outputs=[summarize_button]
        )

        summarize_button.click(
            fn=summarize_pdf,
            inputs=[doc_id],
            outputs=[summary_output]
        ).then(
            fn=lambda: gr.Textbox(visible=True),
            outputs=[save_status]
        )

        save_button.click(
            fn=save_summary,
            inputs=[doc_id, summary_output],
            outputs=[save_status]
        )

        ask_button.click(
            fn=ask_question,
            inputs=[question_input, doc_id],
            outputs=[answer_output]
        )

    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        favicon_path="https://www.svgrepo.com/show/530600/file-search.svg"
    )