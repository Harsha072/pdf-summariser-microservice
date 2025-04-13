from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from summarise import summarize_pdf
from retriever import DocumentRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader
import os
from dotenv import load_dotenv
import tempfile
from werkzeug.utils import secure_filename
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)
api = Api(app)
retriever = DocumentRetriever()

# class SummarizePDF(Resource):
#     def post(self):
#         # Check if a file is uploaded
#         if 'file' not in request.files:
#             return {"error": "No file provided"}, 400
        
#         pdf_file = request.files['file']
        
#         # Validate file type
#         if not pdf_file.filename.lower().endswith('.pdf'):
#             return {"error": "Only PDF files are supported"}, 400
        
#         # Save the uploaded file temporarily
#         with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
#             temp_path = temp_file.name
#             pdf_file.save(temp_path)
        
#         try:
#             # Generate summary
#             summary = summarize_pdf(temp_path)
            
#             # Ensure the summary is a string (not a Response object)
#             if hasattr(summary, 'data'):
#                 # If it's a Response object, decode it
#                 summary = summary.data.decode('utf-8')
            
#             return {"summary": summary}, 200
#         except Exception as e:
#             return {"error": str(e)}, 500
#         finally:
#             # Clean up temporary file
#             if os.path.exists(temp_path):
#                 os.remove(temp_path)

# # Add the resource to the API
# api.add_resource(SummarizePDF, '/summarize')

@app.route('/summarize', methods=['POST'])
def summarize():
    
    doc_id = request.json.get("doc_id")  # Optional: Filter by specific upload
    print(doc_id)
    if not doc_id:
        return jsonify({"error": "Question is required"}), 400

    try:
        # Filter by doc_id if provided, else search all documents
        filter_criteria = doc_id if doc_id else None
        
        # Get top 3 most relevant chunks (filtered if doc_id exists)
        docs = summarize_pdf(doc_id)
        
        if not docs:
            return jsonify({"error": "No matching content found"}), 404
        
        print(docs)

        

        return jsonify({
            "answer": docs['summary']
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    pdf_file = request.files['file']
    if not pdf_file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Only PDF files are supported"}), 400

    try:
        # Save to temp file
        # temp_path = f"/tmp/{secure_filename(pdf_file.filename)}"
        # pdf_file.save(temp_path)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_path = temp_file.name
            pdf_file.save(temp_path)
        
        # Generate unique document ID
        doc_id = str(uuid.uuid4())
        
        # Load and index document
        loader = PyPDFLoader(temp_path)
        docs = loader.load_and_split()
        
        for doc in docs:
            retriever.index_document(
                text=doc.page_content,
                metadata={
                    "doc_id": doc_id,  # Unique ID for this upload
                    "source": secure_filename(pdf_file.filename),  # Original filename
                    "page": doc.metadata.get("page", "N/A"),
                    "upload_time": datetime.now(timezone.utc).isoformat()  # Track when indexed
                }
            )
        
        return jsonify({
            "status": "success",
            "doc_id": doc_id,
            "pages_indexed": len(docs)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)  # Clean up



@app.route('/ask', methods=['POST'])
def ask_question():
    question = request.json.get("question")
    doc_id = request.json.get("doc_id")  # Optional: Filter by specific upload
    print(doc_id)
    if not question:
        return jsonify({"error": "Question is required"}), 400

    try:
        # Filter by doc_id if provided, else search all documents
        filter_criteria = {"doc_id": doc_id} if doc_id else None
        
        # Get top 3 most relevant chunks (filtered if doc_id exists)
        docs = retriever.query(question, top_k=3, filter_criteria=filter_criteria)
        
        if not docs:
            return jsonify({"error": "No matching content found"}), 404

        # Generate answer strictly from these docs
        context = "\n\n".join([doc.page_content for doc in docs])

        answer = ChatOpenAI(model="gpt-3.5-turbo").invoke(
            f"Answer using ONLY this:\n{context}\n\nQuestion: {question}"
        ).content

        return jsonify({
            "answer": answer,
            "sources": [doc.metadata["source"] for doc in docs]  # Provenance
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)