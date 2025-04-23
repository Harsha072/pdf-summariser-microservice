from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from summarise import summarize_pdf
from werkzeug.utils import secure_filename
from retriever import DocumentRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from logger_config import setup_logger
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from langchain_community.document_loaders import PyPDFLoader
import threading
import tempfile
import os

import uuid
# from tasks import process_pdf
from celery.result import AsyncResult

# Load environment variables
load_dotenv()
logger = setup_logger(__name__)
logger.info("Starting PDF Summarizer microservice")
app = Flask(__name__)
api = Api(app)
retriever = DocumentRetriever()

CHUNK_SIZE = 100  # Number of pages to process at once
MAX_WORKERS = 4   # Number of parallel workers

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
        
        print(docs['summary'])

        

        return jsonify({
            "answer": docs['summary']
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def process_chunk(docs_chunk, doc_id, filename):
    """Process a chunk of documents"""
    texts = []
    metadatas = []
    
    for i, doc in enumerate(docs_chunk):
        texts.append(doc.page_content)
        metadatas.append({
            "doc_id": doc_id,
            "source": secure_filename(filename),
            "page": doc.metadata.get("page", "N/A"),
            "chunk": i,
            "upload_time": datetime.now(timezone.utc).isoformat()
        })
    
    return texts, metadatas

@app.route('/upload', methods=['POST'])
def upload_file():
    logger.info("uploading file")
    if 'file' not in request.files:
        logger.error("No file provided")
        return jsonify({"error": "No file provided"}), 400
    
    pdf_file = request.files['file']
    if not pdf_file.filename.lower().endswith('.pdf'):
        logger.error("Only PDF files are supported")
        return jsonify({"error": "Only PDF files are supported"}), 400

    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_path = temp_file.name
            pdf_file.save(temp_path)
        
        # Generate unique document ID
        doc_id = str(uuid.uuid4())
        
        # Load and split PDF
        loader = PyPDFLoader(temp_path)
        docs = loader.load_and_split()
        
        # Split into chunks for parallel processing
        doc_chunks = [docs[i:i + CHUNK_SIZE] for i in range(0, len(docs), CHUNK_SIZE)]
        
        all_texts = []
        all_metadatas = []
        
        # Process chunks in parallel
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            process_func = partial(process_chunk, doc_id=doc_id, filename=pdf_file.filename)
            results = executor.map(process_func, doc_chunks)
            
            for texts, metadatas in results:
                all_texts.extend(texts)
                all_metadatas.extend(metadatas)
        
        # Batch index to ChromaDB
        retriever.index_document(
            texts=all_texts,
            metadatas=all_metadatas,
            ids=[f"{doc_id}-{i}" for i in range(len(all_texts))]
        )
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return jsonify({
            "status": "success",
            "doc_id": doc_id,
            "pages_processed": len(docs),
            "message": "File processed successfully"
        })
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": str(e)}), 500

# @app.route('/upload', methods=['POST'])
# def upload_file():
#     logger.info("uploading file")
#     if 'file' not in request.files:
#         logger.error("No file provided")
#         return jsonify({"error": "No file provided"}), 400
    
#     pdf_file = request.files['file']
#     if not pdf_file.filename.lower().endswith('.pdf'):
#         logger.error("Only PDF files are supported")
#         return jsonify({"error": "Only PDF files are supported"}), 400

#     try:
#         # Save to temp file
#         with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
#             temp_path = temp_file.name
#             pdf_file.save(temp_path)
        
#         # Generate unique document ID
#         doc_id = str(uuid.uuid4())
        
#         # Start background processing
#         task = process_pdf.delay(
#         temp_path=temp_path,
#         original_filename=pdf_file.filename,
#         doc_id=doc_id,
#         openai_api_key=os.getenv("OPENAI_API_KEY")  # Explicitly pass key
#     )
        
#         return jsonify({
#             "status": "processing",
#             "doc_id": doc_id,
#             "task_id": task.id,
#             # "task_id": "123",
#             "message": "File uploaded successfully. Processing in background."
#         })
        
#     except Exception as e:
#         logger.info("error :"+str(e))
#         return jsonify({"error": str(e)}), 500




@app.route('/status/<task_id>')
def get_status(task_id):
    """Check the status of a PDF processing task"""
    task_result = AsyncResult(task_id)
    
    if task_result.state == 'PENDING':
        response = {
            'state': task_result.state,
            'status': 'Waiting to start processing...'
        }
    elif task_result.state == 'FAILURE':
        response = {
            'state': task_result.state,
            'status': 'Processing failed',
            'error': str(task_result.info)
        }
    elif task_result.state == 'SUCCESS':
        response = {
            'state': task_result.state,
            'status': 'Processing complete',
            'result': task_result.get()
        }
    else:
        # Processing in progress
        response = {
            'state': task_result.state,
            'status': 'Processing in progress...',
            'progress': task_result.info if task_result.info else {}
        }
    
    return jsonify(response)

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