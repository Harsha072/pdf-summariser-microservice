from datetime import  time
from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from summarise import summarize_pdf
from werkzeug.utils import secure_filename
from retriever import DocumentRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from logger_config import setup_logger
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from langchain_community.document_loaders import PyPDFLoader
import threading
import tempfile
import os
import time

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

# Create custom temp directory
TEMP_DIR = os.path.join(os.path.dirname(__file__), 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

CHUNK_SIZE = 10  # Optimal for CPU-bound tasks
MAX_WORKERS = min(32, os.cpu_count() + 4)  # Dynamic worker count
chroma_lock = threading.Lock() 

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
    
@app.route('/save', methods=['POST'])
def save_summary():
    doc_id = request.json.get("doc_id")
    summary = request.json.get("summary")  # Expect a single summary string
    if not doc_id or not summary:
        return jsonify({"error": "Document ID and summary are required"}), 400

    try:
        # Save the edited summary back to the database or storage
        retriever.save_summary(doc_id, summary)
        return jsonify({"status": "success", "message": "Summary saved successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def process_chunk(docs_chunk, doc_id, filename, start_idx):
    """Optimized chunk processor with direct indexing"""
    texts = []
    metadatas = []
    ids = []
    
    for i, doc in enumerate(docs_chunk, start=start_idx):
        texts.append(doc.page_content)
        metadatas.append({
            "doc_id": doc_id,
            "source": secure_filename(filename),
            "page": doc.metadata.get("page", i+1),  # Default to logical page number
            "chunk": i,
            "upload_time": time.time()  # Faster than datetime.now()
        })
        ids.append(f"{doc_id}-{i}")
    
    # Thread-safe batch insert
    with chroma_lock:
        retriever.index_document(
            texts=texts,
            metadatas=metadatas,
            ids=ids
        )
    
    return len(texts)

@app.route('/upload', methods=['POST'])
def upload_file():
    start_time = time.time()
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    pdf_file = request.files['file']
    if not pdf_file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Only PDF files are supported"}), 400

    try:
        # Use custom temp directory
        temp_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}.pdf")
        pdf_file.save(temp_path)
        
        try:
            # Load PDF with optimized settings
            loader = PyPDFLoader(temp_path)
            docs = loader.load_and_split()
            
            # 2. Parallel processing with progress tracking
            total_pages = 0
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                doc_id = str(uuid.uuid4())
                
                for chunk_idx, i in enumerate(range(0, len(docs), CHUNK_SIZE)):
                    future = executor.submit(
                        process_chunk,
                        docs_chunk=docs[i:i + CHUNK_SIZE],
                        doc_id=doc_id,
                        filename=pdf_file.filename,
                        start_idx=i
                    )
                    futures.append(future)
                
                # Get results as they complete
                for future in as_completed(futures):
                    total_pages += future.result()
            
            return jsonify({
                "status": "success",
                "doc_id": doc_id,
                "pages_processed": total_pages,
                "processing_time": f"{time.time() - start_time:.2f}s"
            })
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
    except Exception as e:
        logger.exception("Upload failed")  # Auto logs stack trace
        return jsonify({"error": "Processing failed"}), 500

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