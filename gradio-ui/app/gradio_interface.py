import gradio as gr
import requests
import os

# FLASK_API_URL_SUMMARIZE = os.getenv("FLASK_API_URL_SUMMARIZE", "http://flask-api:5000/summarize")
FLASK_API_URL_SUMMARIZE = os.getenv("FLASK_API_URL_SUMMARIZE", "http://localhost:5000/summarize")
FLASK_API_URL_ASK = os.getenv("FLASK_API_URL_ASK", "http://localhost:5000/ask")
FLASK_API_URL_UPLOAD = os.getenv("FLASK_API_URL_UPLOAD", "http://localhost:5000/upload")


def upload_pdf(filepath):
    """Uploads a PDF file to the Flask API for indexing."""
    try:
        with open(filepath, "rb") as f:
            response = requests.post(FLASK_API_URL_UPLOAD, files={"file": f})
            response.raise_for_status()
        data = response.json()
        return data.get("doc_id"), f"Successfully uploaded and indexed {data.get('pages_indexed')} pages."
    except Exception as e:
        return None, f"Error: {str(e)}"

def summarize_pdf(doc_id):
    """Gets the summary for the uploaded PDF using doc_id."""
    if not doc_id:
        return "Please upload a document first."
    
    try:
        response = requests.post(
            FLASK_API_URL_SUMMARIZE,
            json={"doc_id": doc_id},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        if "summary" in data:
            return f"""# Document Summary

{data['summary']}

📚 Source: {data.get('source', 'Unknown')}
📝 Pages: {data.get('page_count', 'Unknown')}"""
        else:
            return "Error: No summary generated."
            
    except requests.exceptions.RequestException as e:
        return f"API Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"



def ask_question(question, doc_id):
    print(doc_id)
    """Sends a question to Flask API and formats the answer."""
    if not doc_id:
        return "Please upload a document first."
    try:
        # 1. Call Flask API
        response = requests.post(
            FLASK_API_URL_ASK,  # e.g., "http://localhost:5000/ask"
            json={"question": question, "doc_id": doc_id},
            timeout=10
        )
        response.raise_for_status()  # Raise error for bad status codes
        
        # 2. Process response
        data = response.json()
        
        if "answer" in data:  # If using the LLM-synthesized version
            return data["answer"]
        elif "answers" in data:  # If using raw ChromaDB results
            answers = data["answers"]
            return "\n\n".join([
                f"📄 Page {doc.get('page', '?')}:\n{doc['text']}" 
                for doc in answers
            ])
        else:
            return "No answer found."
            
    except requests.exceptions.RequestException as e:
        return f"API Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
     with gr.Blocks() as interface:
        gr.Markdown("# PDF Summarizer and Question Answering")
        gr.Markdown("First upload your PDF, then you can summarize or ask questions about it.")
        
        # Store document ID in state
        doc_id = gr.State(None)
        
        # Upload Section
        with gr.Row():
            pdf_input = gr.File(label="Upload PDF", type="filepath")
            upload_status = gr.Textbox(label="Upload Status", interactive=False)
        upload_button = gr.Button("Upload Document")
        upload_button.click(
            upload_pdf,
            inputs=[pdf_input],
            outputs=[doc_id, upload_status]
        )
        
        # Tabs for Summary and Q&A
        with gr.Tabs():
            with gr.Tab("Summarize"):
                summary_output = gr.Textbox(label="Summary", lines=10)
                summarize_button = gr.Button("Generate Summary", interactive=True)
                summarize_button.click(
                    summarize_pdf,
                    inputs=[doc_id],
                    outputs=[summary_output]
                )
            
            with gr.Tab("Ask Questions"):
                question_input = gr.Textbox(
                    label="Ask a Question",
                    placeholder="Type your question here..."
                )
                answer_output = gr.Textbox(label="Answer", lines=10)
                ask_button = gr.Button("Ask")
                ask_button.click(
                    ask_question,
                    inputs=[question_input, doc_id],
                    outputs=[answer_output]
                )

interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True
)